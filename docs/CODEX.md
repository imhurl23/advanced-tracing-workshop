# Using Codex with the workshop `.env`

You can drive [Codex](https://developers.openai.com/codex) through the **Braintrust AI
gateway** using only the Braintrust API key in your `.env` — no OpenAI account or
ChatGPT login needed. The gateway authenticates your Braintrust key and forwards the
request to OpenAI using the OpenAI key configured in the `dataoutpost-workshop` org.

Your `.env` already has what's needed:

```bash
BRAINTRUST_API_KEY="<your Braintrust API key>"
OPENAI_BASE_URL="https://gateway.braintrust.dev"
OPENAI_API_KEY="${BRAINTRUST_API_KEY}"          # reuses your Braintrust key
```

## 1. Add a Codex profile (one time)

Create `~/.codex/braintrust.config.toml` (a separate profile file, so your default Codex
setup is untouched):

```toml
model = "gpt-5"
model_provider = "braintrust"

[model_providers.braintrust]
name = "Braintrust"
base_url = "https://gateway.braintrust.dev/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
```

> Newer Codex versions reject a `[profiles.braintrust]` table inside `config.toml` —
> the profile must live in its own `<name>.config.toml` file as above.

## 2. Load `.env` and run Codex

Codex reads the key from your shell environment, so export `.env` first (from the repo
root):

```bash
set -a; source .env; set +a
codex --profile braintrust
```

Quick smoke test:

```bash
codex exec --profile braintrust "Reply with exactly: ok"
# → ok
```

### No profile file? Use flags

The same settings work inline:

```bash
set -a; source .env; set +a
codex -m gpt-5 \
  -c model_provider=braintrust \
  -c model_providers.braintrust.name=Braintrust \
  -c model_providers.braintrust.base_url=https://gateway.braintrust.dev/v1 \
  -c model_providers.braintrust.env_key=OPENAI_API_KEY \
  -c model_providers.braintrust.wire_api=responses
```

## Notes

- **Model:** use `gpt-5`. `gpt-5-codex` returns `model_not_found` through the org key.
- **Harmless warning:** `Model metadata for 'gpt-5' not found. Defaulting to fallback
  metadata` — Codex works fine regardless.
- **Cost:** every Codex session bills the workshop org's OpenAI key, and Codex sends a
  large context (~20k tokens even for a one-word reply). Please use it for the workshop.
- **Repo guidance:** Codex reads [`AGENTS.md`](../AGENTS.md) natively — that's where the
  project conventions and the investigation playbook live.
- **Troubleshooting:** a missing-`OPENAI_API_KEY` or auth error usually means `.env`
  wasn't sourced in this shell (re-run `set -a; source .env; set +a`).

Verified with `codex-cli 0.150.1`.
