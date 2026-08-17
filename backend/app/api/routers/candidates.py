from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateOut

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Candidate)
    if q:
        query = query.filter(Candidate.full_name.ilike(f"%{q}%"))
    return query.order_by(Candidate.first_seen_at.desc()).offset(skip).limit(limit).all()


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    return db.get(Candidate, candidate_id)
