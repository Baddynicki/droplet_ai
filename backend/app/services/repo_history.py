import json
from pathlib import Path
from uuid import UUID, uuid4
from typing import List, Dict, Any

from git import Repo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

#hardcode base_dir 's path rn 
base_dir = Path("repos")
def clone_or_open_repo(repo_url: str, base_dir: Path) -> Path:  #basic local cache for the repo
    """
    Clone repo if not present
    else make a new
    """
    repo_name = repo_url.rstrip("/").split("/")[-1] #Baddynicki/droplet_ai
    target_dir = base_dir/ repo_name
    if target_dir.exists():
        repo = Repo(str(target_dir))
    else:
        repo = Repo.clone_from(repo_url, str(target_dir))

    return Path(repo.working_dir)

#per-commit change metadata
def build_change_bundles(repo_path: Path, branch: str, max_commits: int = 50) -> List[Dict[str, Any]]:
    """
    Read recent commits on the branch and build simple change bundles.
    """
    repo = Repo(str(repo_path))
    commits = list(repo.iter_commits(branch))[:max_commits]  # latest N commits

    bundles: List[Dict[str, Any]] = []
    for commit in commits:
        # basic metadata
        commit_id = commit.hexsha
        timestamp = commit.committed_datetime

        # files touched: use commit.stats
        stats = commit.stats
        files_touched = list(stats.files.keys())  # file path

        # simple diff summary: lines added/removed per file
        diff_summary = {
            f: {
                "insertions": stats.files[f]["insertions"],
                "deletions": stats.files[f]["deletions"],
            }
            for f in files_touched
        }

        bundles.append(
            {
                "commit_id": commit_id,
                "timestamp": timestamp,
                "files_touched": files_touched,
                "diff_summary": diff_summary,
            }
        )

    return bundles

#saves bundles in history_events 
async def save_history_bundles(
        db: AsyncSession,
        job_id: UUID,
        bundles: List[Dict[str, Any]],
) -> None:
    stmt = text("""
        INSERT INTO history_events (id, job_id, commit_id, timestamp, files_touched, diff_summary)
        VALUES (:id, :job_id, :commit_id, :timestamp, CAST(:files_touched AS jsonb), CAST(:diff_summary AS jsonb))
                """)
    for bundle in bundles:
        await db.execute(
            stmt,{
                "id": uuid4(), 
                "job_id": job_id,
                "commit_id": bundle["commit_id"],
                "timestamp": bundle["timestamp"],
                "files_touched": json.dumps(bundle["files_touched"]),
                "diff_summary": json.dumps(bundle["diff_summary"]),
            },
        )
    await db.commit()

