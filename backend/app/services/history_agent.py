from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
import json

from ..llm import summarise_history_event

async def run_history_summariser(job_id: UUID, db: AsyncSession) -> None:
    #load content from the db
    stmt = text("""
        select id, job_id, commit_id, timestamp, files_touched, diff_summary
        from history_events
        where job_id = :job_id 
        and llm_summary is null
        order by timestamp asc;
    """)
    result = await db.execute(stmt, {"job_id": job_id})
    events = result.mappings().all()
    if not events:
        return


    #calling the llm for each event
    updates =[]
    for e in events:
        summary = await summarise_history_event(e)
        updates.append((e["id"], summary))

    #Writing llm_summary back into history_events
    update_stmt = text("""
        UPDATE history_events
        SET llm_summary = CAST(:llm_summary AS jsonb)
        WHERE id = :id
    """)
    for event_id, summary in updates:
        await db.execute(
            update_stmt,
            {"id": event_id, "llm_summary": json.dumps(summary)},
        )
    await db.commit()