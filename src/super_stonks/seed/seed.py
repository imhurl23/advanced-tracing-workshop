"""Drive the (toolless) agent to seed production-like traces.

The span tree and the logged input/output/metadata mirror the Streamlit app
(`super_stonks/app.py`) exactly, so seeded "sims" are indistinguishable in shape from
real traffic:

    stonks-sessions (root, metadata: entrypoint/conversation_id/project/bucket)
    └─ turn_{n}      (input = user_input string; metadata: turn/tool_names/message_count)
       └─ { LLM span, TOOL span }
    (the root/conversation span is logged each turn with input = the list of user messages)

Topics must be enabled first — the Makefile makes `topics` upstream of seeding.
Sessions are a mix of single- and multi-turn (see scenarios.py).

    uv run python -m super_stonks.seed.seed --count 10
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import uuid
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # OPENAI_API_KEY (agent) + BRAINTRUST_API_KEY (SDK)

import braintrust

from super_stonks.agent.config import get_braintrust_project_name, init_braintrust_logger
from super_stonks.seed.scenarios import build

ENTRYPOINT = "seed"


def _extract_assistant_reply(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("content"):
            return str(message["content"])
    return "I could not produce a response for that request."


def _extract_tool_names(messages: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for message in messages:
        for tool_call in message.get("tool_calls", []) or []:
            name = (tool_call.get("function") or {}).get("name")
            if name:
                names.append(name)
    return names


def _seed_session(scenario: dict, project: str, run_id: str) -> dict:
    from super_stonks.agent.agent import graph

    conversation_id = str(uuid.uuid4())
    with braintrust.start_span(
        name="stonks-sessions",
        span_attributes={"type": "task"},
        metadata={
            "entrypoint": ENTRYPOINT,
            "conversation_id": conversation_id,
            "project": project,
            "bucket": scenario["bucket"],
            "synthetic": False,
            "seed_run_id": run_id,
            "scenario_family": scenario.get("scenario_family", scenario["bucket"]),
            "variant": scenario.get("variant"),
        },
    ) as session:
        agent_messages: list[dict] = []
        observed_turns = []
        for turn_idx, user_input in enumerate(scenario["turns"]):
            previous_count = len(agent_messages)
            agent_messages.append({"role": "user", "content": user_input})

            with braintrust.start_span(name=f"turn_{turn_idx}", span_attributes={"type": "task"}) as span:
                result = graph.invoke({"messages": agent_messages})
                agent_messages = result["messages"]
                new_messages = agent_messages[previous_count:]
                tool_names = _extract_tool_names(new_messages)
                reply = _extract_assistant_reply(agent_messages)
                observed_turns.append({
                    "input": user_input,
                    "output": reply,
                    "tool_names": tool_names,
                    "tool_results": [m["content"] for m in new_messages if m.get("role") == "tool"],
                })

                span.log(
                    input=user_input,
                    output=reply,
                    metadata={
                        "entrypoint": ENTRYPOINT,
                        "conversation_id": conversation_id,
                        "turn": turn_idx + 1,
                        "tool_names": tool_names,
                        "message_count": len(agent_messages),
                        "synthetic": False,
                        "seed_run_id": run_id,
                    },
                )
                session.log(
                    input=[m for m in agent_messages if m.get("role") == "user"],
                    output=reply,
                    metadata={
                        "entrypoint": ENTRYPOINT,
                        "conversation_id": conversation_id,
                        "turns": turn_idx + 1,
                        "message_count": len(agent_messages),
                        "last_tool_names": tool_names,
                    },
                )
    braintrust.flush()
    return {
        "seed_run_id": run_id,
        "conversation_id": conversation_id,
        "root_span_id": session.root_span_id,
        "bucket": scenario["bucket"],
        "completed": True,
        "turns": observed_turns,
    }


def run(count: int, scenario_set: str = "workshop", seed: int = 0, workers: int = 1,
        families: tuple[str, ...] | None = None, report: Path | None = None) -> None:
    init_braintrust_logger()  # sets the active logger → spans land in the project
    project = get_braintrust_project_name()
    if scenario_set == "recurring":
        from super_stonks.seed.recurring import FAMILIES, build as build_recurring

        scenarios = build_recurring(count, seed, families or FAMILIES)
    elif scenario_set == "patterns":
        from super_stonks.seed.patterns import FAILURES, build as build_patterns

        # Use only the adversarial user inputs. Outputs/tools come from the real
        # unmodified graph; scenario buckets are test intents, not observed failures.
        candidates = build_patterns((count + len(FAILURES) - 1) // len(FAILURES), 0, seed)
        scenarios = [{"bucket": f"probe_{s['bucket']}",
                      "turns": [t["input"] for t in s["turns"]]} for s in candidates[:count]]
    else:
        scenarios = build(count, seed)
    turns_total = sum(len(s["turns"]) for s in scenarios)
    run_id = str(uuid.uuid4())
    print(f"[seed] run {run_id}: {len(scenarios)} sessions ({turns_total} turns) into '{project}' …", flush=True)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)

    errors = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_seed_session, scenario, project, run_id) for scenario in scenarios]
        for i, future in enumerate(as_completed(futures), start=1):
            try:
                result = future.result()
            except Exception as exc:
                errors += 1
                print(f"  session failed: {type(exc).__name__}", flush=True)
                result = {"seed_run_id": run_id, "completed": False, "error_type": type(exc).__name__}
            if report:
                with report.open("a") as output:
                    output.write(json.dumps(result) + "\n")
            if i % 10 == 0 or i == len(scenarios):
                print(f"  {i}/{len(scenarios)} ({errors} failed)", flush=True)

    print(f"[seed] done: {count - errors} completed; {errors} failed.")
    if errors:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Super Stonks traces.")
    parser.add_argument("--count", type=int, default=10, help="number of sessions/traces to seed")
    parser.add_argument("--scenario-set", choices=["workshop", "patterns", "recurring"], default="workshop")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gateway", action="store_true", help="use Braintrust Gateway with BRAINTRUST_API_KEY")
    parser.add_argument("--workers", type=int, default=1, help="concurrent independent sessions")
    parser.add_argument("--families", help="comma-separated recurring scenario families (default: all)")
    parser.add_argument("--report", type=Path, help="append actual responses and tools to local JSONL")
    args = parser.parse_args()
    if args.count < 1 or args.workers < 1:
        parser.error("count and workers must be positive")
    families = tuple(args.families.split(",")) if args.families else None
    if families:
        from super_stonks.seed.recurring import FAMILIES

        if args.scenario_set != "recurring" or any(f not in FAMILIES for f in families):
            parser.error(f"--families requires recurring scenarios and names from {FAMILIES}")
    if args.gateway:
        key = os.environ.get("BRAINTRUST_API_KEY", "").strip()
        if not key:
            parser.error("--gateway requires BRAINTRUST_API_KEY")
        # Applied before importing the graph, whose OpenAI client reads these.
        os.environ["OPENAI_BASE_URL"] = "https://gateway.braintrust.dev"
        os.environ["OPENAI_API_KEY"] = key
        from super_stonks.agent import agent

        # Bound stalled gateway requests during a batch; keep failures in traces.
        agent._client = agent._client.with_options(timeout=45, max_retries=0)
    run(args.count, args.scenario_set, args.seed, args.workers, families, args.report)


if __name__ == "__main__":
    main()
