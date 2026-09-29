# Droplet AI — Repo Summariser Extension

A Visual Studio Code extension for analyzing a GitHub repository through the Droplet AI backend. It detects the Git remote of the currently opened workspace, starts an analysis job, runs the repository pipeline, and displays both historical context and an extracted methodology in VS Code webviews.

This extension is one component of the larger Droplet AI project, whose goal is to turn repositories, documents, and research sources into understandable, structured, reusable technical knowledge.

## Features

- Detects the `origin` Git remote from the open VS Code workspace.
- Creates an analysis job through the Droplet AI FastAPI backend.
- Runs the backend analysis pipeline for the selected repository.
- Displays a **History** view with commit-level rationale, change type, touched files, and estimated risk.
- Displays a **Methods** view with a machine-readable repository methodology.
- Persists the latest analysis job ID in VS Code workspace state, allowing the History and Methods commands to work after an extension reload.
- Supports HTTPS GitHub remotes and converts standard GitHub SSH remotes such as `git@github.com:owner/repo.git` to HTTPS for backend use.

## Requirements

- Visual Studio Code version compatible with the extension's `engines.vscode` setting in `package.json`.
- Node.js and npm.
- A local Droplet AI backend running before analysis begins.
- A Git repository open as the VS Code workspace.
- An `origin` remote configured in the repository's `.git/config`.

The backend is expected to be available at:

```text
http://127.0.0.1:8000
```

The configured backend must expose these endpoints:

```text
POST /analyze
POST /analysis/{jobId}/run-all
GET  /analysis/{jobId}/history
GET  /analysis/{jobId}/methods
POST /analysis/{jobId}/papers
GET  /analysis/{jobId}/papers
POST /analysis/{jobId}/paper-adaptations
GET  /analysis/{jobId}/paper-adaptations
```

## Project structure

```text
extension/
├── .vscode/                 # Extension debugging configuration
├── src/
│   ├── extension.ts          # Extension commands and webview panels
│   └── test/                 # Extension tests
├── out/                      # Generated JavaScript; ignored by Git
├── node_modules/             # Installed dependencies; ignored by Git
├── package.json              # Extension manifest and npm scripts
├── package-lock.json         # Locked dependency versions
├── tsconfig.json             # TypeScript configuration
├── eslint.config.mjs         # Lint configuration
├── .vscodeignore             # Files excluded from packaged VSIX files
└── README.md                 # This file
```

## Setup

### 1. Start the backend

From the Droplet AI backend folder, activate the Python virtual environment and start FastAPI:

```powershell
cd ..\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Confirm that the backend is running at `http://127.0.0.1:8000` before continuing.

### 2. Install extension dependencies

From this extension folder, run:

```powershell
npm install
```

This installs packages defined in `package.json` and uses `package-lock.json` to reproduce the locked dependency versions.

### 3. Compile the extension

```powershell
npm run compile
```

For development, use watch mode if it is defined in `package.json`:

```powershell
npm run watch
```

### 4. Run in the Extension Development Host

1. Open this `extension` folder in VS Code.
2. Open the **Run and Debug** view.
3. Select the extension launch configuration.
4. Press `F5`.
5. A new **Extension Development Host** window opens.
6. In that window, open a local Git repository to analyze.

## Configuration

The extension reads its backend URL from the VS Code setting:

```json
{
  "repoSummariser.backendUrl": "http://127.0.0.1:8000"
}
```

To configure it, open VS Code Settings and search for `Repo Summariser Backend Url`, or add the setting to the target workspace's `.vscode/settings.json`.

Use `127.0.0.1` rather than `localhost` if the backend only listens on IPv4.

## Commands

Open the Command Palette with `Ctrl+Shift+P` and run one of these commands.

| Command | Purpose |
|---|---|
| `Repo Summariser: Analyze Current Repo` | Detects the workspace Git remote, creates an analysis job, and runs the full backend pipeline. |
| `Repo Summariser: Run Full Pipeline` | Re-runs the history and method-extraction pipeline for the latest analysis job. |
| `Repo Summariser: Show History` | Opens the History panel for the latest analysis job. |
| `Repo Summariser: Show Methods` | Opens the Methods panel for the latest analysis job. |
| `Repo Summariser: Upload Research Paper` | Selects one to three PDFs and attaches them to the latest analysis job. |
| `Repo Summariser: Adapt Paper to Current Repo` | Selects extracted papers and collects the requested dataset or parameter changes. |
| `Repo Summariser: View Paper Adaptations` | Opens evidence-linked implementation recommendations for the latest analysis job. |
| `Repo Summariser: Focus on History View` | Focuses the contributed History view, if configured in the extension manifest. |
| `Repo Summariser: Focus on Methods View` | Focuses the contributed Methods view, if configured in the extension manifest. |

## How analysis works

1. The extension reads `.git/config` from the first open workspace folder.
2. It extracts the `origin` remote URL.
3. It sends the repository URL and branch to `POST /analyze`.
4. The backend returns an analysis job ID.
5. The extension stores that job ID in workspace state.
6. It calls `POST /analysis/{jobId}/run-all` to run the backend pipeline.
7. The backend analyzes the repository structure, summarizes selected history events, and extracts a structured methodology.
8. The extension retrieves and displays the results through the History and Methods panels.

## Expected API response shapes

### History

The History endpoint should return an array similar to:

```json
[
  {
    "commit_id": "abc123",
    "timestamp": "2026-09-08T10:30:00Z",
    "files_touched": ["app/main.py"],
    "llm_summary": {
      "reason": "Added startup validation for missing configuration.",
      "type": "bugfix",
      "risk": "low"
    }
  }
]
```

### Methods

The Methods endpoint is expected to return an outer record containing `schema_json`:

```json
{
  "repo_url": "https://github.com/owner/repository",
  "branch": "main",
  "schema_yaml": "...",
  "schema_json": {
    "name": "Repository Methodology",
    "summary": "A short explanation of the repository workflow.",
    "steps": [
      {
        "id": "step_1",
        "title": "Example step",
        "description": "What happens in this step.",
        "code_refs": ["app/main.py::run"],
        "history_refs": ["abc123"]
      }
    ]
  },
  "created_at": "2026-09-08T10:30:00Z"
}
```

The extension renders the `summary` and `steps` found inside `schema_json`.

## Troubleshooting

### `connect ECONNREFUSED 127.0.0.1:8000`

The backend is not running or the configured URL is incorrect.

```powershell
cd ..\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Set the extension setting to:

```json
{
  "repoSummariser.backendUrl": "http://127.0.0.1:8000"
}
```

### `Request failed with status code 500`

The extension connected to the backend, but the backend raised an error. Check the terminal where Uvicorn is running and inspect the full Python traceback.

Common causes include invalid source-file encoding, Git clone failures, database configuration issues, AI provider errors, or invalid model output.

### `Could not detect Git remote URL`

Make sure the workspace is a Git repository with an `origin` remote:

```powershell
git remote -v
```

If necessary, add one:

```powershell
git remote add origin https://github.com/OWNER/REPOSITORY.git
```

### History or Methods view stays empty

First run:

```text
Repo Summariser: Analyze Current Repo
```

Then check that the backend completed `/analysis/{jobId}/run-all` successfully. Open the Uvicorn terminal for any backend errors.

### `No active analysis job`

The extension has no stored job ID in the current workspace. Analyze the current repository again.

## Git hygiene

Commit source code and project configuration. Do not commit generated dependencies, compiled output, tokens, or environment files.

Recommended entries in the root `.gitignore` are:

```gitignore
# VS Code extension dependencies and build output
extension/node_modules/
extension/out/
extension/dist/
extension/*.vsix
extension/.vscode-test/
extension/.vscode-test.mjs
extension/coverage/

# Backend secrets and Python environments
backend/.env
backend/.venv/
backend/__pycache__/
**/__pycache__/
*.py[cod]

# General environment files and logs
.env
.env.*
!.env.example
*.log
.DS_Store
Thumbs.db
```

Keep these extension files under version control:

```text
package.json
package-lock.json
src/
tsconfig.json
eslint.config.mjs
.vscode/launch.json
README.md
```

## Security

Do not place GitHub tokens, OpenRouter keys, database passwords, or other secrets in this extension repository or its source code. Store backend secrets in a backend `.env` file that is excluded by `.gitignore`, and provide a safe `.env.example` file for setup instructions.

## Development notes

- The extension is written in TypeScript and compiles to JavaScript in `out/`.
- The extension uses Axios for HTTP calls to the local FastAPI backend.
- Webviews are used to render History and Methods results in VS Code.
- The extension uses `workspaceState` to persist the most recent backend analysis job ID for the current workspace.

## License

Add the license information for your project here.
