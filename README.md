# Repo Summariser

Repo Summariser is a local developer tool that analyzes Git repositories and converts them into useful engineering knowledge. It combines repository structure analysis, Git-history context, and LLM-generated methodology extraction, then surfaces the results through a FastAPI backend and a Visual Studio Code extension.

Given the Git remote for an open VS Code workspace, Repo Summariser analyzes the repository, summarizes why important commits occurred, and produces a structured methodology containing inputs, assumptions, steps, parameters, outputs, and failure cases.

## Features

- Detects a GitHub repository from the `origin` remote of the repository open in VS Code.
- Analyzes repository structure, including modules, classes, and functions where supported.
- Collects Git-history events including commit IDs, timestamps, changed files, and diff summaries.
- Generates commit-level context explaining likely change rationale, classification, and risk.
- Extracts a machine-readable repository methodology in JSON and YAML-oriented form.
- Stores analysis data through the FastAPI backend and database layer.
- Displays History and Methods views directly inside VS Code.
- Uses OpenRouter through an OpenAI-compatible asynchronous Python client.

## Architecture

```text
┌──────────────────────────────────────────────────────────┐
│ VS Code Extension                                        │
│                                                          │
│ - Detects current workspace Git remote                   │
│ - Creates repository analysis jobs                       │
│ - Opens History and Methods webviews                     │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP
                        ▼
┌──────────────────────────────────────────────────────────┐
│ FastAPI Backend                                          │
│                                                          │
│ POST /analyze                                            │
│ POST /analysis/{jobId}/run-all                           │
│ GET  /analysis/{jobId}/history                           │
│ GET  /analysis/{jobId}/methods                           │
└───────┬───────────────────┬───────────────────┬──────────┘
        │                   │                   │
        ▼                   ▼                   ▼
 Repository scanner     History summariser   Method extractor
        │                   │                   │
        └───────────────────┴──────────┬────────┘
                                        ▼
                          PostgreSQL and OpenRouter
```

## Project structure

```text
repo-summariser/
├── backend/                         # FastAPI application
│   ├── app/
│   │   ├── main.py                  # FastAPI application
│   │   ├── llm.py                   # OpenRouter integration
│   │   ├── routes/                  # API route handlers
│   │   ├── services/                # Scanner, history, pipeline services
│   │   └── ...
│   ├── requirements.txt
│   ├── .env                         # Local secrets; do not commit
│   ├── .env.example                 # Safe configuration template
│   └── .venv/                       # Local virtual environment; ignored
│
├── extension/                       # VS Code extension
│   ├── .vscode/                     # Extension debug configuration
│   ├── src/
│   │   ├── extension.ts             # Commands, webviews, API calls
│   │   └── test/
│   ├── out/                         # Generated JavaScript; ignored
│   ├── node_modules/                # npm dependencies; ignored
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   └── README.md
│
├── docker-compose.yml               # Optional PostgreSQL setup
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.11 or later.
- Node.js 20 or later and npm.
- Visual Studio Code.
- Git.
- PostgreSQL, either installed locally or run through Docker Compose.
- An OpenRouter API key.
- A GitHub token if you analyze private repositories.

## Backend setup

### 1. Create the Python environment

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Create local environment variables

Create the local configuration file:

```powershell
Copy-Item .env.example .env
```

Set the needed values in `backend/.env`:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)
OPENROUTER_MODEL=(example:- poolside/laguna-s-2.1:free)

APP_URL=http://localhost:8000
APP_TITLE=Repo Summariser

# Required only if private GitHub repositories need authentication.
GITHUB_TOKEN=

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repo_summariser
```

Do not commit the `.env` file.

### 3. Start PostgreSQL

If the project uses Docker Compose:

```powershell
cd ..
docker compose up -d
docker compose ps
```

Otherwise, start your local PostgreSQL server and ensure the values in `DATABASE_URL` match your local database.

### 4. Start FastAPI

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The backend should be reachable at:

```text
http://127.0.0.1:8000
```

If available, verify it:

```powershell
curl http://127.0.0.1:8000/health
```

## Extension setup

### 1. Install dependencies

Open another terminal:

```powershell
cd extension
npm install
```

`package-lock.json` must remain next to `package.json` in the `extension/` folder and should be committed.

### 2. Compile

```powershell
npm run compile
```

For development, if the script is available:

```powershell
npm run watch
```

### 3. Launch the Extension Development Host

1. Open the root `repo-summariser` folder in VS Code.
2. Open the Run and Debug view.
3. Select the VS Code extension launch configuration.
4. Press `F5`.
5. A new Extension Development Host window opens.
6. Open a local Git repository in that window.

## Extension configuration

Set the backend URL in VS Code settings:

```json
{
  "repoSummariser.backendUrl": "http://127.0.0.1:8000"
}
```

Use `127.0.0.1` rather than `localhost` if the backend only listens on IPv4.

## Commands

Open the VS Code Command Palette using `Ctrl+Shift+P`.

| Command | Description |
|---|---|
| `Repo Summariser: Analyze Current Repo` | Detects the workspace Git remote, creates an analysis job, and runs the backend pipeline. |
| `Repo Summariser: Run Full Pipeline` | Re-runs history and method extraction for the most recent analysis job. |
| `Repo Summariser: Show History` | Displays the generated Git-history analysis. |
| `Repo Summariser: Show Methods` | Displays the extracted repository methodology. |

## Analysis workflow

1. The extension reads the open workspace’s `.git/config`.
2. It finds the `origin` repository URL.
3. It calls `POST /analyze`.
4. The backend creates an analysis job and analyzes the repository structure.
5. The extension stores the returned job ID in VS Code workspace state.
6. It calls `POST /analysis/{jobId}/run-all`.
7. The backend summarizes selected Git commits and extracts a structured method schema.
8. The extension fetches and renders History and Methods results.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `POST /analyze` | Creates a repository analysis job. |
| `POST /analysis/{jobId}/run-all` | Runs history summarization and method-schema extraction. |
| `GET /analysis/{jobId}/history` | Returns commit history and generated summaries. |
| `GET /analysis/{jobId}/methods` | Returns the extracted method-schema record. |

### Example analysis request

```powershell
curl -X POST "http://127.0.0.1:8000/analyze" `
  -H "Content-Type: application/json" `
  -d '{"repo_url":"[https://github.com/OWNER/REPOSITORY.git](https://github.com/OWNER/REPOSITORY.git)","branch":"main"}'
```

### Method-schema response

The methods endpoint returns an outer record with the actual methodology inside `schema_json`:

```json
{
  "repo_url": "[https://github.com/owner/repository](https://github.com/owner/repository)",
  "branch": "main",
  "schema_yaml": "...",
  "schema_json": {
    "name": "Repository Methodology",
    "version": "v0.1",
    "summary": "A concise explanation of the repository workflow.",
    "steps": [
      {
        "id": "step_1",
        "title": "Example step",
        "description": "What happens in this step.",
        "code_refs": ["app/main.py::run"],
        "history_refs": ["commit-id"]
      }
    ]
  },
  "created_at": "2026-09-08T10:30:00Z"
}
```

The VS Code Methods panel reads:

```text
schema_json.summary
schema_json.steps
```

## LLM and token control

The backend uses OpenRouter through the OpenAI-compatible `AsyncOpenAI` client.

Free models may be rate-limited, especially if repository structure and Git history are sent as large prompts. Keep LLM inputs compact:

- Limit the number of commits sent for history processing.
- Limit changed files included per commit.
- Truncate long diff summaries.
- Exclude `node_modules`, `.venv`, `.git`, `dist`, `build`, and generated files from repository scanning.
- Send compact history summaries to method extraction rather than raw diffs.
- Limit method extraction to a practical number of files, modules, classes, and functions.
- Request a limited number of methodology steps.

## Troubleshooting

### `connect ECONNREFUSED 127.0.0.1:8000`

The extension cannot reach FastAPI. Start the backend:

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Then set:

```json
{
  "repoSummariser.backendUrl": "http://127.0.0.1:8000"
}
```

### HTTP `500`

The extension reached the backend, but a backend exception occurred. Check the Uvicorn terminal for the full traceback.

Common causes include:

- Python file encoding/BOM errors during AST parsing.
- Large repository scans that include dependencies or generated files.
- Git clone authentication issues.
- PostgreSQL connection errors.
- OpenRouter rate limits.
- Invalid JSON generated by the selected LLM.

### OpenRouter `429`

A `429` generally means a free/shared model provider is temporarily rate-limited.

- Wait briefly before retrying.
- Reduce prompt size and LLM call concurrency.
- Use exponential backoff in the backend.
- Select another compatible model.
- Add OpenRouter credits or configure a provider key if needed.

### Method schema is invalid JSON

Ensure the prompt says:

```text
Return exactly one JSON object.
Do not return Markdown.
Do not wrap the response in code fences.
```

Before calling `json.loads`, remove optional ````json` and closing ``` code fences from model output.

### Git remote cannot be detected

Check the target repository:

```powershell
git remote -v
```

Add an origin remote if it is missing:

```powershell
git remote add origin [https://github.com/OWNER/REPOSITORY.git](https://github.com/OWNER/REPOSITORY.git)
```

## Git ignore rules

Use a root `.gitignore` similar to:

```gitignore
# Backend virtual environments and secrets
backend/.venv/
backend/venv/
backend/env/
backend/.env
backend/.env.*
backend/__pycache__/
backend/**/*.py[cod]

# Extension dependencies and generated output
extension/node_modules/
extension/out/
extension/dist/
extension/*.vsix
extension/.vscode-test/
extension/.vscode-test.mjs
extension/coverage/
extension/.nyc_output/
extension/test-results/

# Analysis working directories
backend/repos/
backend/cloned_repos/
backend/data/
repos/
cloned_repos/
data/

# General secrets, logs, and OS files
.env
.env.*
!.env.example
*.log
npm-debug.log*
.DS_Store
Thumbs.db
```

Commit these project files:

```text
backend/app/
backend/requirements.txt
backend/.env.example
extension/src/
extension/.vscode/launch.json
extension/package.json
extension/package-lock.json
extension/tsconfig.json
extension/eslint.config.mjs
extension/README.md
README.md
.gitignore
```

## Development workflow

Run the backend and extension build in separate terminals:

```powershell
# Terminal 1
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

```powershell
# Terminal 2
cd extension
npm run watch
```

Then launch the extension through `F5` and test it inside the Extension Development Host.

## License

Add your selected project license here.
