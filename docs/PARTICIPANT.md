# Super Stonks — Participant Guide

Follow top to bottom. Participants use **`bt` in the terminal** to inspect Braintrust;
no Braintrust UI account is needed. Your coding agent uses `bt` too. Topics and Patterns
screens are instructor demos. The stock-chat app opens locally in your browser.

Read the pre-seeded **`super-stonks`** project. Write your traces, dataset, experiments,
and online score to **your own project**. Do not run the seeding commands.

## 1. Install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://bt.dev/cli/install.sh | bash
```

Open a new terminal, then check both tools. Use `bt` 0.28.1 or newer.

```bash
uv --version
bt --version
```

## 2. Configure

```bash
git clone https://github.com/imhurl23/advanced-tracing-workshop.git
cd advanced-tracing-workshop
make setup
```

`make setup` creates `.env` with these defaults. Existing `.env` files are kept.
Open it and replace only the API key and `<your-name>`:

```bash
# .env
BRAINTRUST_API_KEY="<paste your Braintrust API key>"
OPENAI_BASE_URL="https://gateway.braintrust.dev"
OPENAI_API_KEY="${BRAINTRUST_API_KEY}"

BRAINTRUST_DEFAULT_PROJECT="<your-name>-stonks"
BRAINTRUST_ORG_NAME="dataoutpost-workshop"
```

Load it in **every new terminal**, before starting your coding agent:

```bash
set -a; source .env; set +a
```

If you don't have a coding agent, you can use Codex through the Braintrust gateway, follow
[`CODEX.md`](CODEX.md) to configure it.

Connect your coding agent to the Braintrust MCP server (step 6 uses it). Follow the guide
for your agent:

- **Claude Code:** [`claude-code-mcp.md`](claude-code-mcp.md)
- **Codex:** [`codex-mcp.md`](codex-mcp.md)
- **Cursor:** [`cursor-mcp.md`](cursor-mcp.md)

## 3. Run the agent and view your trace

```bash
make agent
```

In the local app, ask: **“Should I buy, hold, or sell MSFT right now?”**
Stop the app with **Ctrl+C** in the terminal, then inspect the trace:

```bash
bt view logs
```

Compare the question, tool calls, and reply. A completed trace does not guarantee a
correct answer.

## 4. Explore Topics on the shared seed

Watch the instructor open Topics for `super-stonks`. Topics groups traces by what users
ask for, such as stock research or price checks. It does not tell us whether answers
are correct.

## 5. Find the problem with Patterns

Watch the instructor open Patterns for `super-stonks`. Patterns finds recurring
problems and links to examples, including failures with no span error.

Find the pattern about dotted share-class tickers.

## 6. Investigate with your coding agent

Start your coding agent from this terminal, in this repository. Ask:

```text
Use the Braintrust MCP server to find the pattern about dotted share-class tickers in 'super-stonks'. Pull a representative sample of its traces. Compare the user's question, the ticker passed to each tool, and the tool's output. What is the root cause? Do not change code yet.
```

Discuss the evidence before continuing. A tool can return `{"error": "No data found..."}`
without raising an exception. Patterns connects those failures across requests.

## 7. Create your dataset

Exit your coding agent. Collect the pattern's failing turns into your own project:

```bash
make curate-dataset
bt datasets view share-class-tickers
```

Each row contains the question, broken reply, failing tool call, and source trace.

## 8. Understand the scorer

**Nothing to select or configure.** The eval already uses `tool_call_succeeded` from
`src/super_stonks/evals/scorers.py`. It measures the fraction of tool calls that return
data: **1 = all succeeded; 0 = all failed**. No tool calls means no score.

It catches error payloads, but cannot tell whether a successful lookup used the right
share class. Check the ticker too. A second scorer, `response_grounded_in_data`, judges
whether the answer includes supporting figures.

## 9. Run the baseline

Run this **before fixing the code**:

```bash
uv run bt eval src/super_stonks/evals/qa_eval.py
bt experiments view
```

Select the new experiment and note its name and `tool_call_succeeded` score. Some
lookups may recover, so the baseline need not be zero.

## 10. Fix the agent

Ask your coding agent:

```text
Fix the dotted share-class ticker failure from step 6. Normalize the ticker once in src/super_stonks/agent/agent.py::_invoke_tool before either stock tool runs (BRK.B -> BRK-B, HEI.A -> HEI-A), preserving the requested share class. Do not change the tool functions or analyze_stock_buy.
```

Exit your coding agent, then restart the app:

```bash
make agent
```

Ask **“Should I buy BRK.B right now?”** Stop with **Ctrl+C**, then inspect the tool span:

```bash
bt view logs
```

Check that the tool received `BRK-B` and returned data for that share class.

## 11. Compare with the baseline

```bash
uv run bt eval src/super_stonks/evals/qa_eval.py
bt experiments view
```

Select the new experiment. Compare its scores with your baseline; tool success should
improve. Inspect any remaining failures and confirm the requested share class is preserved.

## 12. Enable online scoring

Publish the same tool-success check to your project:

```bash
make push-scorer
bt scorers view
```

Select `tool_call_succeeded` to review it, then enable it on every new tool span:

```bash
make automations
```

## 13. Validate

```bash
make agent
```

Ask both questions to exercise both tools:

- **“Should I buy BRK.B right now?”** → `analyze_stock_buy`
- **“How has BRK.B performed today and this week?”** → `get_stock_performance`

Stop with **Ctrl+C**, then open the new traces:

```bash
bt view logs
```

Check each tool span: ticker **`BRK-B`**, data returned, and **`tool_call_succeeded = 1`**.
Online scores may take a few minutes; reopen the trace if needed. If the score is 0,
inspect the tool output before continuing.
