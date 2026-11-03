# Super Stonks — Participant Guide

Follow top to bottom. You **read** the shared, pre-seeded `super-stonks` project; you
**write** (dataset, experiments, online score) to **your own** project.

> **Using Codex as your coding agent?** You don't need an OpenAI account — Codex can run
> on the Braintrust API key in your `.env` via the Braintrust AI gateway. After step 2
> (once `.env` is filled in), follow [`CODEX.md`](CODEX.md) to set it up.

## 1. Install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv
curl -fsSL https://bt.dev/cli/install.sh | bash          # bt
bt --version                                             # verify installation and version >= 0.27.2
```

## 2. Configure

Clone the workshop repository and set up the environment:

```bash
git clone git@github.com:imhurl23/advanced-tracing-workshop.git && cd advanced-tracing-workshop
make setup  # uv sync + creates .env
```

Open `.env` and fill in the values for `$BRAINTRUST_API_KEY` and `$BRAINTRUST_DEFAULT_PROJECT`:

```bash
# .env
BRAINTRUST_API_KEY="<paste your Braintrust API key>"
OPENAI_BASE_URL="https://gateway.braintrust.dev"
OPENAI_API_KEY="${BRAINTRUST_API_KEY}"

BRAINTRUST_DEFAULT_PROJECT="<your-name>-stonks"
BRAINTRUST_ORG_NAME="dataoutpost-workshop"
```

Load it into your shell so `bt`, `make`, and your coding agent all pick it up:
```bash
set -a; source .env; set +a
```

> **Note:** this lasts for the current terminal only. Re-run it in every new terminal,
> and **before** starting your coding agent (Claude Code, Codex, Cursor) — they only see
> what was exported in the shell they were launched from.

With `.env` loaded, connect your coding agent to the Braintrust MCP server — follow
[`MCP.md`](MCP.md) for Claude Code, Codex, or Cursor.


<!-- Next, set up the Braintrust skills so coding agents know exactly how to interact with `bt`. Select `local` as the scope, press "Enter" to accept the default workflow docs, and choose the coding agent of your choice. We will be using Claude in this workshop, but all should work the same way.
```bash
bt setup skills 
``` -->


## 3. Run the agent, see your trace

This repository contains a simple agent you'll use throughout to generate traces and interact with. Use the `make` command to launch it. It will open in your browser.

> **Note:** make sure `.env` is filled in and loaded (`set -a; source .env; set +a`) in this terminal, otherwise you will run into issues.
```bash
make agent
```
Once the Streamlit app opens and loads, ask a question in the chat input or select a "Starting point" from the left. When you've done some interacting, interrupt the app with `Ctrl + c`.

With some interactions logged, use the following to view your traces in the console.
```bash
bt view logs
```

## 4. Explore Topics on the shared seed

> **Note:** participants do not have access to the Braintrust UI, so this is instructor led.
```bash
bt topics open --project super-stonks
```

Topics groups the shared project's traces by **what users are asking for** — stock
research, price checks, retirement questions, and so on. It's a great map of the traffic,
but notice what it doesn't tell you: whether the agent actually *answered* any of it. The
"stock research" cluster looks perfectly healthy here.

## 5. Find the problem with Patterns

> **Note:** instructor led.

Patterns runs on a schedule, reads the recent traces, and records **recurring problems**
with evidence, frequency, and a suggested fix — including failures that never raise an
error. Open the Patterns page for `super-stonks`:

```text
https://www.braintrust.dev/app/dataoutpost-workshop/p/super-stonks/patterns
```

Target the dotted share-class ticker pattern, currently titled
**"Dotted tickers fail or change share classes"**. Its stable ID is
`b2c6500a-00ec-480f-a5ce-ed9456b6bd76`. Patterns generates and updates titles, so the
wording may change; the ID identifies the workshop record.

## 6. Investigate it with your coding agent

Ask your coding agent:
```text
Use the Braintrust MCP server to find pattern ID b2c6500a-00ec-480f-a5ce-ed9456b6bd76 in 'super-stonks' (currently titled "Dotted tickers fail or change share classes"). Pull a representative sample of its traces and compare what the user asked, which ticker the agent passed to its tools, and what the tools returned. What's the root cause?
```
Accept the dialogs while observing what your agent does to answer the question.

It should find it: users type class shares with a dot (`BRK.B`), but Yahoo Finance only
knows the dash form (`BRK-B`). The tool returns "No data found" as a normal result — no
error on the span — so the agent guesses another symbol or tells the user the ticker is
wrong.

## 7. Curate the pattern's evidence into your dataset

The pattern records exactly which spans are affected. Turn that evidence into a dataset in
your own project — one row per failing turn, with the user's question as the input and the
broken reply and failing tool call in the metadata:
```bash
make curate-dataset
```

The command selects the shared pattern by its stable ID, so title changes do not
affect this step. Keep the default dataset name `share-class-tickers`; step 9 uses it
automatically. Instructors replacing the seed pattern can set `PATTERN_ID` to the new
record ID. `PATTERN` also supports an explicit, unique name substring; `PATTERN_ID`
takes precedence when both are set.

View it with:
```bash
bt datasets view share-class-tickers
```

## 8. Select a scorer

Evals require at least one scorer. We've already defined it in the code:
`tool_call_succeeded` checks that **each time a tool fires, it returns data** rather than
an `{"error": ...}` payload. The eval runs it locally; you'll push it to Braintrust in
step 12 for online scoring.

## 9. Baseline experiment

Run this baseline before applying the ticker fix in step 10. If this checkout already
has normalization in `_invoke_tool`, use a fresh workshop checkout for the baseline.

`qa_eval.py` runs the agent over your dataset and scores each run with
`tool_call_succeeded` (the share of tool calls that returned data) and
`response_grounded_in_data` (an LLM judge: does the answer cite real figures?).
```bash
uv run bt eval src/super_stonks/evals/qa_eval.py
```

When the eval completes, view the results. Look at `tool_call_succeeded` — it should be
low, because the dataset contains turns where dotted ticker lookups failed. The model may
recover on some runs, so the baseline need not be zero.

## 10. Fix the agent

Start your coding agent again, then instruct it to do the following:
```text
Fix the dotted share-class ticker failure investigated in step 6. Normalize the ticker once in agent.py::_invoke_tool before either stock tool runs (BRK.B → BRK-B, HEI.A → HEI-A), preserving the requested share class. Don't change the tool functions.
```
When your coding agent is done, exit with Ctrl + C.

Run the agent again and pick the **"Should I buy BRK.B right now?"** starting point (or
ask about any class share yourself):
```bash
make agent
```

When done, interrupt the agent with Ctrl + C, then view the interaction(s) in the console.
Look at the tool span: it should now contain real data instead of "No data found".
```bash
bt view logs
```

## 11. Evaluate the updated agent against the baseline

With the fix in place, run the eval experiment again.
```bash
uv run bt eval src/super_stonks/evals/qa_eval.py
```

The new experiment should score much higher on `tool_call_succeeded` than the baseline
(and on grounding, since the answers now have real data to cite).

## 12. Enable online scoring for the new scorer

First, push the scorer to your Braintrust project so a versioned copy is available across
the team:
```bash
make push-scorer
```

Review the scorer you just pushed. Select `tool_call_succeeded` when prompted.
```bash
bt scorers view
```

Now turn the scorer on for live traffic. Every tool span logged to your project will be
scored as it arrives — so if a ticker format ever starts failing again, you'll see it.
```bash
make automations
```

## 13. Validate

Run the agent again to generate fresh traffic, including a class-share question:
```bash
make agent
```

When done, interrupt the agent with Ctrl + C, then view the `tool_call_succeeded` score on
the new trace's tool spans:
```bash
bt view logs
```

Online scores may take a little time to appear. Or list your tool calls with their
scores in one table (this optional command requires `jq`):
```bash
PID=$(bt projects list --json | jq -r --arg p "$BRAINTRUST_DEFAULT_PROJECT" '.[] | select(.name==$p) | .id')
bt sql "SELECT created, span_attributes.name AS tool, input.ticker AS ticker,
               scores.tool_call_succeeded AS score
        FROM project_logs('$PID')
        WHERE span_attributes.type = 'tool' AND created >= NOW() - INTERVAL 1 DAY
        ORDER BY created DESC LIMIT 20"
```

Congratulations, you have just executed the Braintrust flywheel!
