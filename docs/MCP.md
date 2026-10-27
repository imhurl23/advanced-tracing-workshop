# Connect your coding agent to the Braintrust MCP server

Connect your coding agent to the Braintrust MCP server with the **Braintrust API key**
from the workshop. Load `.env` into your shell first (from the repo root):

```bash
set -a; source .env; set +a
```

#### Codex

```bash
codex mcp add braintrust --url https://api.braintrust.dev/mcp \
  --bearer-token-env-var BRAINTRUST_API_KEY
```

Codex reads the key from `BRAINTRUST_API_KEY` each time it starts, so launch `codex` from
a shell where `.env` is loaded. To run Codex itself on the workshop key (no OpenAI
account), see [`CODEX.md`](CODEX.md).

#### Claude Code

```bash
claude mcp add --transport http braintrust https://api.braintrust.dev/mcp \
  -H "Authorization: Bearer $BRAINTRUST_API_KEY"
```

This saves the key into your local Claude Code config (private to you, not committed).

#### Cursor

Add this to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "braintrust": {
      "url": "https://api.braintrust.dev/mcp",
      "headers": {
        "Authorization": "Bearer ${env:BRAINTRUST_API_KEY}"
      }
    }
  }
}
```

Cursor only reads `BRAINTRUST_API_KEY` from the environment it was launched from, so
start it from that shell (`cursor .`) and restart it after editing the file. Don't put the
key itself in a project's `.cursor/mcp.json`.

#### Verify

Ask your agent: *"List my recent Braintrust projects."* You should see the
`dataoutpost-workshop` projects.
