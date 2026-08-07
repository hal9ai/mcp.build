# mcp.build

**mcp.build** is a community to build open source [MCPs](https://modelcontextprotocol.io) (Model Context Protocol servers) that adopted the [Hal9](https://github.com/hal9ai/hal9) open source agent structure for its ease of use for deployment and interoperability.

## Why Hal9 agents?

Hal9 agents are intentionally simple: read from stdin with `input()`, write to stdout with `print()`. No framework lock-in. That shape maps cleanly to how MCPs expose tools to models, and makes agents easy to:

- **Develop** — plain Python, any library
- **Deploy** — `hal9 deploy` or GitHub Actions to [hal9.com](https://hal9.com)
- **Interoperate** — same agent can run as a chatbot, an API, or an MCP tool

## Agents

| Agent | Description | Path |
| --- | --- | --- |
| **send-email** | Send emails with [Resend](https://resend.com) from natural language prompts (Groq tool use) | [`send-email/`](./send-email) |

### send-email

Example prompt:

```text
send email to javier@hal9.ai with text hello!
```

The agent:

1. Reads the prompt via `input()`
2. Calls a Groq model with a `send_email` tool definition
3. Maps the tool call to the Resend API
4. Prints the result via `print()`

**Environment variables**

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | API key from [console.groq.com](https://console.groq.com) |
| `RESEND_API_KEY` | Yes | API key from [resend.com](https://resend.com) |
| `RESEND_FROM` | No | Sender address (default: `mcp.build <onboarding@resend.dev>`) |
| `GROQ_MODEL` | No | Model id (default: `llama-3.3-70b-versatile`) |

**Local run**

```bash
cd send-email
pip install -r requirements.txt
export GROQ_API_KEY=...
export RESEND_API_KEY=...
echo "send email to you@example.com with text hello!" | python app.py
```

**Deploy to Hal9**

```bash
export HAL9_TOKEN=...   # from https://hal9.com/devs
hal9 deploy send-email --name send-email --access public \
  --title "Send Email" \
  --description "Send emails via Resend using natural language prompts"
```

On push to `main`, if files under `send-email/` change, [`.github/workflows/send-email.yaml`](./.github/workflows/send-email.yaml) deploys a new version to Hal9 (same pattern as [hal9ai/hal9](https://github.com/hal9ai/hal9) app deploy workflows). Set the `HAL9_TOKEN` repository secret in GitHub Actions.

## Contributing

1. Add a new folder at the repo root (or under a clear name) with at least `app.py`.
2. Prefer `input()` / `print()` (or any stdin/stdout) so the agent stays Hal9- and MCP-friendly.
3. Add a `requirements.txt` if you need third-party packages.
4. Optionally add `hal9.yaml` for a welcome message.
5. Add a GitHub Actions workflow that deploys when that folder changes, following the `send-email` pattern.
