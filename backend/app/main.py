from fastapi import FastAPI, Depends
from uuid import uuid4
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from .db.session import get_session
from .models.jobs import AnalysisJobCreate, AnalysisJobOut, create_job
from pathlib import Path
from .services.repo_history import clone_or_open_repo, build_change_bundles, save_history_bundles
from .routes import code, history, analyze, methods, orchestrator, papers
from .services.code_analyser import analyze_repo_code, save_code_structure
from .services.history_agent import run_history_summariser
from .services.orchestrator import run_full_pipeline

BASE_REPOS_DIR = Path("repos")
app = FastAPI()

app.include_router(history.router)
app.include_router(code.router)
app.include_router(analyze.router)
app.include_router(methods.router)
app.include_router(orchestrator.router)
app.include_router(papers.router)

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
    
    #repo and history collector
    repo_path = clone_or_open_repo(str(payload.repo_url), BASE_REPOS_DIR)
    bundles = build_change_bundles(repo_path, payload.branch)
    await save_history_bundles(db, job_id=job_id, bundles=bundles)

    structure = analyze_repo_code(repo_path)
    await save_code_structure(
        db,
        job_id=job_id,
        repo_url=str(payload.repo_url),
        branch=payload.branch,
        structure=structure,
    )

    return AnalysisJobOut(
        id=job_id,
        repo_url=payload.repo_url,
        branch=payload.branch,
        status="done",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)

    )
