# Connect Cursor to the Braintrust MCP server

Connect Cursor to the Braintrust MCP server with the **Braintrust API key**
from the workshop. Load `.env` into your shell first (from the repo root):

```bash
set -a; source .env; set +a
```

Then add this to `~/.cursor/mcp.json`:

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
