# Connect Codex to the Braintrust MCP server

Connect Codex to the Braintrust MCP server with the **Braintrust API key**
from the workshop. Load `.env` into your shell first (from the repo root):

```bash
set -a; source .env; set +a
```

Then add the server:

```bash
codex mcp add braintrust --url https://api.braintrust.dev/mcp \
  --bearer-token-env-var BRAINTRUST_API_KEY
```

Codex reads the key from `BRAINTRUST_API_KEY` each time it starts, so launch `codex` from
a shell where `.env` is loaded. To run Codex itself on the workshop key (no OpenAI
account), see [`CODEX.md`](CODEX.md).
