from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..services.orchestrator import run_full_pipeline

router = APIRouter(prefix="/analysis")

@router.post("/{job_id}/run-all")
async def run_all(
    job_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    await run_full_pipeline(job_id, db)
    return {"status": "ok"}