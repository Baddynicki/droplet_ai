# app/services/method_agent.py
from uuid import UUID, uuid4
import json
import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date

from ..llm import extract_method_schema


def _normalize_row(row: dict) -> dict:
    """Convert UUID and datetime objects to JSON-safe values."""
    out = {}
    for k, v in row.items():
        if isinstance(v, UUID):
            out[k] = str(v)
        elif isinstance(v, (datetime, date)):
            # ISO 8601 string, JSON-safe
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def run_method_extractor(job_id: UUID, db: AsyncSession) -> None:
    code_stmt = text("""
        SELECT repo_url, branch, structure_json
        FROM code_structures
        WHERE job_id = :job_id
        LIMIT 1;
    """)
    code_result = await db.execute(code_stmt, {"job_id": str(job_id)})
    code_row = code_result.mappings().first()
    if not code_row:
        return

    history_stmt = text("""
        SELECT id, commit_id, timestamp, files_touched, diff_summary, llm_summary
        FROM history_events
        WHERE job_id = :job_id
        ORDER BY timestamp ASC;
    """)
    history_result = await db.execute(history_stmt, {"job_id": str(job_id)})
    history_rows = history_result.mappings().all()

    # Convert RowMapping -> dict and normalize UUIDs
    history_events = [_normalize_row(dict(row)) for row in history_rows]

    schema_json = await extract_method_schema(
        repo_url=code_row["repo_url"],
        branch=code_row["branch"],
        structure_json=code_row["structure_json"],
        history_events=history_events,
    )

    schema_yaml = yaml.safe_dump(
        schema_json,
        sort_keys=False,
        allow_unicode=True,
    )

    insert_stmt = text("""
        INSERT INTO method_schemas (
            id, job_id, repo_url, branch, schema_yaml, schema_json
        )
        VALUES (
            :id, :job_id, :repo_url, :branch, :schema_yaml, CAST(:schema_json AS jsonb)
        );
    """)

    await db.execute(
        insert_stmt,
        {
            "id": str(uuid4()),
            "job_id": str(job_id),
            "repo_url": code_row["repo_url"],
            "branch": code_row["branch"],
            "schema_yaml": schema_yaml,
            "schema_json": json.dumps(schema_json),
        },
    )
    await db.commit()