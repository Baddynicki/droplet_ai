from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from .history_agent import run_history_summariser
from .method_agent import run_method_extractor

async def run_full_pipeline(job_id: UUID, db: AsyncSession) -> None:
    await run_history_summariser(job_id, db)
    await run_method_extractor(job_id, db)