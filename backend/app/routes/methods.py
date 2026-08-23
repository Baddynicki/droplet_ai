from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.session import get_session
from ..services.method_agent import run_method_extractor


router = APIRouter(prefix="/analysis")

@router.post("/{job_id}/extract-methods")
async def extract_methods(
    job_id: UUID, 
    db: AsyncSession = Depends(get_session)
):
    await run_method_extractor(job_id, db)
    return {"status": "ok"}

from sqlalchemy import text
@router.get("/{job_id}/methods")
async def get_methods(
    job_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    stmt = text("""
        SELECT repo_url, branch, schema_yaml, schema_json, created_at
        FROM method_schemas
        WHERE job_id = :job_id
        ORDER BY created_at DESC
        LIMIT 1;
""")
    result = await db.execute(stmt, {"job_id": str(job_id)})
    row = result.mappings().first()
    return dict(row) if row else {}