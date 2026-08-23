# Smart Repo Summariser – IDE Extension

## What It Is

This is a comprehensive **IDE extension** currently under development that turns GitHub repos, research PDFs, and technical blogs into **executable understanding** directly inside your editor.

Instead of generic “analyze this repo” chat, it:

- Builds a **History Layer** over the code by analyzing Git history, commit messages, and (future) PR discussions.
- Reconstructs **why** each change exists (workarounds, refactors, incident fixes), not just what the code currently does.
- Extracts a **machine‑readable method schema** (inputs, assumptions, core algorithm, parameters, outputs, failure cases) that can be exported as pipelines + scaffolded code.[file:1]

---

## Current MVP (Backend + Extension Glue)

The repo currently includes:

- A **FastAPI backend** that:
  - Accepts a repo URL + branch (`POST /analyze`).
  - Clones the repo and builds per‑commit change bundles (`history_events`).
  - Analyzes Python code structure (modules, functions, classes, tests, configs) into `code_structures`.

- API endpoints the IDE extension will call:
  - `POST /analyze` – start analysis for a repo.
  - `GET /analysis/{job_id}/history` – retrieve the History Layer (commits, files, diffs, future `llm_summary`).
  - `GET /analysis/{job_id}/code` – retrieve code structure snapshot for that job.

The VS Code (or other IDE) extension will sit on top of these APIs to display:

- A **history timeline** with “why this change exists” narratives.
- A **method/architecture view** that maps pipelines and components over time.
- Cross‑alignment between papers/blogs and the actual code for research repos.

---

## Local Dev (for the Engine)

To run the analysis engine locally:

```bash
# Infra (Postgres + Redis)
cd infra
docker compose up -d

# Backend API
cd ../backend
python -m venv .venv
source .venv/Scripts/activate  # on Windows/Git Bash
pip install -r requirements.txt
uvicorn app.main:app --reload
set GEMINI_API_KEY="your-key"
```

Example flow:

```bash
# 1. Create an analysis job
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"repo_url\":\"https://github.com/xyb/PixELM\",\"branch\":\"main\"}"

# 2. Fetch history
curl "http://localhost:8000/analysis/<job_id>/history"

# 3. Fetch code structure
curl "http://localhost:8000/analysis/<job_id>/code"

# 4. Fetch Code Analysis (Via LLM model)
curl "http://localhost:8000/analysis/<job_id>/summarise-history"
```

The IDE extension will use these same endpoints, but surface the results as rich views (history timeline, architecture diagrams, method schemas, “Apply to my data” flows) inside your editor.
