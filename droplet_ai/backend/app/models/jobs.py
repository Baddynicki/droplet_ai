from pydantic import BaseModel, HttpUrl
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class AnalysisJobCreate(BaseModel):
    repo_url: HttpUrl
    branch: str

class AnalysisJobOut(BaseModel):
    id: UUID
    repo_url: HttpUrl
    branch: str
    status: str
    created_at: datetime
    updated_at: datetime

async def create_job(
        db: AsyncSession,
        job_id: UUID,
        payload: AnalysisJobCreate
)-> None:
    stmt = text("""
        INSERT INTO analysis_jobs (id, repo_url, branch, status)
        VALUES (:id, :repo_url, :branch, :status)
    """)
    await db.execute(
        stmt,
        {
            "id": job_id,
            "repo_url": str(payload.repo_url),
            "branch": payload.branch,
            "status": "queued",
        },
    )
    await db.commit()