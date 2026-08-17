"""Cliente HTTP para a API da inHire.

Confirmado contra a documentacao oficial (paginas "Login" e "Obter
candidaturas paginadas", lidas via HTML salvo pelo usuario):

- Login: `POST https://auth.inhire.app/login`, headers `Content-Type:
  application/json` + `X-Tenant: <tenant>`, body `{"email", "password"}`,
  resposta 201 `{"accessToken", "refreshToken"}`.
- Toda chamada em `api.inhire.app` exige `Authorization: Bearer <token>` E
  `X-Tenant: <tenant>` (identificador multi-tenant, mapeia pra partition key
  no DynamoDB deles).
- "Listar talentos paginados" (CONFIRMADO E TESTADO direto na conta da
  DB1): `POST /talents/paginated` lista os talentos da CONTA INTEIRA,
  independente de vaga — nao precisa escanear vaga por vaga (a conta da
  DB1 tem centenas de vagas; escanear cada uma e' inviavel, jah tentamos).
  Body: `{"exclusiveStartKey"?, "orderBy": {"field": "createdAt"|
  "updatedAt", "direction": "asc"|"desc"}, "filter"?: {"createdAt"?,
  "updatedAt"?}}`. Resposta: `{"items": [...], "exclusiveStartKey":
  {...}|null}`. O campo `filter.updatedAt`/`filter.createdAt` nao teve a
  semantica exata confirmada na doc (assumindo "desde essa data", como um
  `>=` — precisa validar no primeiro uso real da Fase 2).
- CONFIRMADO NA PRATICA (a doc descreve o item como "lean" mas a resposta
  real vem bem mais completa): cada item de `talents/paginated` ja traz
  `id`, `name`, `email`, `phone`, `location`, `status`, `createdAt`,
  `updatedAt`, `linkedinUsername`, `files` (lista de `{id, name,
  fileCategory, key}` — curriculo = `fileCategory: "resumes"`),
  `structuredResume` (CV parseado) e até `resume` (texto do curriculo ja
  extraido pela propria inHire, pronto pra usar sem precisar de
  pypdf/python-docx). Ou seja: **nenhuma chamada extra por candidato e'
  necessaria** pra popular candidato + curriculo — só o download do
  arquivo original via signature (abaixo). O campo `jobs` descrito na doc
  nao apareceu nos testes reais (provavelmente só aparece quando o
  talento tem candidatura(s) ativa(s) a alguma vaga).
- Download de arquivo via signature (pagina "Lidando com arquivos"):
  `GET /files/signature/{fileCategory}/{nome-sem-extensao}*{id}.{extensao}`
  retorna URL assinada da S3 (valida 2 min), usada num GET direto pra
  baixar o arquivo original (guardado no storage, além do texto que já
  vem em `talent["resume"]`).
- "Obter candidaturas de um talento": `GET /job-talents/{jobId}/talents/
  {talentId}` — devolve a candidatura completa incluindo a etapa do funil
  daquela vaga especifica (`stage`). Nao usado no fluxo de sync de
  candidatos/curriculo (que não precisa mais disso), mas fica disponivel
  pro dia em que formos popular `Application.funnel_stage` por vaga.
- "Obter vagas paginadas": `POST /jobs/paginated/lean`, body
  `{"exclusiveStartKey", "limit"}`, resposta `{"results": [...],
  "startKey": {...}}` — mantido no cliente para uso futuro (dashboards por
  vaga/recrutador), mas NAO e' mais usado pelo backfill de candidatos.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings


class InHireClient:
    def __init__(self) -> None:
        self._auth_client = httpx.Client(base_url=settings.INHIRE_AUTH_BASE_URL, timeout=30.0)
        self._api_client = httpx.Client(base_url=settings.INHIRE_API_BASE_URL, timeout=30.0)
        self._token: str | None = None

    def close(self) -> None:
        self._auth_client.close()
        self._api_client.close()

    def _authenticate(self) -> str:
        response = self._auth_client.post(
            settings.INHIRE_LOGIN_ENDPOINT,
            json={"email": settings.INHIRE_EMAIL, "password": settings.INHIRE_PASSWORD},
            headers={"X-Tenant": settings.INHIRE_TENANT},
        )
        response.raise_for_status()
        data = response.json()

        token = data.get("accessToken")
        if not token:
            raise RuntimeError(f"Resposta de login da inHire sem accessToken: {data}")
        return token

    def _authorized_headers(self) -> dict:
        if self._token is None:
            self._token = self._authenticate()
        return {"Authorization": f"Bearer {self._token}", "X-Tenant": settings.INHIRE_TENANT}

    def list_jobs(self) -> list[dict]:
        """Retorna todas as vagas (para descobrir os `jobId` a percorrer).
        Confirmado: `POST /jobs/paginated/lean`, itens em `results`, cursor
        de continuacao em `startKey` (nome diferente do `exclusiveStartkey`
        usado pelo endpoint de candidaturas)."""
        results: list[dict] = []
        exclusive_start_key: dict | None = None

        while True:
            body = {"exclusiveStartKey": exclusive_start_key} if exclusive_start_key else {}
            response = self._api_client.post(
                settings.INHIRE_JOBS_ENDPOINT,
                json=body,
                headers=self._authorized_headers(),
            )
            response.raise_for_status()
            payload = response.json()

            items = payload.get("results", [])
            results.extend(items)

            exclusive_start_key = payload.get("startKey")
            if not exclusive_start_key or not items:
                break

        return results

    def list_recent_talents(self, limit: int = 200) -> list[dict]:
        """Retorna os `limit` talentos mais recentes da conta inteira
        (independente de vaga), usados no backfill inicial (Fase 1). Para
        assim que tiver `limit` itens — nao escaneia a conta inteira."""
        results: list[dict] = []
        exclusive_start_key: dict | None = None

        while len(results) < limit:
            body: dict = {"orderBy": {"field": "createdAt", "direction": "desc"}}
            if exclusive_start_key:
                body["exclusiveStartKey"] = exclusive_start_key

            response = self._api_client.post(
                "/talents/paginated",
                json=body,
                headers=self._authorized_headers(),
            )
            response.raise_for_status()
            payload = response.json()

            items = payload.get("items", [])
            results.extend(items)

            exclusive_start_key = payload.get("exclusiveStartKey")
            if not exclusive_start_key or not items:
                break

        return results[:limit]

    def list_talents_since(self, since: datetime) -> list[dict]:
        """Retorna talentos atualizados desde `since`, usados na rotina
        incremental de 12h (Fase 2).

        PENDENTE: a semantica exata de `filter.updatedAt` (>= vs igualdade
        exata) nao foi confirmada na documentacao — assumindo ">=" (o caso
        de uso descrito e' "filtrar por data de atualizacao" para sync
        incremental). Validar no primeiro uso real."""
        results: list[dict] = []
        exclusive_start_key: dict | None = None

        while True:
            body: dict = {
                "orderBy": {"field": "updatedAt", "direction": "desc"},
                "filter": {"updatedAt": since.isoformat()},
            }
            if exclusive_start_key:
                body["exclusiveStartKey"] = exclusive_start_key

            response = self._api_client.post(
                "/talents/paginated",
                json=body,
                headers=self._authorized_headers(),
            )
            response.raise_for_status()
            payload = response.json()

            items = payload.get("items", [])
            results.extend(items)

            exclusive_start_key = payload.get("exclusiveStartKey")
            if not exclusive_start_key or not items:
                break

        return results

    def get_job_talent_detail(self, job_id: str, talent_id: str) -> dict:
        """Confirmado ("Obter candidaturas de um talento"): `GET
        /job-talents/{jobId}/talents/{talentId}` devolve a candidatura
        completa (nao o payload "lean"), com `files`/`resumeSigned` na raiz
        — e' daqui que vem o curriculo de fato."""
        response = self._api_client.get(
            f"/job-talents/{job_id}/talents/{talent_id}",
            headers=self._authorized_headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_talent_detail(self, talent_id: str) -> dict:
        """CONFIRMADO na pratica (nao documentado nas paginas salvas até
        agora): `GET /talents/{id}` devolve o talento com um campo `jobs`
        — a lista de vagas as quais ele se candidatou, cada uma com
        `id`, `name`, `status` da vaga e `talent.stage` (etapa do funil
        daquela candidatura especifica). O payload de `talents/paginated`
        usado no backfill NAO traz esse campo preenchido."""
        response = self._api_client.get(
            f"/talents/{talent_id}",
            headers=self._authorized_headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_file_signed_url(self, file_category: str, filename: str, file_id: str) -> str:
        """Implementa o fluxo de download descrito em "Lidando com arquivos":
        gera uma URL assinada (valida por 2 minutos) para o arquivo `file_id`.

        CONFIRMADO na pratica: a resposta e' `{"signedURL": "..."}` (com
        "URL" maiusculo — nao "url" nem "signedUrl" como a doc de
        "Lidando com arquivos" fazia supor)."""
        name_no_ext, _, extension = filename.rpartition(".")
        key = f"{name_no_ext}*{file_id}.{extension}" if extension else f"{filename}*{file_id}"

        response = self._api_client.get(
            f"/files/signature/{file_category}/{key}",
            headers=self._authorized_headers(),
        )
        response.raise_for_status()
        data = response.json()

        url = data.get("signedURL") or data.get("signedUrl") or data.get("url")
        if not url:
            raise RuntimeError(f"Resposta de /files/signature sem URL assinada reconhecida: {data}")
        return url

    def download_file_content(self, signed_url: str) -> bytes:
        """A URL assinada e' um link direto da S3: nao leva o Bearer token da inHire."""
        response = httpx.get(signed_url, timeout=30.0)
        response.raise_for_status()
        return response.content
