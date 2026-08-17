from datetime import datetime

from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Job(Base):
    """Vaga espelhada da inHire. recruiter_name e job_type/department viabilizam
    as visoes por recrutador e por tipo de vaga que a inHire nao oferece."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    inhire_job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    title: Mapped[str] = mapped_column(String(255))
    job_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recruiter_name: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    status: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)

    # Referencia ao work item do Azure DevOps que acompanha essa vaga (fase futura).
    azure_devops_work_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    applications = relationship("Application", back_populates="job")
