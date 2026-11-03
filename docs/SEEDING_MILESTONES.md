# Seeding Milestones — provisioning the workshop project

The build plan for standing up a **live, pre-seeded Braintrust project** before the
workshop, then the **live workshop arc** that fixes what it surfaces. Pre-work leaves the
project with: **Topics** and the **Patterns** automation enabled, and a few hundred production-like
traces in which users type class shares in dot notation (`BRK.B`) and the tools quietly
return "No data found". The live arc finds that in Patterns, builds a scorer, proves the
fix with two experiments, and promotes the scorer to an online score.

> **The agent already exists** (`src/super_stonks/agent/`). These milestones wire
> everything *around* it. Both tools (`get_stock_performance`, `analyze_stock_buy`) are
> **enabled** — the failure lives in the traffic, not in a disabled tool.

**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done

---

## The workshop arc (the story these milestones serve)

1. **Seed the shared `super-stonks` project** (M2–M3). ~12% of sessions ask about
   share-class or renamed tickers the way users type them (`BRK.B`, `BF.B`, `HEI.A`,
   `LEN.B`, `SQ`). Yahoo/yfinance only knows the dash form (`BRK-B`), so the tools return
   `{"error": "No data found …"}` as a **normal result** — no span error.
2. **Patterns runs** (daily) and records the recurring failure — *"Stock analysis rejects
   dotted share-class tickers"* — without being told what to look for (`PARTICIPANT.md` step 5).
3. **Investigate it** with a coding agent via the Braintrust MCP + `bt` (step 6).
4. **Curate** the pattern's traces into a dataset in each attendee's own project (step 7).
5. **Push the scorer** that catches it — `tool_call_succeeded`, a code check that each
   tool call returned data.
6. **Experiment 1 — baseline**: tickers passed through as typed → score is **poor**.
7. **Fix**: normalize the ticker once in `agent.py::_invoke_tool` (`.` → `-`, plus an
   alias map such as `SQ` → `XYZ`).
8. **Experiment 2**: same dataset, same scorer → score **jumps**.
9. **Push the scorer + add it as an online automation**, generate new traffic, confirm.

> **Topics still runs** during seeding (`make topics`, upstream of the seed) so the
> project has clusters to browse — but the key finding comes from **Patterns**.

> ⚠️ **CLI limitations baked into the plan.** The `bt` CLI can't create a **Patterns**
> automation (M2) or an **online-scoring** automation (M6). Both are scripted against the
> REST API (`make patterns`, `make automations`).

---

## Where everything lives (verified against the code)

**Org:** always `dataoutpost-workshop` — pinned by the `BRAINTRUST_ORG_NAME` in `.env`
(`PARTICIPANT.md` step 2).

**Project:** resolved from **`BRAINTRUST_DEFAULT_PROJECT`**. Every command, seed, eval,
and automation reads it — attendees point it at their own project; the presenter
overrides it inline to seed the shared one:

```bash
set -a; source .env; set +a; BRAINTRUST_DEFAULT_PROJECT=super-stonks make prepare
```

`agent/config.py::get_braintrust_project_name()` reads `BRAINTRUST_DEFAULT_PROJECT`
(falls back to `BRAINTRUST_PROJECT_NAME`; errors if neither is set — no hardcoded default). The CLI agent, the
Streamlit app, and the seeder all log through it.

**Stack:** LangGraph + OpenAI **gpt-4o-mini** through the Braintrust AI gateway, wrapped
with `braintrust.wrap_openai`; market data via **yfinance**; system prompt is the
**hardcoded `STOCK_CHAT_SYSTEM`** — no prompt registry, nothing pushed.

**Config:** everything is in **`.env`** (template `.env.example`):
`BRAINTRUST_API_KEY` (the one key; `OPENAI_API_KEY` reuses it via the gateway),
`OPENAI_BASE_URL`, `BRAINTRUST_ORG_NAME`, `BRAINTRUST_DEFAULT_PROJECT`. Python loads it
with `load_dotenv()`; the shell (and `bt`) gets it from `set -a; source .env; set +a`.
`bt` authenticates with the exported API key — no `bt login` or profile needed.

| Path | What it is |
|---|---|
| `src/super_stonks/agent/__main__.py` | CLI entry (`python -m super_stonks.agent`). Owns the manual span tree: `stonks-sessions` (root) → `turn_{n}`. |
| `src/super_stonks/agent/agent.py` | LangGraph `agent` ⟷ `tools` nodes; compiled `graph`. `_invoke_tool` routes tool calls — **the fix goes here**. OpenAI client reads key + base URL from `.env`. |
| `src/super_stonks/agent/tools.py` | `TOOLS_SPEC` + two `@traced` TOOL-span tools: `get_stock_performance` (price + day/week/year %) and `analyze_stock_buy` (RSI / MA cross / 52w / analyst → BUY·HOLD·SELL). Both return `{"error": …}` for unknown symbols. |
| `src/super_stonks/app.py` | Streamlit UI (`make agent`) — same span tree as the CLI. |
| `src/super_stonks/seed/scenarios.py` | Weighted question mix, incl. the `share_class` bucket that plants the failure. |
| `src/super_stonks/seed/seed.py` | Drives `graph.invoke` over the mix and logs sessions exactly like Streamlit traffic. |
| `src/super_stonks/provision/patterns.py` | Enables the Patterns automation via the REST API (`make patterns`). |
| `src/super_stonks/provision/configure.py` | Creates the online-scoring automation via the REST API (`make automations`). |
| `src/super_stonks/provision/copy_dataset.py` | Copies a `super-stonks` dataset to every other org project. |
| `src/super_stonks/evals/` | `scorers.py`, `judge_prompts.py`, `push_assets.py`, `qa_eval.py`. |

**Trace shape:**

```
stonks-sessions          (root, type = task; metadata.entrypoint = "streamlit")
└─ turn_0                    (type = task)   input = user text, output = reply
   ├─ chat.completions.create   (LLM span, via wrap_openai)
   └─ get_stock_performance / analyze_stock_buy   (TOOL span, via @traced)
└─ turn_1
   └─ …
```

> **Span names are shared across entrypoints.** The CLI, Streamlit, and the seeder all
> emit `stonks-sessions` + `turn_{n}` (0-based). The graph itself doesn't create them —
> the entrypoint does. Keep the names identical or scorers / Patterns evidence /
> `btql_filter`s won't apply uniformly to seeded vs. live traffic.

---

## The planted failure — dotted share-class tickers

Nothing in the code is broken on purpose. The failure is in the **traffic**: the seed's
`share_class` bucket asks about `BRK.B`, `BF.B`, `HEI.A`, `LEN.B` (dot notation) and `SQ`
(renamed to `XYZ`). yfinance returns empty history for those, so the tool returns
`{"error": "No data found for 'BRK.B'. Check the ticker symbol."}` as an ordinary
result. The span has no error flag, so error filters and dashboards miss it; the agent
then guesses another symbol (sometimes `BRK-B`, sometimes a wrong one like `BLOCK`) or
tells the user the ticker is invalid.

**Don't label it in the data.** Seeded sessions carry no bucket/scenario metadata and log
`entrypoint = "streamlit"`, so Patterns has to infer the failure from behavior — that's
the demo.

The fix (live, M5) is a ticker normalization in `agent.py::_invoke_tool` before either
tool runs. Don't change the tool functions or `analyze_stock_buy` itself.

---

## Order of operations

Enable Topics + Patterns, smoke-seed, verify, then full-seed. Topics only clusters
spans logged **after** it's enabled, so it must come first. Patterns reads a 30-day window on
a daily schedule, so it picks up traces seeded before or after it's enabled; a Pattern
stays **active** only while matching traces keep arriving (activity in the last two
weekdays) — hence the top-up.

```
PRE-WORK:   enable Topics + Patterns ─▶ SMOKE seed (10) ─▶ verify ─▶ FULL seed (COUNT) ─▶ … ─▶ TOP-UP (day before)
                    M2                    M3-smoke          gate        M3-full                 M3-top-up

LIVE ARC:   Patterns (step 5) ─▶ curate (step 7) ─▶ scorer (M4) ─▶ exp1 (as typed, poor) ─▶ ticker fix ─▶ exp2 (better)
            ─▶ make push-scorer ─▶ make automations ─▶ new traffic scored live
                    M6                   M6                     M6
```

---

## Milestone 0 — Scaffold (uv + make)

| Status | Task | Notes |
|---|---|---|
| [x] | `pyproject.toml` + `uv.lock` | package **`super-stonks`** (hatchling, src-layout); `uv sync` installs it editable → `import super_stonks…` works everywhere |
| [x] | `make setup` → `uv sync` + copy `.env.example`→`.env` if missing | then fill the two `<…>` values and source it |
| [x] | `Makefile` targets (below) | |
| [x] | `.gitignore` keeps `.env` out | verified |

**Make targets:**

```
make setup            # uv sync + .env bootstrap
make agent            # Streamlit app (live demo — step 3)
make project          # M2  create the project if it doesn't exist (bt projects create)
make topics           # M2  enable Topics (bt topics config enable) — clustering, not the key finding
make patterns         # M2  enable the Patterns automation (REST API; idempotent)
make seed-smoke       # M3  topics + patterns + seed 10 traces
make seed             # M3  seed-smoke + seed COUNT traces (default 500)
make top-up           # M3  seed COUNT more traces only (keeps Patterns active)
make provision        # alias for seed-smoke — stops at the smoke gate
make prepare          # one-shot: project → topics + patterns → smoke → full seed
make copy-dataset DATASET=<name>   # fan a super-stonks dataset out to all other org projects
make push-scorer      # M6  bt functions push the tool-success scorer
make automations      # M6  create the online-scoring automation (REST API)
```

Seed sizes and mixes: `COUNT=200`, and `SEED=N` to reproduce a run exactly. By default
every run draws a fresh random mix (printed as `seed=N`), so top-ups don't repeat the
same questions.

---

## Milestone 1 — Agent tools (both enabled)

| Status | Task | Notes |
|---|---|---|
| [x] | `get_stock_performance` enabled in `TOOLS_SPEC` and routed in `_invoke_tool` | the old price-gap setup is retired |
| [x] | `analyze_stock_buy` unchanged | |
| [x] | Confirm the failure reproduces | `get_stock_performance("BRK.B")` → `{"error": …}`; `"BRK-B"` → real data |

---

## Milestone 2 — Enable Topics + Patterns (`make topics`, `make patterns`)

| Status | Task | Notes |
|---|---|---|
| [x] | `make topics` → `bt topics config enable` | runs before seeding so seeded spans cluster |
| [x] | `provision/patterns.py` creates the automation via `POST /v1/project_automation` | idempotent: skips if the project already has a Patterns automation |
| [x] | Enabled on `super-stonks` | automation `Patterns` (`0b679557-…`), daily 9am PT, 30-day window |
| [ ] | Verify the create path on a fresh project | only the "already enabled" path has been exercised by the script |

The automation config (mirrors what the Braintrust MCP's `create_scheduled_loop_job`
produces):

```jsonc
{
  "event_type": "windowed",
  "product_origin": "patterns",
  "window": {
    "window_seconds": 2592000,                       // 30 days
    "schedule": {"type": "cron", "cron_expression": "0 9 * * *", "timezone": "America/Los_Angeles"}
  },
  "loop": {
    "prompt": "Load and follow `braintrust/pattern-analysis`. …",
    "agent_slug": "loop-chat",
    "auto_approve_tools": ["new_pattern", "update_pattern"],
    "reasoning_effort": "xhigh"
  },
  "actions": []
}
```

> To run it on demand (instead of waiting for 9am), trigger it from the project's
> Patterns page in the UI. Patterns can also review source code if a repo is connected —
> without one, findings show `source_review: no_source_code`.

---

## Milestone 3 — Seed the project: smoke 10 → full → top-up

| Status | Task | Notes |
|---|---|---|
| [x] | `seed/scenarios.py` defines the use-case mix (below) | stratified, so even a 10-trace smoke includes every bucket |
| [x] | `seed/seed.py` runs sessions through the real `graph` | span tree matches prod; random mix per run, `--seed N` to reproduce |
| [x] | Seeded `super-stonks` | 200 sessions so far |
| [x] | Patterns found it | *"Stock analysis rejects dotted share-class tickers"* + *"Block analysis fails for SQ ticker requests"* |
| [ ] | Top-up the day before the workshop | `BRAINTRUST_DEFAULT_PROJECT=super-stonks make top-up COUNT=100` |

**Use-case mix:**

| Bucket | Share | Behavior |
|---|---|---|
| `realtime_price` — "what's TSLA at right now" | 20% | ✅ `get_stock_performance` |
| `research` — "should I buy MSFT" | 16% | ✅ `analyze_stock_buy` |
| `performance` — "how has NVDA done this year" | 15% | ✅ `get_stock_performance` |
| `concept` — P/E, ETFs, dividends, IRAs, RMDs | 14% | parametric |
| **`share_class` — BRK.B, BF.B, HEI.A, LEN.B, SQ** | **12% (the planted failure)** | ❌ tools return "No data found" |
| `budgeting` — emergency fund, debt, capital gains | 10% | parametric |
| `compare` — two tickers | 8% | ✅ |
| `account_action` — "roll my 401k for me" | 5% | out of scope → should decline |

**Smoke gate (after `make seed-smoke`):**

```bash
bt view logs --list-mode spans --json | jq '.'   # project from $BRAINTRUST_DEFAULT_PROJECT
```
- [ ] traces landed · [ ] span tree `stonks-sessions → turn_n → { LLM, TOOL }` · [ ] a `share_class` turn shows a TOOL span whose output is `{"error": "No data found …"}`

Silent-failure count, for sanity (scope by date — the SQL linter requires a range):

```bash
bt sql "SELECT count(*) AS failures, count(DISTINCT root_span_id) AS traces
        FROM project_logs('<project id>')
        WHERE created >= '<date>' AND span_attributes.name IN ('analyze_stock_buy','get_stock_performance')
          AND output LIKE '%No data found%'" --json | jq '.data'
```

> Emergent findings are a bonus, not a bug: on the first run Patterns also surfaced the
> agent misreading the 52-week range position and quoting an outdated RMD penalty.

---

## Milestone 4 — The scorer (`src/super_stonks/evals/scorers.py`)

**`tool_call_succeeded`** — a code scorer: did each tool call return data rather than an
`{"error": …}` payload? The check lives in `evals/tool_checks.py` (stdlib only) and is
shared by both paths:

- **Offline** (`scorers.tool_call_succeeded`, in `qa_eval.py`): trace-scoped — score =
  share of the trace's tool calls that succeeded; skipped when no tool fired.
- **Online** (`push_assets.py` → `make push-scorer`): a pushed Python code scorer run on
  **every tool span** (input = tool args, output = tool result) → 1 or 0.

`response_grounded_in_data` (LLM judge) stays as a secondary offline score.

| Status | Task | Notes |
|---|---|---|
| [x] | `tool_call_succeeded` offline + online | verified: pushed scorer returns 0 for `{"error": …}`, 1 for data |

| Scorer | Type | Scope |
|---|---|---|
| `tool_call_succeeded` | **code** | trace offline / tool span online — *the workshop scorer* |
| `response_grounded_in_data` | LLM judge | row |
| `tool_ticker_valid` | code | span |
| `has_citations_header` | code | span |
| `research_verdict_sound` | LLM judge | span/row |
| `scope_adherence` | LLM judge | trace |
| `conversation_quality` | LLM judge | trace |

---

## Milestone 5 — Two experiments: prove the failure, then the fix

| Status | Task | Notes |
|---|---|---|
| [x] | `make curate-dataset` → dataset from the Pattern's evidence (step 7) | `provision/curate_dataset.py`: reads the Pattern from `project_patterns()`, runs its `affected_filter` over the logs, writes one row per failing turn with `bt datasets create`/`update`. Default `PATTERN=share-class`, `DATASET=share-class-tickers`; refuses to write into `super-stonks` |
| [x] | `evals/qa_eval.py` — `Eval()` wrapping `graph` | scores `tool_call_succeeded` + `response_grounded_in_data`; dataset via `EVAL_DATASET` (default `share-class-tickers`) |
| [ ] | **Experiment 1 (as typed):** `bt eval src/super_stonks/evals/qa_eval.py` | low — the baseline |
| [ ] | **Fix:** normalize tickers in `agent.py::_invoke_tool` | `.` → `-`, plus `{"SQ": "XYZ"}` |
| [ ] | **Experiment 2:** re-run | score **jumps** — compare in the UI (step 11) |

> **`bt sql` gotchas** (hit while building `curate_dataset.py`): it returns **10 rows**
> unless you add a `LIMIT`; queries selecting `input`/`output` must use `LIMIT 100` or
> less; and filtering on `span_id` requires a `root_span_id` filter too.

---

## Milestone 6 — Promote the scorer to an online score

| Status | Task | Notes |
|---|---|---|
| [x] | `make push-scorer` | `bt functions push` of a Python code scorer — runs from `src/` so the bundled module path is `super_stonks.evals.push_assets` |
| [x] | `make automations` | `provision/configure.py`: `PUT /v1/project_score`, `score_type: "online"`, `btql_filter: span_attributes.type = 'tool'` |
| [ ] | Generate fresh traffic (Streamlit "Should I buy BRK.B right now?" starter) | |
| [ ] | Confirm the online score attaches and is higher after the fix | step 13 |

---

## Day-of checklist

```bash
# --- pre-work (presenter, against the shared project) ---
set -a; source .env; set +a
export BRAINTRUST_DEFAULT_PROJECT=super-stonks
make setup
make provision             # topics + patterns + 10-trace smoke  ← STOP & verify
make seed                  # COUNT traces (default 500)
make top-up COUNT=100      # the day before — keeps the Patterns active

# --- live arc ---
# step 5  Patterns → "Stock analysis rejects dotted share-class tickers"
# step 6  investigate with the coding agent (Braintrust MCP + bt)
make curate-dataset        # step 7: the Pattern's evidence → dataset (own project)
bt eval src/super_stonks/evals/qa_eval.py   # Experiment 1 → low
#      normalize tickers in agent.py::_invoke_tool
bt eval src/super_stonks/evals/qa_eval.py   # Experiment 2 → higher (step 11)
make push-scorer
make automations
# step 13  drive new traffic → online score confirms the improvement
```
