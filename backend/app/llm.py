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


async def summarise_history_event(e: dict) -> Dict[str, Any]:
    prompt = f"""
You are a senior engineer explaining why a code change exists.

Commit ID: {e['commit_id']}
Timestamp: {e['timestamp']}
Files touched: {e['files_touched']}
Diff summary: {e['diff_summary']}

Explain:
- The reason for this change (business/technical context).
- Classify the change as bugfix, refactor, feature, performance, infra, etc.
- Any risks or follow-up work implied.

Return a JSON object with keys:
reason, type, risk.
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
    prompt = f"""
You are extracting a machine-readable methodology from a software repository.

Repo: {repo_url}
Branch: {branch}

Code structure:
{json.dumps(structure_json)[:120000]}

History events:
{json.dumps(history_events)[:120000]}

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
- Infer the actual method or pipeline implemented by the repository.
- Prefer code_refs grounded in the provided structure.
- Use history_refs only where they add real rationale.
- Do not return markdown.
- Return valid JSON only.
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
    return json.loads(text)


