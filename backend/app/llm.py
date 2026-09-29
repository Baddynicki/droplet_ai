"""from typing import Any, Dict
from openai import OpenAI
import json
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def summarise_history_event(e: dict) -> Dict[str, Any]:
    prompt = f"""
"""You are a senior engineer explaining why a code change exists.

Commit ID: {e['commit_id']}
Timestamp: {e['timestamp']}
Files touched: {e['files_touched']}
Diff summary: {e['diff_summary']}

Explain:
- The reason for this change (business/technical context).
- Classify the change as bugfix, refactor, feature, performance, infra, etc.
- Any risks or follow-up work implied.
Return a JSON object with keys: reason, type, risk. """
""".strip()

    response = client.responses.create(
        model="gpt-4.1-mini",  # or "gpt-5", "gpt-5-mini", etc.
        input=prompt,
    )

    text = response.output_text.strip()

    try:
        summary = json.loads(text)
    except json.JSONDecodeError:
        summary = {
            "reason": text,
            "type": "unknown",
            "risk": "unknown",
        }

    return summary
"""

"""
from typing import Any, Dict
from google import genai
import json
from dotenv import load_dotenv
import os

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def summarise_history_event(e: dict) -> Dict[str, Any]:
    prompt = f""" """
You are a senior engineer explaining why a code change exists.

Commit ID: {e['commit_id']}
Timestamp: {e['timestamp']}
Files touched: {e['files_touched']}
Diff summary: {e['diff_summary']}

Explain:
- The reason for this change (business/technical context).
- Classify the change as bugfix, refactor, feature, performance, infra, etc.
- Any risks or follow-up work implied.
Return a JSON object with keys: reason, type, risk.
"""""".strip()

    # Interactions API
    interaction = client.interactions.create(
        model="gemini-3.5-flash",
        input=prompt,
    )
    text = interaction.output_text.strip()

    # Try to parse json and fall back to wrapping plain text
    try:
        summary = json.loads(text)
    except json.JSONDecodeError:
        summary = {
            "reason": text,
            "type": "unknown",
            "risk": "unknown",
        }

    return summary"""

    
import json
import os
import re
from typing import Any, Dict

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# OpenRouter-compatible OpenAI client
client = AsyncOpenAI(
    base_url=os.getenv(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1",
    ),
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Pick any OpenRouter model you like
MODEL = "poolside/laguna-s-2.1:free"

MAX_HISTORY_EVENTS = 12
MAX_FILES_PER_EVENT = 10
MAX_DIFF_SUMMARY_CHARS = 1_200

MAX_STRUCTURE_FILES = 80
MAX_STRUCTURE_MODULES = 40
MAX_STRUCTURE_CLASSES = 40
MAX_STRUCTURE_FUNCTIONS = 60


def truncate_text(value: Any, limit: int) -> str:
    text = str(value or "")

    if len(text) <= limit:
        return text

    return text[:limit] + "... [truncated]"


def parse_json_response(value: str) -> Dict[str, Any]:
    """Accept JSON returned with an accidental Markdown fence, but nothing else."""
    cleaned = value.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned).strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object")
    return parsed


def compact_history_event(event: Dict[str, Any]) -> Dict[str, Any]:
    files_touched = event.get("files_touched") or []

    if not isinstance(files_touched, list):
        files_touched = [str(files_touched)]

    return {
        "commit_id": str(event.get("commit_id", "")),
        "timestamp": str(event.get("timestamp", "")),
        "files_touched": [
            str(file_name)
            for file_name in files_touched[:MAX_FILES_PER_EVENT]
        ],
        "diff_summary": truncate_text(
            event.get("diff_summary", ""),
            MAX_DIFF_SUMMARY_CHARS,
        ),
    }


def compact_history_events(history_events: Any) -> list[Dict[str, Any]]:
    if not isinstance(history_events, list):
        return []

    return [
        compact_history_event(event)
        for event in history_events[:MAX_HISTORY_EVENTS]
        if isinstance(event, dict)
    ]


def compact_structure(structure_json: Any) -> Dict[str, Any]:
    if not isinstance(structure_json, dict):
        return {}

    files = structure_json.get("files") or []
    modules = structure_json.get("modules") or []
    classes = structure_json.get("classes") or []
    functions = structure_json.get("functions") or []

    return {
        "files": files[:MAX_STRUCTURE_FILES]
        if isinstance(files, list)
        else [],
        "modules": modules[:MAX_STRUCTURE_MODULES]
        if isinstance(modules, list)
        else [],
        "classes": classes[:MAX_STRUCTURE_CLASSES]
        if isinstance(classes, list)
        else [],
        "functions": functions[:MAX_STRUCTURE_FUNCTIONS]
        if isinstance(functions, list)
        else [],
    }

async def summarise_history_event(e: dict) -> Dict[str, Any]:
    event = compact_history_event(e)
    prompt = f"""
You are a senior engineer explaining why a code change exists.

Commit ID: {event['commit_id']}
Timestamp: {event['timestamp']}
Files touched: {", ".join(event['files_touched'])}
Diff summary: {event['diff_summary']}

Return one valid JSON object only:

{{
    "reason": "short explanation, maximum 2 sentences",
    "type": "bugfix|feature|refactor|performance|infra|docs|test|chore|unknown",
    "risk": "low|medium|high"
}}
""".strip()

    completion = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        extra_headers={
            "HTTP-Referer": os.getenv(
                "APP_URL",
                "http://localhost:8000",
            ),
            "X-Title": os.getenv(
                "APP_TITLE",
                "Droplet IDE Extension",
            ),
        },
    )

    text = completion.choices[0].message.content.strip()

    # Try to parse JSON; fall back to wrapping plain text
    try:
        summary = json.loads(text)
    except json.JSONDecodeError:
        summary = {
            "reason": text,
            "type": "unknown",
            "risk": "unknown",
        }

    return summary

async def extract_method_schema(
        repo_url: str,
        branch: str,
        structure_json,
        history_events,
) -> Dict[str, Any]:
    compact_code = compact_structure(structure_json)
    compact_history = compact_history_events(history_events)

    code_context = json.dumps(
        compact_code,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    history_context = json.dumps(
        compact_history,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    prompt = f"""
You are extracting a machine-readable methodology from a software repository.

Repo: {repo_url}
Branch: {branch}

Code structure:
{code_context}

Recent history:
{history_context}

Return valid JSON only with this shape:
{{
    "name": "...",
    "version": "v0.1",
    "summary": "...",
    "inputs": [
        {{"name": "...", "type": "...", "required": true, "notes": "..."}}
    ],
    "assumptions": ["..."],
    "steps": [
        {{
        "id": "...",
        "title": "...",
        "description": "...",
        "code_refs": ["path.py::symbol"],
        "history_refs": ["history_event_id"]
        }}
    ],
    "parameters": [
        {{"name": "...", "type": "...", "default": null, "notes": "..."}}
    ],
    "outputs": [
        {{"name": "...", "type": "...", "notes": "..."}}
    ],
    "failure_cases": ["..."]
}}

Rules:
- Return JSON only; no Markdown.
- Include 3 to 8 steps.
- Use only code references and history references shown above.
- Keep fields concise.
- Use no more than 8 code_refs and 3 history_refs per step.
""".strip()
    completion = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000"),
            "X-Title": os.getenv("APP_TITLE", "Droplet IDE Extension"),
        },
    )
    text = completion.choices[0].message.content.strip()
    return parse_json_response(text)


async def extract_paper_method(filename: str, paper_text: str) -> Dict[str, Any]:
    prompt = f"""
You are extracting a reproducible method from a research paper.

Paper filename: {filename}
Paper text:
{paper_text}

Return valid JSON only with this exact high-level shape:
{{
  "title": "...",
  "problem": "...",
  "datasets": [{{"name": "...", "role": "training|validation|test|benchmark", "notes": "..."}}],
  "algorithm": {{"name": "...", "summary": "...", "steps": ["..."]}},
  "parameters": [{{"name": "...", "value": "...", "purpose": "...", "tunable": true}}],
  "implementation_requirements": ["..."],
  "reported_results": ["..."],
  "limitations": ["..."],
  "confidence_notes": ["Missing or ambiguous details that need confirmation"]
}}

Rules:
- Extract only claims supported by the supplied paper text.
- Use an empty list or "not specified" when the paper does not say.
- Do not invent parameter values, datasets, or results.
- Return JSON only; no Markdown.
""".strip()
    completion = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000"),
            "X-Title": os.getenv("APP_TITLE", "Droplet IDE Extension"),
        },
    )
    return parse_json_response(completion.choices[0].message.content.strip())


async def recommend_paper_adaptation(
    repository_method: Dict[str, Any] | None,
    papers: list[Dict[str, Any]],
    instruction: str,
    source_dataset: str | None,
    target_dataset: str | None,
    parameter_overrides: Dict[str, Any],
) -> Dict[str, Any]:
    paper_context = [
        {
            "paper_id": str(paper["id"]),
            "filename": paper["filename"],
            "method": paper["method_json"],
        }
        for paper in papers
    ]
    prompt = f"""
You are a research engineering lead. Create an evidence-aware implementation plan for
adapting one or more published methods to an existing repository.

User request: {instruction}
Source dataset: {source_dataset or "not provided"}
Target dataset: {target_dataset or "not provided"}
Required parameter overrides: {json.dumps(parameter_overrides)}
Repository method schema: {json.dumps(repository_method or {})}
Selected paper methods: {json.dumps(paper_context)}

Return JSON only in this shape:
{{
  "recommendation": "short decision and rationale",
  "selected_strategy": {{
    "mode": "single-paper-adaptation|multi-paper-combination|repository-only",
    "paper_ids": ["paper UUIDs used"],
    "why": "evidence-grounded rationale"
  }},
  "compatibility": {{
    "dataset": ["required mapping/preprocessing changes"],
    "parameters": ["parameter changes and validation needs"],
    "repository": ["likely repository modules or method steps to change"]
  }},
  "implementation_plan": [
    {{"order": 1, "change": "...", "reason": "...", "validation": "..."}}
  ],
  "experiment_matrix": [
    {{"name": "...", "variables": {{"parameter": "value/range"}}, "success_metric": "..."}}
  ],
  "risks": ["..."],
  "questions": ["blocking uncertainty or missing detail"],
  "evidence": [{{"paper_id": "...", "claim": "..."}}]
}}

Rules:
- With multiple papers, recommend a combination only when their extracted methods have compatible roles.
- Never claim an unprovided experimental result. Mark assumptions and open questions clearly.
- Respect explicit parameter overrides but flag contradictions with paper evidence.
- Refer only to the selected paper IDs in evidence and selected_strategy.paper_ids.
- Return JSON only; no Markdown.
""".strip()
    completion = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000"),
            "X-Title": os.getenv("APP_TITLE", "Droplet IDE Extension"),
        },
    )
    return parse_json_response(completion.choices[0].message.content.strip())
