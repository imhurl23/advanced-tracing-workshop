# Super Stonks — Advanced Tracing Workshop

A hands-on Braintrust workshop built around **Super Stonks**, a small LangGraph
stock-chat agent instrumented with the Braintrust SDK. The agent has an *unknown
issue* baked in — and the workshop is the story of finding and fixing it.

## The goal

Super Stonks looks like a helpful stock assistant. But somewhere in its behavior
there's a recurring failure that users keep running into — one that isn't obvious
until you look at the traces. You won't be told what it is up front; you'll
uncover it the way you would in the real world.

Over the session you'll run the full **Braintrust flywheel** to discover and
remediate that issue:

1. **Observe** production traces in a shared, pre-seeded project.
2. **Find** a recurring failure with Patterns, which analyzes the traces automatically.
3. **Curate** the affected traces into a dataset in your own project.
4. **Score** them with a scorer and run a **baseline experiment**.
5. **Fix** the agent once you understand what's going wrong.
6. **A/B test** the fixed agent against the baseline to prove the improvement.
7. **Deploy** an online score so the same regression can't sneak back in.

By the end you'll have run the loop end-to-end — from a surfaced production
failure to a verified fix guarded by online scoring.

## For participants

**Follow [`docs/PARTICIPANT.md`](docs/PARTICIPANT.md).** It's the step-by-step
guide you run top to bottom during the workshop: install, configure, run the
agent, investigate the failure, build the dataset, score, fix it, and validate.

Before the session, the install steps also live on the welcome screen —
[`docs/WELCOME.md`](docs/WELCOME.md).

**Using Codex?** You can run it on the Braintrust API key in your `.env` (via the
Braintrust AI gateway) — no OpenAI account needed. See [`docs/CODEX.md`](docs/CODEX.md).

## For presenters

Use these resources to set the workshop up again and run it:

| Resource | Purpose |
| --- | --- |
| [`docs/SEEDING_MILESTONES.md`](docs/SEEDING_MILESTONES.md) | Build plan for provisioning the shared, pre-seeded `super-stonks` project (Topics + Patterns + seeded traces) and the trace/scorer design. |
| [`docs/WELCOME.md`](docs/WELCOME.md) | Attendee install/welcome screen. |
| [`AGENTS.md`](AGENTS.md) | Single source of truth for coding-agent guidance, conventions, and the shared-seed vs. own-project split. |

### Setup at a glance

1. Provision the shared `super-stonks` project per
   [`docs/SEEDING_MILESTONES.md`](docs/SEEDING_MILESTONES.md):
   `BRAINTRUST_DEFAULT_PROJECT=super-stonks make prepare` enables Topics + Patterns and
   seeds the traffic (including the planted share-class tickers). Run
   `make top-up` with the same override the day before so the Patterns stay active.
2. Distribute a `BRAINTRUST_API_KEY` for the `dataoutpost-workshop` org. No
   OpenAI key is handed out — OpenAI calls go through the Braintrust AI gateway using
   the OpenAI key configured in the org (make sure one is set under the org's AI
   providers).
3. Walk participants through [`docs/PARTICIPANT.md`](docs/PARTICIPANT.md) — it's the
   run-of-show too.

## The agent

A LangGraph agent using OpenAI `gpt-4o-mini`, wrapped with `braintrust.wrap_openai`;
market data comes from yfinance.

```
src/super_stonks/
  app.py            # Streamlit UI  → `make agent`
  agent/            # LangGraph agent: agent.py, tools.py, prompts.py, config.py, ...
  evals/            # scorers.py + qa_eval.py
```

### Running locally

```bash
make setup   # uv sync + create .env
make agent   # launch the Streamlit app
make help    # all targets
```

See [`AGENTS.md`](AGENTS.md) for conventions, the shared-seed vs. own-project
split, and the coding-agent playbook.
