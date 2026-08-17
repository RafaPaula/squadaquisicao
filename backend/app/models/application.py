from datetime import datetime

from sqlalchemy import String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Application(Base):
    """Candidatura: liga um candidato a uma vaga e guarda a etapa do funil
    em que essa candidatura especifica se encontra na inHire."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    inhire_application_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)

    funnel_stage: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    status: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
