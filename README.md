# Talent Mirror

Espelho local dos candidatos/currículos da inHire, com banco de currículos
categorizável para hunting. Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
para o desenho completo e as fases planejadas.

## Rodando localmente

1. Copie `.env.example` para `.env` e preencha `INHIRE_API_KEY` (e demais
   variáveis conforme necessário).
2. Suba o banco de dados:

   ```
   docker compose up -d db
   ```

3. Backend:

   ```
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   alembic revision --autogenerate -m "init"
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

   API disponível em http://localhost:8000 (docs interativas em `/docs`).

4. Frontend:

   ```
   cd frontend
   npm install
   npm run dev
   ```

   Acesse http://localhost:5173.

## Disparando a Fase 1 (importar os últimos 200 currículos)

Pela UI, clique em "Importar últimos 200 da inHire" na tela do banco de
currículos, ou direto via API:

```
curl -X POST "http://localhost:8000/sync/backfill?limit=200"
```

## Pendências

- Endpoints e formato de payload da inHire ainda não confirmados contra a
  documentação oficial (ver `backend/app/services/inhire_client.py`).
- Integração com Azure DevOps ainda não iniciada.
