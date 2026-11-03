"""Turn on the Patterns automation for a project (`make patterns`).

Patterns is a scheduled Loop automation that reads the project's recent traces and
records recurring behaviors (silent tool failures, wrong outputs, inefficiencies) as
Pattern records. The bt CLI can't create it, so this hits the REST API
(`/v1/project_automation`). Idempotent: if the project already has an automation named
"Patterns", it's left as-is.

It isn't told what to look for — the seed's share-class tickers (see seed/scenarios.py)
are found from the traces alone.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()

API = os.environ.get("BRAINTRUST_API_URL", "https://api.braintrust.dev").rstrip("/")
KEY = os.environ["BRAINTRUST_API_KEY"]
PROJECT = os.environ["BRAINTRUST_DEFAULT_PROJECT"]
NAME = "Patterns"
_HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# Daily at 9am PT over a 30-day window. A Pattern only stays active while matching
# traces keep arriving (activity in the last two weekdays), so top up the seed before
# the workshop.
CONFIG = {
    "event_type": "windowed",
    "product_origin": "patterns",
    "window": {
        "window_seconds": 30 * 24 * 3600,
        "schedule": {"type": "cron", "cron_expression": "0 9 * * *", "timezone": "America/Los_Angeles"},
        "evaluation_delay_seconds": 0,
    },
    "loop": {
        "prompt": (
            "Load and follow `braintrust/pattern-analysis`. Autonomously investigate the current "
            "automation window and create or update the representative set of material patterns."
        ),
        "include_trigger_input": False,
        "agent_slug": "loop-chat",
        "auto_approve_tools": ["new_pattern", "update_pattern"],
        "reasoning_effort": "xhigh",
    },
    "actions": [],
}


def _req(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers=_HEADERS, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read() or "{}")


def _project_id() -> str:
    objs = _req("GET", f"/v1/project?project_name={urllib.parse.quote(PROJECT)}").get("objects", [])
    if not objs:
        raise SystemExit(f"project '{PROJECT}' not found")
    return objs[0]["id"]


def main() -> None:
    project_id = _project_id()
    existing = [
        a for a in _req("GET", f"/v1/project_automation?project_id={project_id}").get("objects", [])
        if a.get("config", {}).get("product_origin") == "patterns"
    ]
    if existing:
        print(f"[patterns] already enabled on '{PROJECT}' ({existing[0]['name']}, {existing[0]['id']})")
        return
    created = _req("POST", "/v1/project_automation", {
        "project_id": project_id,
        "name": NAME,
        "description": f"Daily Patterns analysis of {PROJECT} traces (workshop).",
        "config": CONFIG,
    })
    print(f"[patterns] enabled on '{PROJECT}' ({created.get('id')}) — runs daily 9am PT")


if __name__ == "__main__":
    main()
