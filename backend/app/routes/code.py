from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID

from ..db.session import get_session

router = APIRouter()


@router.get("/analysis/{job_id}/code")
async def get_code_structure(job_id: UUID, db: AsyncSession = Depends(get_session)):
    stmt = text("SELECT structure_json FROM code_structures WHERE job_id = :job_id")
    result = await db.execute(stmt, {"job_id": job_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No code structure for job")
    return row["structure_json"]