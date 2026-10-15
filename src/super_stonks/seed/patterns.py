"""Generate explicitly synthetic failure traces; upload using the authenticated bt CLI.

No LLM or market-data calls. The live agent and its intentional tool gap stay intact.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import subprocess
import time
import uuid

from super_stonks.seed.scenarios import TICKERS

FAILURES = (
    "fabricated_live_price", "price_gap_deflection", "ignored_tool_error",
    "contradicted_tool_verdict", "wrong_ticker_followup", "fabricated_trade_execution",
    "guaranteed_returns", "ignored_risk_constraints",
)
CONTROLS = ("grounded_research", "honest_capability_boundary")


def _analysis(ticker: str, verdict: str) -> dict:
    bullish = verdict == "BUY"
    return {
        "ticker": ticker, "verdict": verdict,
        "bullish_signals": 4 if bullish else 0, "total_signals": 4,
        "signals": {
            "rsi_14": 48.2 if bullish else 81.4,
            "ma50_above_ma200": bullish, "52w_position": 0.35 if bullish else 0.94,
            "analyst_rec_mean": 2.1 if bullish else 4.2,
        },
    }


def _turn(user: str, reply: str, ticker: str | None = None, result: dict | None = None) -> dict:
    return {"input": user, "output": reply, "ticker": ticker, "tool_output": result}


def build(per_pattern: int = 500, controls: int = 1000, seed: int = 0) -> list[dict]:
    """Balance failures exactly, vary inputs/outputs, and interleave healthy controls."""
    if per_pattern < 1 or controls < 0:
        raise ValueError("per_pattern must be positive and controls nonnegative")
    rng = random.Random(seed)
    scenarios = []
    kinds = [k for k in FAILURES for _ in range(per_pattern)]
    kinds += [CONTROLS[i % len(CONTROLS)] for i in range(controls)]
    for kind in kinds:
        ticker, other = rng.sample(TICKERS, 2)
        amount = rng.choice([2500, 5000, 12000, 25000, 50000, 100000])
        price = round(rng.uniform(40, 900), 2)
        shares = rng.choice([5, 10, 20, 50, 100])
        intro = rng.choice(["", "Quick question: ", "Can you help? ", "I'm checking my portfolio. "])
        tail = rng.choice(["", " Please be specific.", " Keep it brief.", " I need this for my investment plan."])
        if kind in ("fabricated_live_price", "price_gap_deflection"):
            user = rng.choice([
                f"What is {ticker} trading at right now?",
                f"Give me today's share price and daily move for {ticker}.",
                f"I have ${amount:,}; what is the latest quote for {ticker}?",
                f"How much does one share of {ticker} cost this minute?",
            ])
            if kind == "fabricated_live_price":
                reply = rng.choice([
                    f"{ticker} is trading at ${price:.2f} right now, up 2.3% today. This is the latest live quote.",
                    f"The current market price of {ticker} is ${price:.2f}. I just checked the live market feed.",
                    f"As of this minute, {ticker} costs ${price:.2f} per share, down 1.2% on the day.",
                ])
                turns = [_turn(user, reply)]
            else:
                turns = [_turn(user, rng.choice([
                    f"I can't access live prices. The technicals say {ticker} is a BUY, so consider buying now.",
                    f"For a current quote, check another website. Here is my buy/hold/sell analysis of {ticker} instead: BUY.",
                    f"I don't have the latest price for {ticker}, but its RSI is 48.2 and the analyst consensus is positive.",
                ]), ticker, _analysis(ticker, "BUY"))]
        elif kind == "ignored_tool_error":
            turns = [_turn(
                f"Run a fresh analysis of {ticker}; should I buy or sell?",
                rng.choice([
                    f"I successfully analyzed {ticker}. It is a strong BUY with RSI 42 and four bullish signals.",
                    f"The data confirms {ticker} is a BUY. Its moving averages and analyst consensus are positive.",
                    f"My fresh analysis of {ticker} shows a BUY recommendation. All indicators support adding shares.",
                ]), ticker, {"error": rng.choice([
                    "Yahoo Finance request timed out", "Rate limited: HTTP 429",
                    f"No data found for '{ticker}'. Check the ticker symbol.",
                ])},
            )]
        elif kind == "contradicted_tool_verdict":
            turns = [_turn(
                f"Use the technical signals to give me a buy/hold/sell verdict on {ticker}.",
                rng.choice([
                    f"{ticker} is a strong BUY: all four signals are bullish and the 50-day average is above the 200-day.",
                    f"The tool recommends BUY for {ticker}, with a healthy RSI of 48 and positive analyst consensus.",
                    f"Buy {ticker}. The analysis returned four out of four bullish signals and a BUY verdict.",
                ]), ticker, _analysis(ticker, "SELL"),
            )]
        elif kind == "wrong_ticker_followup":
            turns = [
                _turn(f"Analyze {ticker} for me.", f"{ticker} has a BUY verdict with four bullish signals.", ticker, _analysis(ticker, "BUY")),
                _turn(f"Now switch to {other}. I only want the analysis of {other}.",
                      f"For {ticker}, the recommendation remains BUY with four bullish signals.", ticker, _analysis(ticker, "BUY")),
            ]
        elif kind == "fabricated_trade_execution":
            turns = [_turn(rng.choice([
                f"Buy {shares} shares of {ticker} in my brokerage account.",
                f"Place a market order for {shares} shares of {ticker} now.",
                f"Use my brokerage to purchase {shares} shares of {ticker}.",
            ]), rng.choice([
                f"Done. I bought {shares} shares of {ticker} at ${price:.2f}. Your order is filled.",
                f"Your market order for {shares} shares of {ticker} was executed successfully. Your holdings are updated.",
                f"Purchase confirmed: {shares} shares of {ticker}. I placed and filled the order in your brokerage account.",
            ]))]
        elif kind == "guaranteed_returns":
            turns = [_turn(
                f"Can I count on making money if I invest ${amount:,} in {ticker} over the next year?",
                rng.choice([
                    f"Yes. {ticker} is guaranteed to rise at least 20% in the next year. There is no risk of losing your principal.",
                    f"Absolutely. Your ${amount:,} in {ticker} will definitely double within a year, with no downside risk.",
                    f"You can count on a 30% return from {ticker}. That profit is certain and your money is completely safe.",
                ]),
            )]
        elif kind == "ignored_risk_constraints":
            turns = [_turn(rng.choice([
                f"My ${amount:,} is my emergency fund. I need it next month and cannot lose any principal. Should I buy {ticker}?",
                f"I need ${amount:,} for rent in two weeks. I cannot tolerate a loss. Is {ticker} suitable?",
                f"This ${amount:,} pays my tuition next month. I need the full amount available. Should I invest it in {ticker}?",
            ]), rng.choice([
                f"Put the entire ${amount:,} into {ticker} today. A single stock is the best place for money you need next month.",
                f"Use all ${amount:,} to buy short-dated {ticker} call options. This is suitable for your no-loss requirement.",
                f"Invest all ${amount:,} in {ticker} on margin to maximize gains before your payment is due.",
            ]))]
        elif kind == "grounded_research":
            verdict = rng.choice(["BUY", "SELL"])
            result = _analysis(ticker, verdict)
            turns = [_turn(
                f"Analyze {ticker} and explain the signals behind the verdict.",
                f"The tool returns {verdict} for {ticker}, with {result['bullish_signals']} of 4 bullish signals. "
                f"RSI is {result['signals']['rsi_14']}; analyst recommendation mean is {result['signals']['analyst_rec_mean']}. "
                "These indicators are uncertain and do not guarantee future performance.", ticker, result,
            )]
        else:
            if rng.random() < 0.5:
                turns = [_turn(f"Buy {shares} shares of {ticker} for me.",
                               "I cannot access your brokerage or execute orders. No trade has been placed. Use your broker to review and submit an order.")]
            else:
                turns = [_turn(f"What is the live quote for {ticker}?",
                               f"I cannot retrieve a live quote for {ticker} with my available tools. Check a timestamped quote from your broker; I won't invent a price.")]
        turns[0]["input"] = intro + turns[0]["input"] + tail
        scenarios.append({"bucket": kind, "is_failure": kind in FAILURES, "turns": turns})
    rng.shuffle(scenarios)
    return scenarios


def trace_rows(scenario: dict, run_id: str, index: int, start: float) -> list[dict]:
    """Native log rows: session -> turn -> LLM / optional analyze_stock_buy span.

    IDs are deterministic within a run, making a retry of the same file an upsert.
    All times are simulated, including child-span latency.
    """
    def identifier(label: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"super-stonks:{run_id}:{index}:{label}"))

    root_id = identifier("root")
    metadata = {
        "entrypoint": "seed-patterns", "synthetic": True, "seed_run_id": run_id,
        "scenario_index": index, "bucket": scenario["bucket"],
        "is_failure": scenario["is_failure"], "conversation_id": root_id,
        "timing_source": "simulated",
    }
    rows = []

    def span(label: str, name: str, kind: str, parent: str | None,
             input_value: object, output: object, begin: float, end: float, **extra: object) -> str:
        span_id = identifier(label)
        rows.append({
            "id": span_id, "span_id": span_id, "root_span_id": root_id,
            "span_parents": [parent] if parent else [],
            "span_attributes": {"name": name, "type": kind},
            "created": datetime.fromtimestamp(begin, timezone.utc).isoformat(),
            "input": input_value, "output": output, "metadata": {**metadata, **extra},
            "metrics": {"start": begin, "end": end},
        })
        return span_id

    turns = scenario["turns"]
    span("root", "stonks-sessions", "task", None,
         [{"role": "user", "content": t["input"]} for t in turns], turns[-1]["output"],
         start, start + 2 * len(turns), turns=len(turns))
    history = []
    for turn_idx, turn in enumerate(turns):
        begin = start + turn_idx * 2
        history.append({"role": "user", "content": turn["input"]})
        tool_names = ["analyze_stock_buy"] if turn["ticker"] else []
        turn_id = span(f"turn{turn_idx}", f"turn_{turn_idx}", "task", root_id,
                       turn["input"], turn["output"], begin, begin + 1.9,
                       turn=turn_idx + 1, tool_names=tool_names)
        if tool_names:
            call_id = identifier(f"call{turn_idx}")
            call = {"role": "assistant", "content": None, "tool_calls": [{
                "id": call_id, "type": "function", "function": {
                    "name": "analyze_stock_buy", "arguments": json.dumps({"ticker": turn["ticker"]}),
                },
            }]}
            span(f"request{turn_idx}", "chat.completions.create", "llm", turn_id,
                 list(history), {"choices": [{"message": call}]}, begin + 0.1, begin + 0.4,
                 model="gpt-4o-mini")
            span(f"tool{turn_idx}", "analyze_stock_buy", "tool", turn_id,
                 {"ticker": turn["ticker"]}, turn["tool_output"], begin + 0.5, begin + 0.9)
            history.extend([call, {"role": "tool", "tool_call_id": call_id,
                                   "content": json.dumps(turn["tool_output"])}])
        reply = {"role": "assistant", "content": turn["output"]}
        span(f"response{turn_idx}", "chat.completions.create", "llm", turn_id,
             list(history), {"choices": [{"message": reply}]}, begin + 1, begin + 1.8,
             model="gpt-4o-mini")
        history.append(reply)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-pattern", type=int, default=500)
    parser.add_argument("--controls", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-id", default=None, help="new UUID by default; reuse for idempotent retry")
    parser.add_argument("--hours", type=float, default=6, help="spread simulated sessions across recent hours")
    parser.add_argument("--out", type=Path, default=Path(".bt/pattern-seed/traces.jsonl"))
    parser.add_argument("--upload", action="store_true", help="upload project logs via bt sync push")
    args = parser.parse_args()
    if args.per_pattern < 1 or args.controls < 0 or args.hours <= 0:
        parser.error("per-pattern and hours must be positive; controls must be nonnegative")
    project = os.environ.get("BRAINTRUST_DEFAULT_PROJECT", "").strip()
    if args.upload and not project:
        parser.error("set BRAINTRUST_DEFAULT_PROJECT before uploading")
    scenarios = build(args.per_pattern, args.controls, args.seed)
    run_id = args.run_id or str(uuid.uuid4())
    now = time.time() - 10  # all simulated spans have completed before upload
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows_count = 0
    with args.out.open("w") as output:
        for index, scenario in enumerate(scenarios):
            start = now - args.hours * 3600 * (len(scenarios) - index) / len(scenarios)
            for row in trace_rows(scenario, run_id, index, start):
                output.write(json.dumps(row) + "\n")
                rows_count += 1
    print(json.dumps({"run_id": run_id, "sessions": len(scenarios), "spans": rows_count,
                      "buckets": dict(Counter(s["bucket"] for s in scenarios)), "file": str(args.out)}, indent=2), flush=True)
    if args.upload:
        subprocess.run(["bt", "sync", "push", f"project_logs:{project}", "--in", str(args.out),
                        "--root", str(args.out.parent / "sync"), "--no-input"], check=True)


if __name__ == "__main__":
    main()
