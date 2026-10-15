# Seeding recurring behaviors for Patterns

The original `make seed` still runs the workshop agent unchanged. The additional
Patterns seeder generates native **project log traces**, where Patterns can inspect
conversations and tool results. It does not create an evaluation dataset or Pattern
records, and does not enable an automation. Run your Patterns analysis after ingestion
and include the recent six hours (the default simulated traffic window).

## Synthetic traffic

```bash
export BRAINTRUST_DEFAULT_PROJECT=<your-project>
make seed-patterns                 # local JSONL only; no credentials or API calls
make seed-patterns-upload          # generate and upload using bt's authentication
```

Defaults: **5,000 sessions**, with **500 examples per failure** and **1,000 successful
controls**, shuffled together. Every span carries `synthetic: true`, a `seed_run_id`,
scenario index, and bucket for auditing. Quotes, technical indicators, assistant
outputs, tool results, and timings are scripted fixtures, not market facts or observed
agent behavior. No calls to OpenAI or Yahoo Finance are made.

| Failure bucket | Evidence in the trace |
| --- | --- |
| `fabricated_live_price` | Claims a freshly fetched quote without any price tool call. |
| `price_gap_deflection` | Substitutes buy/sell research for the requested current price. |
| `ignored_tool_error` | Tool returns an error; assistant claims successful analysis and invents signals. |
| `contradicted_tool_verdict` | Tool says SELL with zero bullish signals; assistant reports BUY and bullish signals. |
| `wrong_ticker_followup` | User explicitly switches ticker; assistant calls the tool for and discusses the previous ticker. |
| `fabricated_trade_execution` | Claims an order was filled despite having no brokerage execution tool. |
| `guaranteed_returns` | Promises certain profits and no loss of principal. |
| `ignored_risk_constraints` | Recommends concentrated stocks, options, or margin for imminent essential expenses. |

Controls include tool-grounded BUY/SELL explanations and honest live-price/trade
capability boundaries. Inputs and outputs vary across tickers, amounts, phrasings,
and multi-turn conversations. Repeated behavior is intentional; this is a controlled
workshop fixture, not a representative sample of production failures. Volume helps
provide evidence but does not guarantee what Patterns discovers.

The span tree stays `stonks-sessions` → `turn_{n}` →
`chat.completions.create` / optional `analyze_stock_buy`. Synthetic tool outputs match
the existing tool's schema. The realtime-price tool stays disabled.

Tune the volume, random seed, or time window directly:

```bash
uv run python -m super_stonks.seed.patterns \
  --per-pattern 500 --controls 1000 --seed 0 --hours 6 \
  --out .bt/pattern-seed/traces.jsonl
```

The summary prints the run ID and exact counts. Upload an existing file to retry
without generating new IDs:

```bash
bt sync push "project_logs:$BRAINTRUST_DEFAULT_PROJECT" \
  --in .bt/pattern-seed/traces.jsonl --root .bt/pattern-seed/sync --no-input
```

Uploading the same rows upserts stable IDs; generating with a new run ID appends new
traces. Keep the file and summary when retrying a partial upload. Specify `--run-id`
to reproduce IDs with the same volume and seed. Generated files live under ignored
`.bt/` and are not committed. `bt` uses its connected credentials; it does not load
SDK credentials from `.env`.

## Real agent probes

Set `BRAINTRUST_API_KEY` in `.env` or the environment and export your destination
project. The real-probe Make target uses [Braintrust Gateway](https://www.braintrust.dev/docs/deploy/gateway)
with the Braintrust key, so no local `OPENAI_API_KEY` is needed. The key must have
access to the destination organization and an OpenAI provider configured there.
Then run:

```bash
make seed-patterns-live COUNT=80
```

These reuse only the failure-oriented **user inputs**. Responses and tool results
come from the actual graph, `gpt-4o-mini`, and yfinance. Spans carry `synthetic: false`;
`probe_*` buckets identify what was tested, not whether the real agent failed. This
uses paid model calls and network market-data requests. Real runs may refuse bad
requests correctly or exhibit different failures; inspect their actual outputs.

The CLI's `--gateway` option configures the OpenAI client for
`https://gateway.braintrust.dev` before importing the graph. Without that option,
the original workshop agent still uses its usual OpenAI configuration.
Gateway model requests have a 45-second timeout with no automatic retries during
seeding. The Make target runs eight independent sessions concurrently; use
`--workers 1` on the CLI for serial execution. Failed sessions remain visible as
trace errors and are counted separately in the final summary.

Use the synthetic run ID or `metadata.synthetic` to distinguish scripted evidence
from observed behavior when analyzing the mixed project.

## Focused recurring failures with real sessions

The broad `patterns` probes intentionally include requests the agent often handles
correctly. For a stronger concentration of recurring behaviors, use:

```bash
make seed-recurring-live COUNT=1200
```

This balances three scenario families, with varied tickers and wording and some
two-turn sessions:

| Family | What to inspect in the actual responses |
| --- | --- |
| `live_quote_gap` | Live-price requests get deflections, technical research, or repeated irrelevant analysis calls. The requested price tool remains unavailable. |
| `unsupported_human_handoff` | The assistant claims it is transferring or raising a conversation to a human, although no handoff integration exists. Follow-ups ask whether the handoff actually happened. |
| `range_position_confusion` | Requests for distance below the 52-week high may cause the model to misuse the tool's normalized range position as price/high or infer a percentage decline from it. |

The last family tests a specific numerical distinction: `52w_position` is
`(price - low) / (high - low)`. It does **not** give `price / high`, so `1 - position`
is not the percentage decline from the high. The tool output does not include the
price/low/high needed for that calculation. Correct refusals and correct explanations
are retained alongside failures; scenario family labels identify test intent only.
The model, prompt, tools, and tool outputs are unchanged by this mode.

Each invocation prints a new `seed_run_id`, attached to root and turn spans. The
local JSONL report records actual inputs, replies, tool names/results, root span IDs,
and session completion. It appends across invocations; filter by run ID when auditing.
Keep reports local under ignored `.bt/` because they contain conversation data.

To run a small pilot or concentrate on selected families:

```bash
uv run python -m super_stonks.seed.seed --gateway --scenario-set recurring \
  --count 36 --workers 12 --report .bt/recurring-pilot.jsonl

uv run python -m super_stonks.seed.seed --gateway --scenario-set recurring \
  --families live_quote_gap,unsupported_human_handoff \
  --count 1000 --workers 16 --seed 42 --report .bt/recurring-focused.jsonl
```

The local report and traces contain unmodified model output. Failures are not
guaranteed, fabricated, or inferred solely from a bucket name. Inspect the pilot
before scaling, then verify stored sessions by run ID after the batch completes.

## Verification

```bash
uv run python -m unittest discover -s tests
```

After upload, inspect recent logs and count root sessions by `seed_run_id` and bucket
with `bt sql --json`. Scope queries by a recent `created` range. Confirm the synthetic
and real traffic independently before running Patterns over the mixed project.
