import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..llm import recommend_paper_adaptation
from ..models.papers import PaperAdaptationCreate


async def create_adaptation(
    db: AsyncSession,
    job_id: UUID,
    request: PaperAdaptationCreate,
) -> dict[str, Any]:
    paper_result = await db.execute(
        text("""
            SELECT id, filename, method_json
            FROM research_papers
            WHERE job_id = :job_id AND id = ANY(CAST(:paper_ids AS uuid[]))
            ORDER BY created_at ASC
        """),
        {"job_id": str(job_id), "paper_ids": [str(value) for value in request.paper_ids]},
    )
    papers = [dict(row) for row in paper_result.mappings().all()]
    requested_ids = {str(value) for value in request.paper_ids}
    if {str(paper["id"]) for paper in papers} != requested_ids:
        raise ValueError("One or more papers do not belong to this analysis job")

    repo_result = await db.execute(
        text("""
            SELECT schema_json FROM method_schemas
            WHERE job_id = :job_id
            ORDER BY created_at DESC LIMIT 1
        """),
        {"job_id": str(job_id)},
    )
    repo_row = repo_result.mappings().first()
    recommendation = await recommend_paper_adaptation(
        repository_method=repo_row["schema_json"] if repo_row else None,
        papers=papers,
        instruction=request.instruction,
        source_dataset=request.source_dataset,
        target_dataset=request.target_dataset,
        parameter_overrides=request.parameter_overrides,
    )

    adaptation_id = uuid4()
    await db.execute(
        text("""
            INSERT INTO paper_adaptations (
                id, job_id, paper_ids, instruction, source_dataset, target_dataset,
                parameter_overrides, recommendation_json
            ) VALUES (
                :id, :job_id, CAST(:paper_ids AS jsonb), :instruction, :source_dataset,
                :target_dataset, CAST(:parameter_overrides AS jsonb),
                CAST(:recommendation_json AS jsonb)
            )
        """),
        {
            "id": str(adaptation_id),
            "job_id": str(job_id),
            "paper_ids": json.dumps([str(value) for value in request.paper_ids]),
            "instruction": request.instruction,
            "source_dataset": request.source_dataset,
            "target_dataset": request.target_dataset,
            "parameter_overrides": json.dumps(request.parameter_overrides),
            "recommendation_json": json.dumps(recommendation),
        },
    )
    await db.commit()
    return {"id": str(adaptation_id), "recommendation": recommendation}


async def get_adaptations(db: AsyncSession, job_id: UUID) -> list[dict[str, Any]]:
    result = await db.execute(
        text("""
            SELECT id, paper_ids, instruction, source_dataset, target_dataset,
                   parameter_overrides, recommendation_json, created_at
            FROM paper_adaptations WHERE job_id = :job_id ORDER BY created_at DESC
        """),
        {"job_id": str(job_id)},
    )
    return [dict(row) for row in result.mappings().all()]
