from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PaperAdaptationCreate(BaseModel):
    instruction: str = Field(
        min_length=3,
        description="The requested change, such as applying the method to another dataset.",
    )
    paper_ids: list[UUID] = Field(min_length=1, max_length=3)
    source_dataset: str | None = None
    target_dataset: str | None = None
    parameter_overrides: dict[str, Any] = Field(default_factory=dict)

