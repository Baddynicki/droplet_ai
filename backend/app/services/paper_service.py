import hashlib
import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pymupdf4llm
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..llm import extract_paper_method


def safe_filename(filename: str) -> str:
    """Keep only a filename, preventing a client from choosing a storage path."""
    cleaned = Path(filename or "paper.pdf").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", cleaned)
    return cleaned or "paper.pdf"


def validate_pdf(filename: str, content: bytes) -> None:
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported")
    if not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF")
    if len(content) > settings.max_pdf_size_mb * 1024 * 1024:
        raise ValueError(
            f"PDF exceeds the {settings.max_pdf_size_mb} MB upload limit"
        )


def extract_pdf_text(path: Path) -> str:
    markdown = pymupdf4llm.to_markdown(str(path))
    compact = markdown.strip()
    if not compact:
        raise ValueError("No readable text could be extracted from this PDF")
    if len(compact) > settings.max_paper_text_chars:
        return compact[: settings.max_paper_text_chars] + "\n\n[Text truncated]"
    return compact


async def ingest_paper(
    db: AsyncSession,
    job_id: UUID,
    filename: str,
    content: bytes,
) -> dict[str, Any]:
    validate_pdf(filename, content)
    digest = hashlib.sha256(content).hexdigest()
    existing = await db.execute(
        text("""
            SELECT id, filename, status, method_json, created_at
            FROM research_papers
            WHERE job_id = :job_id AND sha256 = :sha256
            LIMIT 1
        """),
        {"job_id": str(job_id), "sha256": digest},
    )
    existing_row = existing.mappings().first()
    if existing_row:
        return dict(existing_row)

    paper_id = uuid4()
    job_dir = settings.paper_storage_dir / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    saved_name = f"{paper_id}_{safe_filename(filename)}"
    saved_path = job_dir / saved_name
    saved_path.write_bytes(content)

    try:
        extracted_text = extract_pdf_text(saved_path)
        method_json = await extract_paper_method(filename, extracted_text)
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise

    await db.execute(
        text("""
            INSERT INTO research_papers (
                id, job_id, filename, storage_path, sha256, extracted_text, method_json, status
            ) VALUES (
                :id, :job_id, :filename, :storage_path, :sha256, :extracted_text,
                CAST(:method_json AS jsonb), 'ready'
            )
        """),
        {
            "id": str(paper_id),
            "job_id": str(job_id),
            "filename": safe_filename(filename),
            "storage_path": str(saved_path),
            "sha256": digest,
            "extracted_text": extracted_text,
            "method_json": json.dumps(method_json),
        },
    )
    await db.commit()
    return {
        "id": str(paper_id),
        "filename": safe_filename(filename),
        "status": "ready",
        "method_json": method_json,
    }


async def get_papers(db: AsyncSession, job_id: UUID) -> list[dict[str, Any]]:
    result = await db.execute(
        text("""
            SELECT id, filename, method_json, status, created_at
            FROM research_papers
            WHERE job_id = :job_id
            ORDER BY created_at ASC
        """),
        {"job_id": str(job_id)},
    )
    return [dict(row) for row in result.mappings().all()]

