from fastapi import FastAPI, Depends
from uuid import uuid4
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from .db.session import get_session
from .models.jobs import AnalysisJobCreate, AnalysisJobOut, create_job

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/analyze", response_model = AnalysisJobOut)
async def analyze_repo(
    payload: AnalysisJobCreate,
    db: AsyncSession = Depends(get_session)
):
    job_id = uuid4()
    await create_job(db, job_id=job_id, payload=payload)
    #add orchestrator 
    return AnalysisJobOut(
        id=job_id,
        repo_url=payload.repo_url,
        branch=payload.branch,
        status="queued",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)

    )

#@app.post("/analyze")
#async def analyze_repo()
