"""Push the tool-success scorer to Braintrust as an online code scorer.

This is the workshop's reveal (PARTICIPANT.md step 12), run **after** the offline experiments
show tools returning `{"error": …}` for dotted share-class tickers — not part of pre-seed
provisioning. Nothing else is pushed: attendees' projects stay clean, and the only
online score is the one the story is about.

Online it runs on **every tool span** (`make automations` sets the filter): input = the
tool's arguments, output = what the tool returned. Same check as the offline
`scorers.tool_call_succeeded` (`tool_checks.tool_call_ok`).

Push with `make push-scorer`.
"""

import os
from typing import Any

try:  # local push reads .env; the remote scorer runtime has no python-dotenv (or need for it)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from braintrust import projects
from pydantic import BaseModel

from super_stonks.evals.tool_checks import ticker_of, tool_call_ok

PROJECT = os.environ.get("BRAINTRUST_DEFAULT_PROJECT", "super-stonks")
project = projects.create(name=PROJECT)


class ToolSpanParams(BaseModel):
    input: Any = None
    output: Any = None


def tool_call_succeeded(input: Any = None, output: Any = None, **kwargs: Any) -> dict:
    ok = tool_call_ok(output)
    return {
        "name": "tool_call_succeeded",
        "score": None if ok is None else (1.0 if ok else 0.0),
        "metadata": {"ticker": ticker_of(input), "error": None if ok else output},
    }


project.scorers.create(
    name="tool_call_succeeded",
    slug="tool_call_succeeded",
    description="1 if the tool returned data, 0 if it returned an error payload.",
    parameters=ToolSpanParams,
    handler=tool_call_succeeded,
    if_exists="replace",
)
