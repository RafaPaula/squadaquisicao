from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inhire_candidate_id: str
    full_name: str
    email: str | None
    phone: str | None
    location: str | None
    first_seen_at: datetime
    last_synced_at: datetime
