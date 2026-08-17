# Arquitetura — Talent Mirror

> Última atualização: 2026-08-18. Este documento é o ponto de partida para
> retomar o projeto em qualquer conversa nova — leia isto antes de
> qualquer coisa.

## Objetivo

Espelhar candidatos e currículos administrados na inHire para uma base
própria, permitindo visões que o ATS não oferece e um banco de currículos
pesquisável/categorizável para hunting independente de vaga. Primeiro uso
real: demonstração para a squad de aquisição de talentos da DB1.

## Status atual (resumo executivo)

- ✅ **Sincronização com a inHire funcionando de ponta a ponta**: 200
  candidatos + currículos reais da conta da DB1 já importados.
- ✅ **Frontend funcionando** com identidade visual da DB1 (azul-marinho +
  ciano), duas telas: categorizar e revisar por categoria.
- ⚠️ **Sincronização é 100% manual** — não há scheduler automático rodando
  (ver seção "O que NÃO é automático" abaixo).
- ⚠️ **Roda só localmente**, na máquina do usuário (sem Docker/Postgres —
  ver seção "Ambiente local"). Não é um serviço hospedado ainda.
- ❌ Integração com Azure DevOps: não iniciada.

## Como rodar isto do zero (numa máquina nova, ou depois de reiniciar)

Pré-requisitos já confirmados nesta máquina: Python 3.14 e Node.js v22 já
instalados (sem Docker — não é necessário).

**Backend** (numa janela de terminal):
```
cd Projeto_AT/backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
(se a `.venv` não existir: `python -m venv .venv` e depois
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`)

**Frontend** (outra janela de terminal):
```
cd Projeto_AT/frontend
npm run dev
```
(se `node_modules` não existir: `npm install` antes)

Depois, abrir **http://localhost:5173** no navegador. O Vite faz proxy de
`/api/*` para `http://localhost:8000` (ver `frontend/vite.config.ts`).

**Para importar/atualizar os currículos**: clicar em "Importar últimos 200
da inHire" na tela Categorizar, ou `POST http://localhost:8000/sync/backfill?limit=200`.
Leva ~5 minutos para 200 candidatos (ver por quê na seção de custo de API).

## Ambiente local (por quê SQLite, não Postgres/Docker)

O usuário não tinha Python/Docker instalados e a demonstração era urgente.
Decisão: banco **SQLite local temporário** (`backend/talent_mirror.db`,
arquivo único) em vez de Postgres via Docker Compose. Isso está refletido
em `backend/.env` (`DATABASE_URL=sqlite:///./talent_mirror.db`, comentário
mostra a linha do Postgres para quando migrar). Ajustes de código para
isso funcionar nos dois bancos:
- `app/db/session.py`: `connect_args={"check_same_thread": False}` quando
  a URL é sqlite.
- `app/models/resume.py`: `tags` usa `ARRAY(String).with_variant(JSON(), "sqlite")`
  — Postgres usa ARRAY nativo, SQLite cai pra JSON (não suporta ARRAY).
  **Filtro `.any()` por tag só funciona em Postgres** — não usado ainda
  no fluxo principal.
- `requirements.txt` usa `>=` em vez de `==`: os pins originais não tinham
  wheels pré-compiladas pro Python 3.14 (muito recente) e travavam tentando
  compilar do zero (precisava de Rust/MSVC Build Tools, que não estavam
  instalados). Com `>=`, o pip resolve versões mais novas com wheels prontas.

**Quando migrar pra produção/Azure**: trocar `DATABASE_URL` pro Postgres,
rodar `docker-compose up`, e considerar rodar `alembic` (ainda não há
migrations geradas — hoje as tabelas são criadas via
`Base.metadata.create_all()` no startup do FastAPI, ok pra dev, não pra
produção com dados reais).

## Componentes

- **backend/** — FastAPI + SQLAlchemy. Responsável por:
  - sincronizar dados da inHire (`app/services/inhire_client.py`, `sync_service.py`);
  - extrair texto de PDF/DOCX dos currículos (`resume_parser.py`) — usado
    só como *fallback*, já que a inHire geralmente já manda o texto extraído;
  - armazenar os arquivos originais (`storage.py`, local em dev / Azure Blob em produção);
  - expor API REST para o frontend (`app/api/routers/*`).
- **frontend/** — React 18 + Vite + React Router. Duas telas (ver seção
  própria abaixo), com identidade visual da DB1.

## Modelo de dados

- `Candidate` — candidato espelhado (1 por `inhire_candidate_id`).
  Inclui `applied_jobs` (JSON: lista de `{id, name, status, stage}` das
  vagas às quais já se candidatou — vem de `GET /talents/{id}`).
- `Job` / `Application` — modelos já existem no código mas **ainda não
  são populados por nada** — reservados para quando entrar a visão por
  vaga/recrutador e a integração com Azure DevOps (fases futuras).
- `Resume` — arquivo de currículo + texto extraído + campos de
  categorização. `category` é um enum fixo: `insuficiente` | `bom` |
  `otimo` (decidido nesta sessão, substituindo o texto livre original).
- `SyncLog` — histórico de cada rodada de sincronização (`GET /sync/logs`).

## Fluxo de sincronização com a inHire (confirmado e testado na prática)

**Autenticação**: `POST https://auth.inhire.app/login`, headers
`Content-Type: application/json` + `X-Tenant: db1`, body
`{"email", "password"}` (conta de serviço, credenciais em `.env`).
Resposta `201` com `{"accessToken", "refreshToken"}`. Toda chamada em
`api.inhire.app` exige `Authorization: Bearer <token>` **e**
`X-Tenant: db1` (inferido do subdomínio do painel da conta, confirmado
funcionando).

**Import de candidatos/currículos** (`InHireClient.list_recent_talents`/
`list_talents_since`, chamado por `sync_service.py`):
1. `POST /talents/paginated` — lista talentos da **conta inteira**,
   independente de vaga (a DB1 tem centenas de vagas; escanear vaga por
   vaga é inviável — já tentamos e travava). Suporta `orderBy: {field:
   "createdAt"|"updatedAt", direction}` e paginação por
   `exclusiveStartKey`/resposta `exclusiveStartKey`. Cada item já vem com
   `name`, `email`, `phone`, `location`, `files` (com `fileCategory ==
   "resumes"`) e até `resume` (texto do currículo pré-extraído pela
   própria inHire) — **nenhuma chamada extra é necessária pra isso**.
2. Para o campo `applied_jobs` (vagas às quais o talento já se
   candidatou — não documentado, descoberto testando): uma chamada extra
   por candidato, `GET /talents/{id}` (`InHireClient.get_talent_detail`),
   que devolve `jobs: [{id, name, status, talent: {stage: {name}}}]`.
   É por isso que o backfill de 200 candidatos leva ~5 minutos (200
   chamadas de listagem + assinatura + download + esse detalhe extra).
3. Download do currículo: `GET /files/signature/{fileCategory}/
   {nome-sem-extensao}*{id}.{extensao}` retorna
   `{"signedURL": "..."}` (⚠️ **chave com "URL" maiúsculo** — a doc oficial
   sugere `url`/`signedUrl`, é diferente na prática). Essa URL assinada da
   S3 é usada num GET direto (sem token da inHire) pra baixar o arquivo.

**Bug de acentuação corrigido**: uma fração dos currículos vem da inHire
com mojibake (ex. "experiÃªncia" em vez de "experiência") — tanto no
texto do currículo quanto nos nomes de vaga. Corrigido aplicando
`ftfy.fix_text()` em `sync_service.py` sobre `talent["resume"]` e sobre
`job["name"]`/`stage["name"]`. Texto que já está correto não é alterado.

## O que NÃO é automático (importante)

Não existe nenhum agendador rodando. Nada replica sozinho quando alguém
se candidata na inHire. Pra atualizar a base:
- **Hoje**: clicar em "Importar últimos 200 da inHire" (tela Categorizar)
  ou chamar `POST /sync/backfill?limit=200`. Isso busca de novo os 200
  candidatos mais recentes (cobre bem o que é novo desde o último import,
  mas se mais de 200 pessoas se candidatarem entre um import e outro,
  algum caso mais antigo fica de fora até o próximo).
- **Fase 2 (não implementada ainda)**: `sync_service.sync_since()` e o
  endpoint `POST /sync/incremental?hours=12` já existem no código, prontos
  pra trazer só o que mudou — mas não estão ligados a nenhum agendador
  (ex.: APScheduler, cron, Azure Function com timer trigger). Além disso,
  pra rodar automaticamente 24h isso precisa estar hospedado num servidor
  sempre ligado — hoje só roda enquanto a máquina do usuário está com os
  dois servidores (`uvicorn` + `vite`) de pé.
- A semântica exata do filtro `filter.updatedAt` em `/talents/paginated`
  (usado por `list_talents_since`) não foi validada contra um caso real
  ainda — assumimos que é "desde essa data" (`>=`), mas isso só vai ser
  confirmado quando a Fase 2 for testada de verdade.

## Frontend: as duas telas

Construído em cima do pedido do usuário pra apresentar pra squad de
aquisição de talentos. Identidade visual extraída do modelo de
PowerPoint oficial da DB1 (25 anos) — azul-marinho profundo + ciano
vibrante (ver `frontend/src/theme.css`, variáveis `--db1-navy-*` e
`--db1-cyan*`). **Não temos o arquivo do logo oficial** (losango em duas
tonalidades de azul) — usamos um "chip" de texto "DB1" como placeholder;
trocar se o usuário mandar o PNG/SVG real.

- **`/categorizar`** (`CategorizePage.tsx`) — busca (nome, e-mail,
  telefone, texto do currículo ou nome/código da vaga — via `Resume.raw_text`,
  `Candidate.full_name/email/phone` e `Candidate.applied_jobs` serializado)
  + botões pra marcar categoria (`insuficiente`/`bom`/`otimo`) em cada
  card. Expandir um card mostra:
  - o PDF embutido num `<iframe>` (`GET /resumes/{id}/view`, com
    `Content-Disposition: inline` — endpoint separado do `/download`, que
    força o navegador a baixar em vez de exibir);
  - logo abaixo do link de download, a lista de **vagas às quais o
    candidato já se candidatou** (`applied_jobs`), com etapa do funil e
    status da vaga.
- **`/revisar`** (`ReviewPage.tsx`) — cards de estatística (quantos
  ótimo/bom/insuficiente/total) + abas pra filtrar a lista por categoria.

Componentes compartilhados: `components/Layout.tsx` (header com nav),
`components/CandidateCard.tsx` (usado nas duas telas).

## Fases futuras (não iniciadas)

3. **Dashboards por vaga/recrutador** — os modelos `Job`/`Application` já
   existem mas não são populados. `InHireClient.list_jobs()` (`POST
   /jobs/paginated/lean`) já está implementado e confirmado, pronto pra
   usar quando essa fase começar.
4. **Integração com Azure DevOps** — não iniciada. Entraria como
   `app/services/azure_devops_client.py` + `Job.azure_devops_work_item_id`,
   pra a recrutadora registrar movimentação de funil direto no Talent
   Mirror em vez de atualizar o board manualmente.
