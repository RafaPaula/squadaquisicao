from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ResumeCategory = Literal["insuficiente", "bom", "otimo"]

# Sincronizacao bidirecional entre estrelas e categoria (definida com o
# usuario): 1-2 estrelas = Insuficiente, 3-4 = Bom, 5 = Otimo. No sentido
# categoria -> estrelas (quando a categoria e' marcada direto, sem passar
# pelas estrelas) usa-se um valor representativo de cada faixa.
STAR_TO_CATEGORY: dict[int, ResumeCategory] = {
    1: "insuficiente",
    2: "insuficiente",
    3: "bom",
    4: "bom",
    5: "otimo",
}
CATEGORY_TO_STARS: dict[ResumeCategory, int] = {
    "insuficiente": 2,
    "bom": 3,
    "otimo": 5,
}


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inhire_resume_id: str
    candidate_id: int
    candidate_name: str
    candidate_email: str | None
    candidate_location: str | None
    applied_jobs: list[dict] | None
    original_filename: str
    mime_type: str | None
    category: ResumeCategory | None
    stars: int | None
    tags: list[str] | None
    score: int | None
    notes: str | None
    raw_text: str | None
    parsed_at: datetime | None
    created_at: datetime


class ResumeUpdate(BaseModel):
    category: ResumeCategory | None = None
    stars: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] | None = None
    score: int | None = None
    notes: str | None = None
