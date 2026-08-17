"""Orquestra a sincronizacao de candidatos/curriculos da inHire para a base local.

Fase 1 (ativa): `backfill_recent` traz os N candidatos mais recentes.
Fase 2 (preparada, ainda nao acionada por scheduler): `sync_since` traz apenas
o que mudou desde a ultima sincronizacao, pensada para rodar a cada 12h.

Fluxo confirmado contra a API real (testado direto na conta da DB1):
`InHireClient.list_recent_talents`/`list_talents_since` usam "Listar
talentos paginados" (`POST /talents/paginated`) — talentos da CONTA
INTEIRA, independente de vaga, sem precisar escanear vaga por vaga. Cada
item ja vem com tudo que precisamos pra popular candidato + currículo:
`name`, `email`, `phone`, `location`, `files` (com `fileCategory ==
"resumes"`) e até `resume` (texto do currículo já extraído pela própria
inHire).

Uma chamada extra por candidato (`GET /talents/{id}`, via
`InHireClient.get_talent_detail`) e' feita so' pra pegar `jobs` — as vagas
as quais o talento ja se candidatou — porque esse campo nao vem
preenchido no payload "lean" de `talents/paginated`.
"""

import mimetypes
from datetime import datetime, timezone

import ftfy
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.sync_log import SyncLog
from app.services.inhire_client import InHireClient
from app.services.resume_parser import extract_text
from app.services.storage import get_storage


def backfill_recent(db: Session, limit: int = 200) -> SyncLog:
    log = SyncLog(sync_type="backfill", status="running", started_at=_now(), items_fetched=0)
    db.add(log)
    db.commit()

    client = InHireClient()
    try:
        talents = client.list_recent_talents(limit=limit)
        log.items_fetched = len(talents)

        for talent in talents:
            try:
                created = _upsert_candidate_and_resume(db, talent, client)
            except Exception as exc:  # noqa: BLE001
                # Um talento com dado inesperado (arquivo corrompido, nome
                # estranho, etc.) nao deve derrubar o restante do lote.
                db.rollback()
                log.error_message = f"{talent.get('id')}: {exc}"
                continue
            if created:
                log.items_created += 1
            else:
                log.items_updated += 1
            db.commit()

        log.status = "success"
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.status = "failed"
        log.error_message = str(exc)
    finally:
        client.close()
        log.finished_at = _now()
        db.add(log)
        db.commit()

    return log


def sync_since(db: Session, since: datetime) -> SyncLog:
    log = SyncLog(sync_type="incremental", status="running", started_at=_now(), items_fetched=0)
    db.add(log)
    db.commit()

    client = InHireClient()
    try:
        talents = client.list_talents_since(since)
        log.items_fetched = len(talents)

        for talent in talents:
            try:
                created = _upsert_candidate_and_resume(db, talent, client)
            except Exception as exc:  # noqa: BLE001
                # Um talento com dado inesperado (arquivo corrompido, nome
                # estranho, etc.) nao deve derrubar o restante do lote.
                db.rollback()
                log.error_message = f"{talent.get('id')}: {exc}"
                continue
            if created:
                log.items_created += 1
            else:
                log.items_updated += 1
            db.commit()

        log.status = "success"
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.status = "failed"
        log.error_message = str(exc)
    finally:
        client.close()
        log.finished_at = _now()
        db.add(log)
        db.commit()

    return log


def _upsert_candidate_and_resume(db: Session, talent: dict, client: InHireClient) -> bool:
    inhire_id = str(talent["id"])
    now = _now()

    candidate = db.query(Candidate).filter_by(inhire_candidate_id=inhire_id).one_or_none()
    is_new = candidate is None

    if candidate is None:
        candidate = Candidate(
            inhire_candidate_id=inhire_id,
            first_seen_at=now,
            created_at=now,
        )
        db.add(candidate)

    candidate.full_name = talent.get("name", "")
    candidate.email = talent.get("email")
    candidate.phone = talent.get("phone")
    candidate.location = talent.get("location")
    candidate.raw_payload = talent
    candidate.applied_jobs = _fetch_applied_jobs(client, inhire_id)
    candidate.last_synced_at = now
    candidate.updated_at = now
    db.flush()

    _upsert_resume(db, candidate, talent, client, now)

    return is_new


def _fetch_applied_jobs(client: InHireClient, talent_id: str) -> list[dict]:
    """Busca as vagas as quais o talento ja se candidatou via `GET
    /talents/{id}` (confirmado na pratica — nao vem preenchido no payload
    "lean" de `talents/paginated`)."""
    detail = client.get_talent_detail(talent_id)
    jobs = []
    for job in detail.get("jobs") or []:
        stage = (job.get("talent") or {}).get("stage") or {}
        jobs.append(
            {
                "id": job.get("id"),
                "name": ftfy.fix_text(job.get("name") or ""),
                "status": job.get("status"),
                "stage": ftfy.fix_text(stage.get("name") or "") if stage.get("name") else None,
            }
        )
    return jobs


def _upsert_resume(db: Session, candidate: Candidate, talent: dict, client: InHireClient, now: datetime) -> None:
    resume_files = [f for f in (talent.get("files") or []) if f.get("fileCategory") == "resumes"]
    if not resume_files:
        return

    file_payload = resume_files[0]
    filename = file_payload["name"]
    inhire_resume_id = str(file_payload["id"])
    mime_type = mimetypes.guess_type(filename)[0]

    resume = db.query(Resume).filter_by(inhire_resume_id=inhire_resume_id).one_or_none()

    signed_url = client.get_file_signed_url("resumes", filename, inhire_resume_id)
    content = client.download_file_content(signed_url)
    storage_path = get_storage().save(f"{candidate.inhire_candidate_id}_{filename}", content)

    if resume is None:
        resume = Resume(
            inhire_resume_id=inhire_resume_id,
            candidate_id=candidate.id,
            created_at=now,
        )
        db.add(resume)

    resume.original_filename = filename
    resume.mime_type = mime_type
    resume.storage_path = storage_path
    resume.last_synced_at = now
    resume.updated_at = now

    # A inHire ja devolve o texto do curriculo extraido (`talent["resume"]`)
    # — usamos direto e so caimos pro nosso parser (pypdf/python-docx) se
    # esse campo vier vazio. Em ambos os casos passamos por `ftfy` porque
    # uma parte dos curriculos reais vem da inHire com mojibake (acentos
    # trocados, ex. "experiÃªncia") — ftfy detecta e corrige esse padrao
    # sem alterar texto que ja esta correto.
    resume_text = talent.get("resume")
    if resume_text:
        resume.raw_text = ftfy.fix_text(resume_text)
        resume.parsed_at = now
        resume.parse_error = None
    else:
        try:
            resume.raw_text = ftfy.fix_text(extract_text(content, mime_type, filename))
            resume.parsed_at = now
            resume.parse_error = None
        except Exception as exc:  # noqa: BLE001
            resume.parse_error = str(exc)

    db.flush()


def _now() -> datetime:
    return datetime.now(timezone.utc)
