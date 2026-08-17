from datetime import datetime

from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Candidate(Base):
    """Candidato espelhado da inHire. inhire_candidate_id e o identificador
    do candidato no ATS de origem, usado para upsert em cada sincronizacao."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    inhire_candidate_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Payload original da inHire, guardado para nao perder informacao
    # ainda nao mapeada em colunas proprias.
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    # Vagas as quais o candidato ja se candidatou, vindas de `GET
    # /talents/{id}` (`InHireClient.get_talent_detail`). Lista de
    # {id, name, status, stage}.
    applied_jobs: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    applications = relationship("Application", back_populates="candidate")
    resumes = relationship("Resume", back_populates="candidate")
