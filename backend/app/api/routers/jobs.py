import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.azure_devops_client import AzureDevOpsClient

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobUpdate(BaseModel):
    stage: str | None = None
    recruiter_email: str | None = None


class CommentCreate(BaseModel):
    text: str

# Ordem real das colunas do board "Features" no Azure DevOps (Aquisicao de
# Talentos), usada pra ordenar a visao do funil na mesma sequencia do board.
FUNNEL_STAGE_ORDER = [
    "Backlog",
    "Abertura da Vaga",
    "Triagem/Hunting",
    "Entrevista Inicial",
    "Entrevista Gestor",
    "Entrevista Técnica/Time",
    "Diligência",
    "Fechamento",
    "Impedimento",
    "Cancelada",
    "Contratada",
]


@router.get("/funnel")
def get_funnel(recruiter: str | None = None, stage: str | None = None):
    """Visao do funil de vagas, lida direto do board de Aquisicao de
    Talentos no Azure DevOps (sem cache/espelho local por enquanto — sao
    poucas vagas e a leitura e' rapida)."""
    client = AzureDevOpsClient()
    try:
        vagas = client.list_vagas()
    finally:
        client.close()

    if recruiter:
        vagas = [v for v in vagas if v.get("recruiter") == recruiter]
    if stage:
        vagas = [v for v in vagas if v.get("stage") == stage]

    vagas.sort(
        key=lambda v: (
            FUNNEL_STAGE_ORDER.index(v["stage"]) if v.get("stage") in FUNNEL_STAGE_ORDER else 99,
            v.get("recruiter") or "",
        )
    )
    return vagas


@router.get("/funnel/stats")
def get_funnel_stats():
    """Contagem de vagas por etapa do funil e por recrutador, para os
    cards de resumo da tela de funil."""
    client = AzureDevOpsClient()
    try:
        vagas = client.list_vagas()
    finally:
        client.close()

    by_stage: dict[str, int] = {}
    by_recruiter: dict[str, int] = {}
    by_business_unit: dict[str, int] = {}
    by_area: dict[str, int] = {}
    for vaga in vagas:
        stage = vaga.get("stage") or "Sem etapa"
        by_stage[stage] = by_stage.get(stage, 0) + 1
        recruiter = vaga.get("recruiter") or "Sem responsável"
        by_recruiter[recruiter] = by_recruiter.get(recruiter, 0) + 1
        business_unit = vaga.get("business_unit") or "Sem unidade de negócio"
        by_business_unit[business_unit] = by_business_unit.get(business_unit, 0) + 1
        area = vaga.get("area") or "Sem área"
        by_area[area] = by_area.get(area, 0) + 1

    return {
        "total": len(vagas),
        "by_stage": [
            {"stage": stage, "count": by_stage.get(stage, 0)}
            for stage in FUNNEL_STAGE_ORDER
            if by_stage.get(stage)
        ],
        "by_recruiter": sorted(
            [{"recruiter": r, "count": c} for r, c in by_recruiter.items()],
            key=lambda x: -x["count"],
        ),
        "by_business_unit": sorted(
            [{"business_unit": b, "count": c} for b, c in by_business_unit.items()],
            key=lambda x: -x["count"],
        ),
        "by_area": sorted(
            [{"area": a, "count": c} for a, c in by_area.items()],
            key=lambda x: -x["count"],
        ),
    }


@router.get("/recruiters")
def list_recruiters():
    """Recrutadoras conhecidas (extraidas das vagas existentes), com
    e-mail — usado pra popular o seletor de reatribuicao no card."""
    client = AzureDevOpsClient()
    try:
        vagas = client.list_vagas()
    finally:
        client.close()

    seen: dict[str, str] = {}
    for vaga in vagas:
        email = vaga.get("recruiter_email")
        name = vaga.get("recruiter")
        if email and name:
            seen[email] = name
    return sorted(({"email": e, "name": n} for e, n in seen.items()), key=lambda r: r["name"])


@router.patch("/funnel/{job_id}")
def update_job(job_id: int, payload: JobUpdate):
    """Move a vaga de etapa e/ou troca a recrutadora — escreve direto no
    work item real do Azure DevOps (equivalente a arrastar o card ou
    reatribuir por la)."""
    client = AzureDevOpsClient()
    try:
        if payload.stage:
            client.update_stage(job_id, payload.stage)
        if payload.recruiter_email:
            client.update_recruiter(job_id, payload.recruiter_email)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    finally:
        client.close()
    return {"status": "ok"}


@router.get("/funnel/{job_id}/comments")
def get_job_comments(job_id: int):
    client = AzureDevOpsClient()
    try:
        return client.list_comments(job_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    finally:
        client.close()


@router.post("/funnel/{job_id}/comments")
def create_job_comment(job_id: int, payload: CommentCreate):
    client = AzureDevOpsClient()
    try:
        return client.add_comment(job_id, payload.text)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    finally:
        client.close()
