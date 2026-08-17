import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import candidates, jobs, resumes, sync
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Talent Mirror", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_app_password(request: Request, call_next):
    """Gate temporario de acesso (senha compartilhada) enquanto o SSO real
    via Entra ID nao esta pronto — ver memoria "project_talent_mirror_sso_pending".
    Desligado quando APP_ACCESS_PASSWORD nao esta setado (uso local)."""
    if not settings.APP_ACCESS_PASSWORD or request.method == "OPTIONS" or request.url.path == "/health":
        return await call_next(request)

    # Header pra chamadas via fetch(); query param pra links navegados
    # direto pelo navegador (download/visualizacao de PDF em <iframe>/<a>,
    # que nao tem como carregar um header customizado).
    supplied = request.headers.get("x-app-password") or request.query_params.get("pw")
    if supplied != settings.APP_ACCESS_PASSWORD:
        return JSONResponse(status_code=401, content={"detail": "Senha de acesso invalida ou ausente"})

    return await call_next(request)


app.include_router(candidates.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(sync.router)


@app.on_event("startup")
def on_startup() -> None:
    # Em desenvolvimento cria as tabelas direto; em produção usar `alembic upgrade head`.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
