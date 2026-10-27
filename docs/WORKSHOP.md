# Advanced Tracing Workshop

An end-to-end walkthrough of the Braintrust workflow using the `bt` CLI: observe
production traces, mine them for patterns, build evals, iterate on an agent, and
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

BRAINTRUST_PROFILE="dataoutpost-workshop"
BRAINTRUST_ORG_NAME="dataoutpost-workshop"
# YOUR project — every bt command, eval, and script resolves the project from this
# (bt reads it natively, so `bt view logs`, `bt topics`, etc. need no --project)
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
> §6 views. But your project only holds your handful of traces, so for **Topics
> clustering** (§8) you read the shared, pre-seeded **`super-stonks`** project
> (`--project super-stonks`, thousands of traces). You still **write** your curated
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
- **Why it matters:** it emits the exact trace shape we'll observe, cluster, and
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

## 7. Slide Break — Topics Intro

Pause for slides. Introduce **topic clustering**: how Braintrust groups semantically
similar traces so you can spot patterns across thousands of runs instead of reading
them one at a time.

---

## 8. Explore Clusters with `bt topics`

**Now switch to the shared seed.** Your own project only has the few traces you just
generated — not enough to cluster. `super-stonks` is pre-seeded with thousands, so
specify it explicitly:

```bash
# See the clusters visually in the browser (only the workshop instructors have an account):
bt topics open --project super-stonks

# …or list them in the terminal. Clusters are grouped by facet; the "Task" facet
# (what the user is trying to do) is the one we care about:
TASK=$(bt topics config --json --project super-stonks \
  | jq -r '.automations[0].topic_map_functions[] | select(.name=="Task").id')
bt topics report "$TASK" --project super-stonks \
  | jq -r '.clusters[] | "\(.count)\t\(.name)"'
```

> Note: bare `bt topics` shows automation *status*, not cluster names — cluster names
> come from `bt topics report <topic-map-id>` (JSON; parse `.clusters[]`).

Walk the clusters and target the problematic one — **"Current stock price analysis"**
(the price-gap cluster) — for the rest of the workshop.

### 8.1 Investigate the cluster with your coding agent

Hand the cluster off to your coding agent. It already has the
**`/braintrust`** skill (§4.3) and reads the repo's `AGENTS.md`, so it can drill in with
no extra setup. Ask it something broad — let it reach the conclusion from the traces:

```bash
How are traces performing in the "Current stock price analysis" topic cluster in
`super-stonks`? Pull a representative sample, compare what the user asked against how
the agent responded and which tools it called, and call out any consistent failure mode.
```

The agent samples the cluster's traces and reports back the failure mode — e.g. *"these
are realtime-price requests the agent can't satisfy; with no price tool it deflects into
buy/sell analysis and never returns the actual price."* That's the gap (§9.1),
**discovered from the traces rather than told.** From here the **`agent-auto-improvement`**
skill (§4.4, via the Braintrust MCP) drives the rest of the loop: capture the bad traces, write a scorer, run
evals, and fix the agent — which is exactly §9–§16 below.

---

## 9. Pull a Cluster into a Dataset

Curate the cluster's traces (read from **`super-stonks`**) into a dataset **in your own
project** (`BRAINTRUST_DEFAULT_PROJECT`) — this is the first thing you *write*, and it's
what your experiments run against.

```bash
# Source traces: super-stonks cluster.  Destination dataset: your own project.
bt datasets --help
```

### 9.1 The gap

Call it out explicitly: **there is no scorer capturing how the agent performs on
this cluster.** We can see the traces, but nothing is measuring quality here yet.
That's the motivation for everything after the break.

---

## 10. ☕ 10-Minute Break

---

## 11. Create a New Scorer

Write a scorer that measures quality on the cluster we just curated — the metric
that was missing in §9.1.

```bash
# Scaffold / edit a scorer (LLM-as-judge or code-based)
# add it to the eval file created in the next step
```

- Decide: code-based check vs. LLM-as-judge.
- Define what "good" means for this cluster of inputs.

---

## 12. Run an Experiment — Establish a Baseline

```bash
# Run the eval against your curated dataset (agent tool still OFF = the baseline)
bt eval src/super_stonks/evals/qa_eval.py

# Smoke test a few cases first
bt eval --first 5 src/super_stonks/evals/qa_eval.py
```

### 12.1 Review results

Open the experiment, look at the new scorer's distribution, and record the baseline
number. This is what we're trying to beat.

---

## 13. Change the Agent — close the gap

Fix the exact failure the cluster exposed: give the agent the realtime-price tool it
was missing. Uncomment `get_stock_performance` (the two `THE GAP` blocks in
`src/super_stonks/agent/tools.py` and `agent.py`) — see `GAP.md`. Or have your coding
agent do it: *"fill the tool gap"* → it follows `GAP.md`.

- Before: no price tool → the agent answered from parametric knowledge (ungrounded).
- After: the agent calls `get_stock_performance` and grounds its answer in real data.

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

Close the loop: **observe → cluster → curate → score → experiment → improve →
compare → deploy online → re-observe.**

```bash
tput cnorm
```