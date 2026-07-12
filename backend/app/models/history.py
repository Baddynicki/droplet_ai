from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any, Dict, List

class HistoryEventOut(BaseModel):
    id: UUID
    commit_id: str
    timestamp: datetime
    files_touched: List[str]
    diff_summary: Dict[str, Dict[str, int]]
    