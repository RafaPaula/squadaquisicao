from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.schemas.resume import CATEGORY_TO_STARS, STAR_TO_CATEGORY, ResumeOut, ResumeUpdate
from app.services.storage import get_storage

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    q: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    min_score: int | None = None,
    skip: int = 0,
    limit: int = 250,
    db: Session = Depends(get_db),
):
    """Banco de curriculos com filtros para hunting: por texto do curriculo,
    nome/email/telefone do candidato, nome da vaga (dentro de
    `applied_jobs`), categoria, tag e score minimo (ranking)."""
    query = db.query(Resume).join(Resume.candidate)

    if q:
        like = f"%{q}%"
        query = query.filter(
            Resume.raw_text.ilike(like)
            | Candidate.full_name.ilike(like)
            | Candidate.email.ilike(like)
            | Candidate.phone.ilike(like)
            # applied_jobs e' uma lista de {id, name, status, stage}; busca
            # como texto simples no JSON serializado (nao ha um campo de
            # descricao completa da vaga guardado, so o nome/titulo).
            | cast(Candidate.applied_jobs, String).ilike(like)
        )
    if category:
        query = query.filter(Resume.category == category)
    if tag:
        query = query.filter(Resume.tags.any(tag))
    if min_score is not None:
        query = query.filter(Resume.score >= min_score)

    return (
        query.order_by(Resume.score.desc().nullslast(), Resume.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/stats/by-category")
def resume_category_stats(db: Session = Depends(get_db)):
    """Contagem de curriculos por categoria, usada nos cards de resumo da
    tela de revisao (quantos insuficientes/bons/otimos ja foram avaliados)."""
    rows = db.query(Resume.category, func.count(Resume.id)).group_by(Resume.category).all()
    counts = {category or "sem_categoria": total for category, total in rows}
    return {
        "insuficiente": counts.get("insuficiente", 0),
        "bom": counts.get("bom", 0),
        "otimo": counts.get("otimo", 0),
        "sem_categoria": counts.get("sem_categoria", 0),
        "total": sum(counts.values()),
    }


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Curriculo nao encontrado")
    return resume


@router.patch("/{resume_id}", response_model=ResumeOut)
def update_resume(resume_id: int, payload: ResumeUpdate, db: Session = Depends(get_db)):
    """Usado pela UI de categorizacao para marcar categoria/tags/score/notas."""
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Curriculo nao encontrado")

    data = payload.model_dump(exclude_unset=True)

    # Estrelas e categoria sao duas entradas pra mesma avaliacao: mexer
    # numa sincroniza a outra (e limpar uma limpa a outra). Se as duas
    # vierem no mesmo payload, estrelas manda.
    if "stars" in data:
        stars = data["stars"]
        data["category"] = STAR_TO_CATEGORY[stars] if stars is not None else None
    elif "category" in data:
        category = data["category"]
        data["stars"] = CATEGORY_TO_STARS[category] if category is not None else None

    for field, value in data.items():
        setattr(resume, field, value)

    db.commit()
    db.refresh(resume)
    return resume


@router.get("/{resume_id}/download")
def download_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Curriculo nao encontrado")

    content = get_storage().read(resume.storage_path)
    return Response(
        content=content,
        media_type=resume.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{resume.original_filename}"'},
    )


@router.get("/{resume_id}/view")
def view_resume(resume_id: int, db: Session = Depends(get_db)):
    """Mesmo arquivo do /download, mas com `Content-Disposition: inline`
    para poder ser embutido num <iframe> de visualizacao na tela de
    categorizacao, em vez de forcar o download."""
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Curriculo nao encontrado")

    content = get_storage().read(resume.storage_path)
    return Response(
        content=content,
        media_type=resume.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{resume.original_filename}"'},
    )
