from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.session import get_session
from ..models.papers import PaperAdaptationCreate
from ..services.adaptation_service import create_adaptation, get_adaptations
from ..services.paper_service import get_papers, ingest_paper

router = APIRouter(prefix="/analysis")


@router.post("/{job_id}/papers")
async def upload_papers(
    job_id: UUID,
    files: Annotated[list[UploadFile], File(...)],
    db: AsyncSession = Depends(get_session),
):
    existing_papers = await get_papers(db, job_id)
    if len(existing_papers) + len(files) > settings.max_papers_per_job:
        raise HTTPException(
            status_code=400,
            detail=f"Upload no more than {settings.max_papers_per_job} papers at once",
        )
    papers = []
    try:
        for file in files:
            papers.append(
                await ingest_paper(
                    db,
                    job_id,
                    file.filename or "paper.pdf",
                    await file.read(),
                )
            )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"papers": papers}


@router.get("/{job_id}/papers")
async def list_papers(job_id: UUID, db: AsyncSession = Depends(get_session)):
    return {"papers": await get_papers(db, job_id)}


@router.post("/{job_id}/paper-adaptations")
async def adapt_papers(
    job_id: UUID,
    payload: PaperAdaptationCreate,
    db: AsyncSession = Depends(get_session),
):
    try:
        return await create_adaptation(db, job_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{job_id}/paper-adaptations")
async def list_adaptations(job_id: UUID, db: AsyncSession = Depends(get_session)):
    return {"adaptations": await get_adaptations(db, job_id)}
