# Advanced Tracing Workshop

An end-to-end walkthrough of the Braintrust workflow using the `bt` CLI: observe
production traces, let Patterns surface recurring failures, build evals, iterate on an agent, and
close the loop with online scoring.

> Numbering below continues from the broader session agenda (intro/setup sections
> 1–3 precede this document).

---

## 4. The `bt` CLI

### 4.1 Overview

`bt` is Braintrust's command-line interface. It gives you scriptable,
`--json`-pipeable access to the same data you see in the UI — projects, logs,
traces, prompts, evals, and SQL — plus first-class setup for coding agents.

Everything in this workshop is driven from `bt` so the flow is reproducible and
copy-pasteable.

Install the CLI (https://github.com/braintrustdata/bt)

```bash
curl -fsSL https://bt.dev/cli/install.sh | bash
```

### 4.2 Authentication

```bash
# verify install
bt --version

# Authenticate using API key provided in workshop
bt login

# verify profile listed
bt profiles
```

**Everything lives in `.env`** (`make setup` copies it from `.env.example`). Participants
fill in two values — the Braintrust API key and their name — then load it once per
terminal:

```bash
# .env
BRAINTRUST_API_KEY=<provided in workshop>
OPENAI_BASE_URL="https://gateway.braintrust.dev"
OPENAI_API_KEY="${BRAINTRUST_API_KEY}"

# BRAINTRUST_PROFILE="dataoutpost-workshop"
BRAINTRUST_ORG_NAME="dataoutpost-workshop"
# YOUR project — every bt command, eval, and script resolves the project from this
# (bt reads it natively, so `bt view logs`, `bt datasets`, etc. need no --project)
BRAINTRUST_DEFAULT_PROJECT="<your-name>-stonks"
```

```bash
set -a; source .env; set +a   # every new terminal, before starting a coding agent
```

The Braintrust API key is the only key participants get: OpenAI calls go through the
Braintrust AI gateway (using the org's configured OpenAI key), so `OPENAI_API_KEY` just
reuses the Braintrust key.

Auth resolution order (first match wins): explicit `--profile` →
`BRAINTRUST_API_KEY` → `BRAINTRUST_PROFILE` → org-matched profile →
single-profile auto-select → interactive picker.

> **Where each value lives:** once `.env` is sourced, the `bt` CLI reads the profile,
> org, and project from the shell (no `--env-file` needed). The **Python side** (agent /
> Streamlit / evals) loads `.env` itself via `load_dotenv()`, and the agent's OpenAI
> client always takes its key + gateway URL straight from `.env`. `BRAINTRUST_ORG_NAME`
> keeps `bt` in the **dataoutpost-workshop** org even when it authenticates with the
> exported API key instead of the saved profile.

> **Your project vs. the shared seed.** Traces you generate locally — the app in §5.1,
> your §17 traffic — land in **your own** `BRAINTRUST_DEFAULT_PROJECT`, and that's what
> §6 views. But your project only holds your handful of traces, so for **Patterns**
> (§8) you read the shared, pre-seeded **`super-stonks`** project
> (`--project super-stonks`). You still **write** your curated
> dataset, experiments, and online score back to your own project.

### 4.3 Agent skills setup

Configure interactively your coding agent to work with `bt` by installing agent-specific skills.

```bash
bt setup skills
```

---

### 4.4 Auto Improvement skill (via the Braintrust MCP)

The `agent-auto-improvement` skill enables a coding agent to abide by Braintrust's AI SDLC
Flywheel for building quality AI agents. Nothing to install: it's served by the
**Braintrust MCP server** (set up in [`MCP.md`](MCP.md)), and the agent loads it on demand
through the server's `load_braintrust_skill` tool. Ask for it by name — e.g. *"load the
agent-auto-improvement skill from the Braintrust MCP"* — so the agent fetches it.

## 5. The Demo Agent

Introduce the agent we built for this workshop — what it does, its tools, and how
it's traced.

- **What it is:** a small LLM agent instrumented with the Braintrust SDK so every
  run produces a trace with nested spans (LLM calls, tool calls, retrieval, etc.).
- **Why it matters:** it emits the exact trace shape we'll observe, analyze, and
  evaluate for the rest of the session.

### 5.1 Streamlit front-end (optional live demo)

A lightweight Streamlit app lets the room watch the agent run in real time and see
traces land in Braintrust immediately.

```bash
make agent
```

> Talking point: as questions come in through the UI, refresh `bt view logs` to
> show traces appearing live.

---

## 6. View Traces via `bt view`

Look at the trace you just created by running the app in §5.1 — it's in **your own**
project (no `--project` needed; `bt` uses your `BRAINTRUST_DEFAULT_PROJECT`):

```bash
# Browse logs interactively (TUI on a TTY)
bt view logs
```

TUI controls: `Up/Down` select, `Enter` open trace, `/` search, `t` toggle
span/thread view, `Ctrl+k` copy URL, `q` quit.

---

## 7. Slide Break — Patterns Intro

Pause for slides. Introduce **Patterns**: a scheduled Braintrust Loop automation that
reads a project's recent traces, finds recurring behaviors (tool failures, wrong
outputs, inefficiencies), and records each one as a Pattern with evidence, frequency,
severity, and a suggested fix — so you don't have to read thousands of traces yourself.

Key point to land: Patterns catches failures that **never raise an error**. A tool can
"succeed" and return `{"error": ...}` as its result; span-level error filters miss that.

---

## 8. Explore Patterns on the shared seed

**Now switch to the shared seed.** Your own project only has the few traces you just
generated. `super-stonks` is pre-seeded and has a Patterns automation running on it
(weekdays 9am PT), so the findings are already there.

Show the Patterns page in the browser (only the workshop instructors have an account):

```text
https://www.braintrust.dev/app/dataoutpost-workshop/p/super-stonks/patterns
```

Walk the list. Expect a mix of planted and emergent findings, e.g.:

- **Stock analysis rejects dotted share-class tickers** — the target for the rest of
  the workshop.
- **Block analysis fails for SQ ticker requests** — the same root cause (renamed
  ticker), different fix.
- Emergent findings nobody planted (e.g. misreading the 52-week range position, an
  outdated RMD penalty). Good talking point: Patterns finds things you didn't seed.

> Patterns only stays **active** while matching traces keep arriving (activity in the
> last two weekdays). Top up the seed shortly before the session:
> `set -a; source .env; set +a; BRAINTRUST_DEFAULT_PROJECT=super-stonks uv run python -m super_stonks.seed.seed --count 100`

### 8.1 Investigate the pattern with your coding agent

Participants can't open the UI, but their coding agent can read the same Patterns
through the **Braintrust MCP server** ([`MCP.md`](MCP.md)) and drill into the traces
with `bt`. Ask something broad — let it reach the conclusion from the evidence:

```text
List the Patterns in the 'super-stonks' project. Pick the one about share-class
tickers, pull a representative sample of its traces, and compare what the user asked,
which ticker the agent passed to its tools, and what the tools returned. What's the
root cause?
```

The agent should report the failure mode: *users type class shares in dot notation
(`BRK.B`, `BF.B`, `HEI.A`, `LEN.B`); Yahoo/yfinance only knows the dash form (`BRK-B`),
so `analyze_stock_buy` and `get_stock_performance` return "No data found" as a normal
result, and the agent either guesses another symbol or tells the user the ticker is
invalid.* From here the **`agent-auto-improvement`** skill (§4.4, via the Braintrust
MCP) drives the rest of the loop — exactly §9–§16 below.

---

## 9. Pull the pattern's traces into a dataset

Curate the pattern's traces (read from **`super-stonks`**) into a dataset **in your own
project** (`BRAINTRUST_DEFAULT_PROJECT`) — this is the first thing you *write*, and it's
what your experiments run against. Create it with `bt datasets create --file rows.jsonl`
(see `AGENTS.md`), carrying the source trace id and failure category in `metadata`.

```bash
# Source traces: super-stonks pattern.  Destination dataset: your own project.
bt datasets --help
```

### 9.1 The gap

Call it out explicitly: **there is no scorer catching these silent tool failures.**
The spans have no error flag, so nothing is measuring how often the agent hands a user
"ticker not found" for a perfectly valid company. That's the motivation for everything
after the break.

---

## 10. ☕ 10-Minute Break

---

## 11. Create a New Scorer

Write a scorer that measures quality on the pattern we just curated — the metric that
was missing in §9.1.

```bash
# Scaffold / edit a scorer (LLM-as-judge or code-based)
# add it to the eval file created in the next step
```

- Decide: code-based check vs. LLM-as-judge. A **code-based** check fits well here —
  did any tool call in the trace return an `error` payload?
- Optionally pair it with a judge: did the final answer actually address the company
  the user asked about?

---

## 12. Run an Experiment — Establish a Baseline

```bash
# Run the eval against your curated dataset (ticker fix not applied = the baseline)
bt eval src/super_stonks/evals/qa_eval.py

# Smoke test a few cases first
bt eval --first 5 src/super_stonks/evals/qa_eval.py
```

### 12.1 Review results

Open the experiment, look at the new scorer's distribution, and record the baseline
number. This is what we're trying to beat.

---

## 13. Change the Agent — fix the ticker format

Fix the exact failure the pattern exposed: normalize the ticker **once, before any tool
call**, in `src/super_stonks/agent/agent.py::_invoke_tool` — convert dot notation to the
dash form Yahoo expects (`BRK.B` → `BRK-B`), plus a small alias map for renamed tickers
(`SQ` → `XYZ`). Both tools benefit from the one change. Or have your coding agent do it:
*"fix the share-class ticker pattern"* → it follows `AGENTS.md`.

- Before: dotted tickers → "No data found" → the agent guesses or gives up.
- After: the tools get a symbol Yahoo recognizes and the agent answers with real data.

---

## 14. Run Another Experiment

Same dataset, same scorer, changed agent — directly comparable to the baseline:

```bash
bt eval src/super_stonks/evals/qa_eval.py
```

---

## 15. Compare Experiments

Diff the new experiment against the baseline from §12. Show the score delta and
walk through individual examples that improved (or regressed) to make the impact
concrete.

---

## 16. Add an Online Score

Promote the scorer we validated offline into an **online score** so it runs
automatically on live production traces going forward.

- Offline eval proved the scorer is meaningful.
- Online scoring keeps measuring it continuously in production.

---

## 17. Validate New Coverage

Generate fresh traces (via the Streamlit app or the agent directly) and confirm the
online score now attaches to them. This is **your own project** now — the fresh traffic
and the online score live in `BRAINTRUST_DEFAULT_PROJECT`, not the shared seed:

```bash
bt view logs        # your own project (BRAINTRUST_DEFAULT_PROJECT)
```

Close the loop: **observe → find patterns → curate → score → experiment → improve →
compare → deploy online → re-observe.**

```bash
tput cnorm
```