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

  context.subscriptions.push(
    analyzeCmd,
    runPipelineCmd,
    showHistoryCmd,
    showMethodsCmd
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

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function deactivate() {}