# Connect Claude Code to the Braintrust MCP server

Connect Claude Code to the Braintrust MCP server with the **Braintrust API key**
from the workshop. Load `.env` into your shell first (from the repo root):

```bash
set -a; source .env; set +a
```

Then add the server:

```bash
claude mcp add --transport http braintrust https://api.braintrust.dev/mcp \
  -H "Authorization: Bearer $BRAINTRUST_API_KEY"
```

This saves the key into your local Claude Code config (private to you, not committed).
