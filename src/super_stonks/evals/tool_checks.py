"""Did a tool call return data? — the check behind the `tool_call_succeeded` scorer.

Stdlib only, so the same function runs offline (`scorers.py`, inside `bt eval`) and
online (the code scorer pushed by `push_assets.py`).

The tools never raise on a bad ticker: they return `{"error": "No data found …"}` as a
normal result, so the span has no error flag. This check is what catches that.
"""

from __future__ import annotations

import json
from typing import Any


def tool_call_ok(output: Any) -> bool | None:
    """True when a tool's output is real data: a non-empty dict with no `error` key.

    None when there's no output to judge (e.g. the span's output hasn't been ingested yet
    when an offline scorer reads the trace) — callers leave those out of the score. A real
    failure is always an `{"error": …}` payload, never an empty output."""
    if output is None:
        return None
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except ValueError:
            return False
    return isinstance(output, dict) and bool(output) and "error" not in output


def ticker_of(tool_input: Any) -> str | None:
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except ValueError:
            return None
    return tool_input.get("ticker") if isinstance(tool_input, dict) else None
