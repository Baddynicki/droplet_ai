from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..services.history_agent import run_history_summariser

router = APIRouter()

@router.post("/analysis/{job_id}/summarise-history")
async def summarise_history(
    job_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    await run_history_summariser(job_id, db)
    return {"status": "ok"}