from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID

from ..db.session import get_session
from ..models.history import HistoryEventOut

router = APIRouter()

@router.get("/analysis/{job_id}/history", response_model=list[HistoryEventOut])
async def get_history(job_id: UUID, db: AsyncSession = Depends(get_session)):
    stmt = text("""
        SELECT id, commit_id, timestamp, files_touched, diff_summary
        FROM history_events
        WHERE job_id = :job_id
        ORDER BY timestamp DESC
        LIMIT 100
    """)
    result = await db.execute(stmt, {"job_id": job_id})
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No history found for job")

    events = []
    for r in rows:
        events.append(
            HistoryEventOut(
                id=r["id"],
                commit_id=r["commit_id"],
                timestamp=r["timestamp"],
                files_touched=r["files_touched"],      # asyncpg→jsonb → Python list
                diff_summary=r["diff_summary"],        # asyncpg→jsonb → Python dict
            )
        )
    return events
