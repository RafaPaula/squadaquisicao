from datetime import datetime

from sqlalchemy import String, DateTime, Text, Integer, ARRAY, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Resume(Base):
    """Arquivo de curriculo de um candidato, com o texto extraido e os campos
    de categorizacao/ranking usados pelo banco de curriculos para hunting."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    inhire_resume_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)

    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500))

    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parse_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Categorizacao manual/futura automatica para o banco de curriculos.
    category: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    # Avaliacao em estrelas (1-5), sincronizada com `category` nos dois
    # sentidos (ver STAR_TO_CATEGORY/CATEGORY_TO_STARS no router).
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # ARRAY nativo em produção (Postgres); em SQLite (dev local sem Docker)
    # cai para JSON, já que SQLite não tem tipo array — só a criação da
    # tabela precisa funcionar nos dois; filtro por tag (`.any()`) segue
    # Postgres-only, sem uso no fluxo de sync.
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"), nullable=True
    )
    score: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    candidate = relationship("Candidate", back_populates="resumes")

    @property
    def candidate_name(self) -> str:
        return self.candidate.full_name

    @property
    def candidate_email(self) -> str | None:
        return self.candidate.email

    @property
    def candidate_location(self) -> str | None:
        return self.candidate.location

    @property
    def applied_jobs(self) -> list[dict] | None:
        return self.candidate.applied_jobs
