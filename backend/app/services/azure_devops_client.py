"""Cliente HTTP para o board de Aquisicao de Talentos no Azure DevOps.

Confirmado testando direto contra a API real (org `db1global`, projeto
"Aquisicao de Talentos"):
- Autenticacao: HTTP Basic com usuario vazio e senha = PAT.
- Cada vaga e' um work item do tipo customizado **"Vaga"** (nao "Feature"
  nem o generico "Task"). Campos relevantes:
  - `System.Title` — nome da vaga.
  - `System.State` — etapa do funil (mapeia 1:1 com as colunas do board:
    Backlog, Abertura da Vaga, Triagem/Hunting, Entrevista Inicial,
    Entrevista Gestor, Entrevista Tecnica/Time, Diligencia, Fechamento,
    Impedimento, Cancelada, Contratada).
  - `System.AssignedTo` — a recrutadora responsavel pela vaga (confirmado:
    5 pessoas diferentes distribuidas entre as 75 vagas reais da conta).
  - `Custom.atBusinessUnit` / `Custom.atTipoDeVaga` / `Custom.atLider` —
    unidade de negocio, tipo/area da vaga e lider/gestor solicitante
    (este ultimo NAO e' o recrutador, e' quem pediu a vaga).
- Projeto pode ser referenciado pelo NOME (com espacos/acentos, URL-encoded
  automaticamente pelo httpx) em vez de precisar resolver o ID primeiro.

Leitura E escrita: mover uma vaga de etapa (`update_stage`), trocar a
recrutadora responsavel (`update_recruiter`) e comentarios
(`list_comments`/`add_comment`) refletem direto no work item real do
Azure DevOps — o Talent Mirror e' um espelho de mao dupla desse board,
nao uma copia local. Nao ha cache/DB local pra vagas: cada leitura e'
uma chamada ao vivo.
"""

from __future__ import annotations

import base64

import httpx

from app.core.config import settings

VAGA_FIELDS = [
    "System.Id",
    "System.Title",
    "System.State",
    "System.BoardColumn",
    "System.AssignedTo",
    "System.ChangedDate",
    "System.CreatedDate",
    "Custom.atBusinessUnit",
    "Custom.atTipoDeVaga",
    "Custom.atLider",
]


class AzureDevOpsClient:
    def __init__(self) -> None:
        auth = base64.b64encode(f":{settings.AZURE_DEVOPS_PAT}".encode()).decode()
        self._client = httpx.Client(
            base_url=settings.AZURE_DEVOPS_ORG_URL,
            headers={"Authorization": f"Basic {auth}"},
            timeout=30.0,
        )
        self._project = settings.AZURE_DEVOPS_PROJECT

    def close(self) -> None:
        self._client.close()

    def list_vagas(self) -> list[dict]:
        """Retorna todas as vagas (work items tipo "Vaga") com os campos do
        funil e do recrutador responsavel."""
        wiql = {
            "query": (
                "SELECT [System.Id] FROM WorkItems "
                "WHERE [System.WorkItemType] = 'Vaga' "
                "ORDER BY [System.ChangedDate] DESC"
            )
        }
        response = self._client.post(
            f"/{self._project}/_apis/wit/wiql",
            params={"api-version": "7.1"},
            json=wiql,
        )
        response.raise_for_status()
        ids = [str(item["id"]) for item in response.json().get("workItems", [])]
        if not ids:
            return []

        results: list[dict] = []
        # A API limita a ~200 ids por chamada de detalhe.
        for i in range(0, len(ids), 200):
            batch = ids[i : i + 200]
            detail_response = self._client.get(
                f"/{self._project}/_apis/wit/workitems",
                params={
                    "ids": ",".join(batch),
                    "fields": ",".join(VAGA_FIELDS),
                    "api-version": "7.1",
                },
            )
            detail_response.raise_for_status()
            for item in detail_response.json().get("value", []):
                results.append(_simplify(item))

        return results

    def update_stage(self, work_item_id: int, stage: str) -> None:
        """Move a vaga pra outra coluna do board (equivalente a arrastar o
        card no Azure DevOps): PATCH em `System.State`, que e' o campo que
        as colunas do board mapeiam 1:1 (confirmado em `_apis/work/boards/
        {id}/columns`)."""
        self._patch_fields(work_item_id, {"System.State": stage})

    def update_recruiter(self, work_item_id: int, recruiter_email: str) -> None:
        """Troca a recrutadora responsavel (`System.AssignedTo`). O Azure
        DevOps aceita o e-mail/uniqueName da pessoa e resolve a identidade
        sozinho."""
        self._patch_fields(work_item_id, {"System.AssignedTo": recruiter_email})

    def _patch_fields(self, work_item_id: int, fields: dict[str, str]) -> None:
        response = self._client.patch(
            f"/{self._project}/_apis/wit/workitems/{work_item_id}",
            params={"api-version": "7.1"},
            headers={"Content-Type": "application/json-patch+json"},
            json=[{"op": "add", "path": f"/fields/{name}", "value": value} for name, value in fields.items()],
        )
        response.raise_for_status()

    def list_comments(self, work_item_id: int) -> list[dict]:
        """Lista o mural de discussao do work item — o mesmo que aparece na
        aba "Discussion" ao abrir a vaga no Azure DevOps."""
        response = self._client.get(
            f"/{self._project}/_apis/wit/workItems/{work_item_id}/comments",
            params={"api-version": "7.1-preview.4"},
        )
        response.raise_for_status()
        return [_simplify_comment(c) for c in response.json().get("comments", [])]

    def add_comment(self, work_item_id: int, text: str) -> dict:
        response = self._client.post(
            f"/{self._project}/_apis/wit/workItems/{work_item_id}/comments",
            params={"api-version": "7.1-preview.4"},
            json={"text": text},
        )
        response.raise_for_status()
        return _simplify_comment(response.json())


def _simplify(item: dict) -> dict:
    fields = item.get("fields", {})
    assigned_to = fields.get("System.AssignedTo")
    lider = fields.get("Custom.atLider")

    return {
        "id": item.get("id"),
        "title": fields.get("System.Title"),
        "stage": fields.get("System.State"),
        "recruiter": assigned_to.get("displayName") if isinstance(assigned_to, dict) else None,
        "recruiter_email": assigned_to.get("uniqueName") if isinstance(assigned_to, dict) else None,
        "business_unit": fields.get("Custom.atBusinessUnit"),
        # Custom.atTipoDeVaga tem valores tipo "Comercial"/"Engenharia"/
        # "Produto" — na pratica e' a "area" da vaga, apesar do nome do
        # campo no Azure DevOps.
        "area": fields.get("Custom.atTipoDeVaga"),
        "hiring_manager": lider.get("displayName") if isinstance(lider, dict) else None,
        "changed_at": fields.get("System.ChangedDate"),
        "created_at": fields.get("System.CreatedDate"),
    }


def _simplify_comment(comment: dict) -> dict:
    return {
        "id": comment.get("id"),
        "text": comment.get("text"),
        "author": (comment.get("createdBy") or {}).get("displayName"),
        "created_at": comment.get("createdDate"),
    }
