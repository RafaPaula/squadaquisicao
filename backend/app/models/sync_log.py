from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncLog(Base):
    """Registro de cada execucao de sincronizacao com a inHire (backfill
    inicial ou, futuramente, a rotina incremental a cada 12h)."""

    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_type: Mapped[str] = mapped_column(String(30))  # backfill | incremental
    status: Mapped[str] = mapped_column(String(30))  # running | success | failed

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_created: Mapped[int] = mapped_column(Integer, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
