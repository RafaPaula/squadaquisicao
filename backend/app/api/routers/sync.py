from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.sync_log import SyncLog
from app.services import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/backfill")
def trigger_backfill(limit: int = 200, db: Session = Depends(get_db)):
    """Fase 1: traz os `limit` candidatos/curriculos mais recentes da inHire."""
    log = sync_service.backfill_recent(db, limit=limit)
    return {
        "sync_log_id": log.id,
        "status": log.status,
        "items_fetched": log.items_fetched,
        "items_created": log.items_created,
        "items_updated": log.items_updated,
        "error_message": log.error_message,
    }


@router.post("/incremental")
def trigger_incremental(hours: int = 12, db: Session = Depends(get_db)):
    """Fase 2: traz o que mudou nas ultimas `hours` horas. Pensado para ser
    chamado por um agendador a cada 12h; por ora, disparo manual."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    log = sync_service.sync_since(db, since=since)
    return {
        "sync_log_id": log.id,
        "status": log.status,
        "items_fetched": log.items_fetched,
        "items_created": log.items_created,
        "items_updated": log.items_updated,
        "error_message": log.error_message,
    }


@router.get("/logs")
def list_sync_logs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    logs = (
        db.query(SyncLog)
        .order_by(SyncLog.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "sync_type": l.sync_type,
            "status": l.status,
            "started_at": l.started_at,
            "finished_at": l.finished_at,
            "items_fetched": l.items_fetched,
            "items_created": l.items_created,
            "items_updated": l.items_updated,
            "error_message": l.error_message,
        }
        for l in logs
    ]
