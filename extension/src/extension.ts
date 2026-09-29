import * as vscode from "vscode";
import axios from "axios";
import * as fs from "node:fs";
import * as path from "node:path";

let currentJobId: string | undefined;

const JOB_ID_STATE_KEY = "repoSummariser.currentJobId";
const JOB_ID_CONTEXT = "repoSummariser.jobIdSet";

interface MethodStep {
  id?: string;
  title?: string;
  description?: string;
  code_refs?: string[];
  history_refs?: string[];
}

interface MethodsSchema {
  name?: string;
  version?: string;
  summary?: string;
  steps?: MethodStep[];
}

interface MethodsApiResponse {
  repo_url: string;
  branch: string;
  schema_yaml: string;
  schema_json: MethodsSchema;
  created_at: string;
}

interface ResearchPaper {
  id: string;
  filename: string;
  method_json?: PaperMethod;
  status: string;
  created_at?: string;
}

interface PaperMethod {
  title?: string;
  problem?: string;
  algorithm?: {
    name?: string;
    summary?: string;
  };
}

interface PapersApiResponse {
  papers: ResearchPaper[];
}

interface PaperAdaptation {
  id: string;
  paper_ids: string[];
  instruction: string;
  source_dataset?: string;
  target_dataset?: string;
  parameter_overrides?: Record<string, unknown>;
  recommendation_json: AdaptationRecommendation;
  created_at: string;
}

interface AdaptationsApiResponse {
  adaptations: PaperAdaptation[];
}

interface AdaptationRecommendation {
  recommendation?: string;
  selected_strategy?: {
    mode?: string;
    paper_ids?: string[];
    why?: string;
  };
  compatibility?: {
    dataset?: string[];
    parameters?: string[];
    repository?: string[];
  };
  implementation_plan?: Array<{
    order?: number;
    change?: string;
    reason?: string;
    validation?: string;
  }>;
  experiment_matrix?: Array<{
    name?: string;
    variables?: Record<string, unknown>;
    success_metric?: string;
  }>;
  risks?: string[];
  questions?: string[];
  evidence?: Array<{
    paper_id?: string;
    claim?: string;
  }>;
}

export function activate(context: vscode.ExtensionContext) {
  currentJobId = context.workspaceState.get<string>(JOB_ID_STATE_KEY);

  void vscode.commands.executeCommand(
    "setContext",
    JOB_ID_CONTEXT,
    Boolean(currentJobId)
  );

  const analyzeCmd = vscode.commands.registerCommand(
    "repo-summariser.analyzeCurrentRepo",
    async () => {
      const workspaceFolders = vscode.workspace.workspaceFolders;

      if (!workspaceFolders?.length) {
        vscode.window.showErrorMessage("No workspace folder open.");
        return;
      }

      const folder = workspaceFolders[0].uri.fsPath;
      const repoUrl = await detectRepoUrl(folder);

      if (!repoUrl) {
        vscode.window.showErrorMessage(
          "Could not detect a Git remote URL. Ensure this folder is a Git repository with an origin remote."
        );
        return;
      }

      const backendUrl = getBackendUrl();

      try {
        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Repo Summariser: analyzing repository...",
            cancellable: false,
          },
          async (progress) => {
            progress.report({ message: "Creating analysis job..." });

            const analyzeResp = await axios.post(`${backendUrl}/analyze`, {
              repo_url: repoUrl,
              branch: "main",
            });

            const jobId = analyzeResp.data?.id as string | undefined;

            if (!jobId) {
              throw new Error("Backend did not return an analysis job ID.");
            }

            await setCurrentJobId(context, jobId);

            progress.report({
              message: "Extracting history and methods...",
            });

            await axios.post(`${backendUrl}/analysis/${jobId}/run-all`);

            progress.report({ message: "Complete." });
          }
        );

        vscode.window.showInformationMessage(
          "Analysis pipeline completed."
        );

        //await vscode.commands.executeCommand("repo-summariser.showHistory");
        //await vscode.commands.executeCommand("repo-summariser.showMethods");
      } catch (error: unknown) {
        showApiError("Analysis failed", error);
      }
    }
  );

  const runPipelineCmd = vscode.commands.registerCommand(
    "repo-summariser.runFullPipeline",
    async () => {
      if (!currentJobId) {
        vscode.window.showErrorMessage(
          "No active analysis job. Run 'Repo Summariser: Analyze Current Repo' first."
        );
        return;
      }

      const backendUrl = getBackendUrl();

      try {
        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Repo Summariser: running full pipeline...",
            cancellable: false,
          },
          async () => {
            await axios.post(
              `${backendUrl}/analysis/${currentJobId}/run-all`
            );
          }
        );

        vscode.window.showInformationMessage(
          "Full pipeline completed. Opening History and Methods."
        );

        await vscode.commands.executeCommand("repo-summariser.showHistory");
        await vscode.commands.executeCommand("repo-summariser.showMethods");
      } catch (error: unknown) {
        showApiError("Pipeline failed", error);
      }
    }
  );

  const showHistoryCmd = vscode.commands.registerCommand(
    "repo-summariser.showHistory",
    async () => {
      if (!currentJobId) {
        vscode.window.showErrorMessage(
          "No active analysis job. Run 'Repo Summariser: Analyze Current Repo' first."
        );
        return;
      }

      await openHistoryPanel(currentJobId);
    }
  );

  const showMethodsCmd = vscode.commands.registerCommand(
    "repo-summariser.showMethods",
    async () => {
      if (!currentJobId) {
        vscode.window.showErrorMessage(
          "No active analysis job. Run 'Repo Summariser: Analyze Current Repo' first."
        );
        return;
      }

      await openMethodsPanel(currentJobId);
    }
  );

  const uploadPaperCmd = vscode.commands.registerCommand(
    "repo-summariser.uploadResearchPaper",
    async () => {
      if (!currentJobId) {
        showMissingJobError();
        return;
      }

      const selectedFiles = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        canSelectMany: true,
        filters: { "PDF documents": ["pdf"] },
        openLabel: "Upload Research Paper",
        title: "Select up to three research papers",
      });

      if (!selectedFiles?.length) {
        return;
      }

      if (selectedFiles.length > 3) {
        vscode.window.showErrorMessage("Select no more than three PDFs.");
        return;
      }

      try {
        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Repo Summariser: uploading research papers...",
            cancellable: false,
          },
          async (progress) => {
            const form = new FormData();
            for (const file of selectedFiles) {
              progress.report({ message: `Reading ${path.basename(file.fsPath)}...` });
              const content = await fs.promises.readFile(file.fsPath);
              form.append(
                "files",
                new Blob([content], { type: "application/pdf" }),
                path.basename(file.fsPath)
              );
            }

            progress.report({ message: "Extracting paper methods..." });
            await axios.post(
              `${getBackendUrl()}/analysis/${currentJobId}/papers`,
              form
            );
          }
        );
        vscode.window.showInformationMessage(
          "Research papers uploaded and extracted."
        );
      } catch (error: unknown) {
        showApiError("Paper upload failed", error);
      }
    }
  );

  const adaptPaperCmd = vscode.commands.registerCommand(
    "repo-summariser.adaptPaperToCurrentRepo",
    async () => {
      if (!currentJobId) {
        showMissingJobError();
        return;
      }

      try {
        const papers = await fetchPapers(currentJobId);
        if (!papers.length) {
          vscode.window.showErrorMessage(
            "No research papers are attached. Run 'Repo Summariser: Upload Research Paper' first."
          );
          return;
        }

        const selectedPapers = await vscode.window.showQuickPick(
          papers.map((paper) => ({
            label: paper.filename,
            description: paper.method_json?.algorithm?.name ?? "Method extraction complete",
            detail: paper.method_json?.title ?? paper.method_json?.problem,
            paper,
          })),
          {
            canPickMany: true,
            title: "Select papers to adapt",
            placeHolder: "Choose one to three research papers",
          }
        );

        if (!selectedPapers?.length) {
          return;
        }

        const instruction = await vscode.window.showInputBox({
          title: "Adapt Paper to Current Repo",
          prompt: "Describe the requested implementation change",
          placeHolder: "Apply the method to Dataset B while retaining the current evaluation pipeline",
          validateInput: (value) =>
            value.trim().length >= 3 ? undefined : "Enter at least 3 characters.",
        });
        if (!instruction) {
          return;
        }

        const sourceDataset = await vscode.window.showInputBox({
          title: "Source Dataset",
          prompt: "Optional: dataset used in the paper",
          placeHolder: "Dataset A",
        });
        const targetDataset = await vscode.window.showInputBox({
          title: "Target Dataset",
          prompt: "Optional: dataset to use in this repository",
          placeHolder: "Dataset B",
        });
        const parameterOverrides = await getParameterOverrides();
        if (parameterOverrides === undefined) {
          return;
        }

        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Repo Summariser: preparing paper adaptation...",
            cancellable: false,
          },
          async () => {
            await axios.post(
              `${getBackendUrl()}/analysis/${currentJobId}/paper-adaptations`,
              {
                instruction,
                paper_ids: selectedPapers.map((item) => item.paper.id),
                source_dataset: sourceDataset || undefined,
                target_dataset: targetDataset || undefined,
                parameter_overrides: parameterOverrides,
              }
            );
          }
        );

        vscode.window.showInformationMessage("Paper adaptation created.");
        await openPaperAdaptationsPanel(currentJobId);
      } catch (error: unknown) {
        showApiError("Paper adaptation failed", error);
      }
    }
  );

  const viewAdaptationsCmd = vscode.commands.registerCommand(
    "repo-summariser.viewPaperAdaptations",
    async () => {
      if (!currentJobId) {
        showMissingJobError();
        return;
      }
      await openPaperAdaptationsPanel(currentJobId);
    }
  );

  context.subscriptions.push(
    analyzeCmd,
    runPipelineCmd,
    showHistoryCmd,
    showMethodsCmd,
    uploadPaperCmd,
    adaptPaperCmd,
    viewAdaptationsCmd
  );
}

function showMissingJobError(): void {
  vscode.window.showErrorMessage(
    "No active analysis job. Run 'Repo Summariser: Analyze Current Repo' first."
  );
}

function getBackendUrl(): string {
  const config = vscode.workspace.getConfiguration("repoSummariser");

  return (
    config.get<string>("backendUrl")?.replace(/\/$/, "") ??
    "http://127.0.0.1:8000"
  );
}

async function setCurrentJobId(
  context: vscode.ExtensionContext,
  jobId: string
): Promise<void> {
  currentJobId = jobId;

  await context.workspaceState.update(JOB_ID_STATE_KEY, jobId);

  await vscode.commands.executeCommand(
    "setContext",
    JOB_ID_CONTEXT,
    true
  );
}

async function detectRepoUrl(
  folderPath: string
): Promise<string | undefined> {
  const gitConfigPath = path.join(folderPath, ".git", "config");

  if (!fs.existsSync(gitConfigPath)) {
    return undefined;
  }

  const content = fs.readFileSync(gitConfigPath, "utf8");

  const httpsMatch = content.match(
    /\[remote\s+"origin"\][\s\S]*?url\s*=\s*(https?:\/\/[^\s]+)/m
  );

  if (httpsMatch?.[1]) {
    return httpsMatch[1];
  }

  const sshMatch = content.match(
    /\[remote\s+"origin"\][\s\S]*?url\s*=\s*git@github\.com:([^\s]+?)(?:\.git)?\s*$/m
  );

  if (sshMatch?.[1]) {
    return `https://github.com/${sshMatch[1].replace(/\.git$/, "")}.git`;
  }

  return undefined;
}

async function openHistoryPanel(jobId: string): Promise<void> {
  const panel = vscode.window.createWebviewPanel(
    "repoSummariserHistory",
    "Repo Summariser History",
    vscode.ViewColumn.One,
    { enableScripts: false }
  );

  panel.webview.html = getLoadingHtml("Loading history...");

  try {
    const backendUrl = getBackendUrl();
    const response = await axios.get(
      `${backendUrl}/analysis/${jobId}/history`
    );

    const history = Array.isArray(response.data)
      ? response.data
      : response.data?.history ?? [];

    panel.webview.html = getHistoryHtml(history);
  } catch (error: unknown) {
    panel.webview.html = getErrorHtml(
      `Failed to load history: ${getErrorMessage(error)}`
    );
  }
}

async function openMethodsPanel(jobId: string): Promise<void> {
  const panel = vscode.window.createWebviewPanel(
    "repoSummariserMethods",
    "Repo Summariser Methods",
    vscode.ViewColumn.Two,
    { enableScripts: false }
  );

  panel.webview.html = getLoadingHtml("Loading method schema...");

  try {
    const backendUrl = getBackendUrl();

    const response = await axios.get<MethodsApiResponse>(
      `${backendUrl}/analysis/${jobId}/methods`
    );

    const methods: MethodsSchema = response.data.schema_json;

    panel.webview.html = getMethodsHtml(methods);
  } catch (error: unknown) {
    panel.webview.html = getErrorHtml(
      `Failed to load methods: ${getErrorMessage(error)}`
    );
  }
}

async function fetchPapers(jobId: string): Promise<ResearchPaper[]> {
  const response = await axios.get<PapersApiResponse>(
    `${getBackendUrl()}/analysis/${jobId}/papers`
  );
  return Array.isArray(response.data.papers) ? response.data.papers : [];
}

async function getParameterOverrides(): Promise<Record<string, unknown> | undefined> {
  const value = await vscode.window.showInputBox({
    title: "Parameter Overrides",
    prompt: "Optional JSON object containing required parameter values",
    placeHolder: '{"learning_rate": 0.0003, "batch_size": 32}',
    value: "{}",
    validateInput: (input) => {
      if (!input.trim()) {
        return undefined;
      }
      try {
        const parsed: unknown = JSON.parse(input);
        return parsed && typeof parsed === "object" && !Array.isArray(parsed)
          ? undefined
          : "Enter a JSON object, such as {\"batch_size\": 32}.";
      } catch {
        return "Enter valid JSON.";
      }
    },
  });

  if (value === undefined) {
    return undefined;
  }
  return value.trim() ? (JSON.parse(value) as Record<string, unknown>) : {};
}

async function openPaperAdaptationsPanel(jobId: string): Promise<void> {
  const panel = vscode.window.createWebviewPanel(
    "repoSummariserPaperAdaptations",
    "Repo Summariser Paper Adaptations",
    vscode.ViewColumn.Two,
    { enableScripts: false }
  );
  panel.webview.html = getLoadingHtml("Loading paper adaptations...");

  try {
    const response = await axios.get<AdaptationsApiResponse>(
      `${getBackendUrl()}/analysis/${jobId}/paper-adaptations`
    );
    const adaptations = Array.isArray(response.data.adaptations)
      ? response.data.adaptations
      : [];
    panel.webview.html = getPaperAdaptationsHtml(adaptations);
  } catch (error: unknown) {
    panel.webview.html = getErrorHtml(
      `Failed to load paper adaptations: ${getErrorMessage(error)}`
    );
  }
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail ?? error.response?.data;

    if (typeof detail === "string") {
      return detail;
    }

    if (detail) {
      try {
        return JSON.stringify(detail);
      } catch {
        return "Backend returned an unreadable error response.";
      }
    }

    return error.message || "Could not reach the backend.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

function showApiError(prefix: string, error: unknown): void {
  console.error(`${prefix}:`, error);
  vscode.window.showErrorMessage(`${prefix}: ${getErrorMessage(error)}`);
}

function getLoadingHtml(message: string): string {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Repo Summariser</title>
</head>
<body style="font-family: var(--vscode-font-family); padding: 16px;">
  <p>${escapeHtml(message)}</p>
</body>
</html>`;
}

function getErrorHtml(message: string): string {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Repo Summariser</title>
</head>
<body style="font-family: var(--vscode-font-family); padding: 16px; color: var(--vscode-errorForeground);">
  <h2>Unable to load data</h2>
  <p>${escapeHtml(message)}</p>
  <p>Run “Repo Summariser: Analyze Current Repo” or “Repo Summariser: Run Full Pipeline” and try again.</p>
</body>
</html>`;
}

function getHistoryHtml(history: any[]): string {
  const rows = history
    .map((h) => {
      const filesTouched = Array.isArray(h.files_touched)
        ? h.files_touched.join(", ")
        : "";

      const date = h.timestamp
        ? new Date(h.timestamp).toLocaleString()
        : "Unknown date";

      return `
      <div style="margin-bottom: 12px; border: 1px solid var(--vscode-widget-border); padding: 8px; border-radius: 4px;">
        <div style="font-weight: 600; margin-bottom: 4px;">
          ${escapeHtml(String(h.commit_id ?? "Unknown commit"))} – ${escapeHtml(date)}
        </div>
        <div style="font-size: 0.9em; color: var(--vscode-descriptionForeground);">
          Files: ${escapeHtml(filesTouched || "None recorded")}
        </div>
        ${
          h.llm_summary
            ? `
          <div style="margin-top: 6px; font-size: 0.95em;">
            <strong>Type:</strong> ${escapeHtml(String(h.llm_summary.type ?? "unknown"))} |
            <strong>Risk:</strong> ${escapeHtml(String(h.llm_summary.risk ?? "unknown"))}
          </div>
          <div style="margin-top: 4px;">
            ${escapeHtml(String(h.llm_summary.reason ?? ""))}
          </div>
        `
            : ""
        }
      </div>`;
    })
    .join("");

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Repo Summariser History</title>
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; }
  </style>
</head>
<body>
  <h2>History</h2>
  ${rows || "<p>No history events were returned for this analysis.</p>"}
</body>
</html>`;
}

function getMethodsHtml(methods: MethodsSchema): string {
  const summary = methods.summary ?? "";
  const steps: MethodStep[] = methods.steps ?? [];

  const stepsHtml = steps
    .map(
      (step: MethodStep, index: number) => `
      <div style="margin-bottom: 16px; border: 1px solid var(--vscode-widget-border); padding: 10px; border-radius: 4px;">
        <div style="font-weight: 600; margin-bottom: 4px;">
          ${index + 1}. ${escapeHtml(
            step.title ?? step.id ?? "Untitled step"
          )}
        </div>
        <div style="font-size: 0.95em; margin-bottom: 6px;">
          ${escapeHtml(step.description ?? "")}
        </div>
        <div style="font-size: 0.85em; color: var(--vscode-descriptionForeground);">
          <div><strong>Code refs:</strong> ${escapeHtml(
            step.code_refs?.join(", ") ?? "None"
          )}</div>
          <div><strong>History refs:</strong> ${escapeHtml(
            step.history_refs?.join(", ") ?? "None"
          )}</div>
        </div>
      </div>`
    )
    .join("");

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Repo Summariser Methods</title>
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; }
    h2 { margin-top: 0; }
  </style>
</head>
<body>
  <h2>Method Summary</h2>
  <p style="margin-bottom: 16px;">${escapeHtml(summary)}</p>
  <h3>Steps</h3>
  ${stepsHtml || "<p>No method steps were extracted.</p>"}
</body>
</html>`;
}

function getPaperAdaptationsHtml(adaptations: PaperAdaptation[]): string {
  const cards = adaptations
    .map((adaptation) => {
      const recommendation = adaptation.recommendation_json ?? {};
      const strategy = recommendation.selected_strategy;
      const compatibility = recommendation.compatibility;
      const plan = recommendation.implementation_plan ?? [];
      const experiments = recommendation.experiment_matrix ?? [];
      const evidence = recommendation.evidence ?? [];

      const planHtml = plan
        .map(
          (step, index) => `
          <li>
            <strong>${escapeHtml(String(step.order ?? index + 1))}. ${escapeHtml(step.change ?? "Change")}</strong><br>
            ${escapeHtml(step.reason ?? "")}<br>
            <span class="muted">Validate: ${escapeHtml(step.validation ?? "Not specified")}</span>
          </li>`
        )
        .join("");
      const experimentHtml = experiments
        .map(
          (experiment) => `
          <li><strong>${escapeHtml(experiment.name ?? "Experiment")}</strong>: ${escapeHtml(
            JSON.stringify(experiment.variables ?? {})
          )}<br><span class="muted">Success metric: ${escapeHtml(
            experiment.success_metric ?? "Not specified"
          )}</span></li>`
        )
        .join("");
      const evidenceHtml = evidence
        .map(
          (item) => `<li><span class="muted">${escapeHtml(
            item.paper_id ?? "Paper"
          )}</span>: ${escapeHtml(item.claim ?? "")}</li>`
        )
        .join("");

      return `
      <section class="card">
        <h2>${escapeHtml(recommendation.recommendation ?? adaptation.instruction)}</h2>
        <p class="muted">Created ${escapeHtml(
          adaptation.created_at ? new Date(adaptation.created_at).toLocaleString() : "Unknown date"
        )}</p>
        <h3>Request</h3>
        <p>${escapeHtml(adaptation.instruction)}</p>
        <dl>
          <dt>Source dataset</dt><dd>${escapeHtml(adaptation.source_dataset ?? "Not specified")}</dd>
          <dt>Target dataset</dt><dd>${escapeHtml(adaptation.target_dataset ?? "Not specified")}</dd>
          <dt>Strategy</dt><dd>${escapeHtml(strategy?.mode ?? "Not specified")}</dd>
        </dl>
        <p>${escapeHtml(strategy?.why ?? "")}</p>
        ${getAdaptationListHtml("Dataset compatibility", compatibility?.dataset)}
        ${getAdaptationListHtml("Parameter compatibility", compatibility?.parameters)}
        ${getAdaptationListHtml("Repository changes", compatibility?.repository)}
        <h3>Implementation plan</h3>
        ${planHtml ? `<ol>${planHtml}</ol>` : "<p>No implementation steps were returned.</p>"}
        <h3>Experiment matrix</h3>
        ${experimentHtml ? `<ul>${experimentHtml}</ul>` : "<p>No experiments were returned.</p>"}
        ${getAdaptationListHtml("Risks", recommendation.risks)}
        ${getAdaptationListHtml("Open questions", recommendation.questions)}
        <h3>Evidence</h3>
        ${evidenceHtml ? `<ul>${evidenceHtml}</ul>` : "<p>No evidence records were returned.</p>"}
      </section>`;
    })
    .join("");

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Repo Summariser Paper Adaptations</title>
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; line-height: 1.45; }
    h1 { margin-top: 0; }
    h2 { font-size: 1.1em; margin: 0 0 4px; }
    h3 { font-size: 1em; margin: 18px 0 6px; }
    .card { border: 1px solid var(--vscode-widget-border); border-radius: 4px; padding: 14px; margin-bottom: 14px; }
    .muted { color: var(--vscode-descriptionForeground); font-size: 0.9em; }
    dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; }
    dt { font-weight: 600; }
    dd { margin: 0; }
    li { margin-bottom: 8px; }
  </style>
</head>
<body>
  <h1>Paper Adaptations</h1>
  ${cards || "<p>No paper adaptations have been created for this analysis.</p>"}
</body>
</html>`;
}

function getAdaptationListHtml(title: string, items: string[] | undefined): string {
  if (!items?.length) {
    return "";
  }
  return `
  <h3>${escapeHtml(title)}</h3>
  <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function deactivate() {}
