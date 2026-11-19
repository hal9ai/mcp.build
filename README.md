# mcp.build

**mcp.build** is a community to build open source [MCPs](https://modelcontextprotocol.io) (Model Context Protocol servers) that adopted the [Hal9](https://github.com/hal9ai/hal9) open source agent structure for its ease of use for deployment and interoperability.

**Website:** [mcp.build](https://mcp.build/) — hosted on [cloudish.ai](https://cloudish.ai) from this repo's [`Dockerfile`](./Dockerfile) and [`docs/`](./docs).

This repo is structured so **coding agents** (Claude Code, Grok Build, Cursor, Codex, …) can contribute with minimal guesswork. Start at [`AGENTS.md`](./AGENTS.md) and [`docs/llms.txt`](./docs/llms.txt).

## Why Hal9 agents?

Hal9 agents are intentionally simple: read the prompt from stdin, write the result to stdout. No framework lock-in. That shape maps cleanly to how MCPs expose tools to models, and makes agents easy to:

- **Develop** — plain Python, any library
- **Deploy** — one Cloudish container serves every agent in this repo
- **Interoperate** — the same agent runs as an MCP tool at `https://mcp.build/mcp/<id>`

## Agents

| Agent | Description | Endpoint | Path |
| --- | --- | --- | --- |
| **send-email** | Send emails with [Resend](https://resend.com) from natural language prompts (Groq tool use) | `https://mcp.build/mcp/send-email` | [`send-email/`](./send-email) |
| **run-python** | Run Python and install PyPI packages from natural language prompts (Groq tool use) | `https://mcp.build/mcp/run-python` | [`run-python/`](./run-python) |
| **search-web** | Search the web via [Exa](https://exa.ai) from natural language prompts | `https://mcp.build/mcp/search-web` | [`search-web/`](./search-web) |
| **fetch-url** | Fetch and extract the plain text of any URL (no API key) | `https://mcp.build/mcp/fetch-url` | [`fetch-url/`](./fetch-url) |

Every endpoint is MCP **Streamable HTTP** (protocol `2025-06-18`) and exposes one tool named `chat` with `message` (required) and `chat_id` (optional).

### send-email

Example prompt:

```text
send email to javier@hal9.ai with text hello!
```

The agent:

1. Reads the prompt from stdin
2. Calls a Groq model with a `send_email` tool definition
3. Maps the tool call to the Resend API
4. Prints the result to stdout

**Environment variables**

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | API key from [console.groq.com](https://console.groq.com) |
| `RESEND_API_KEY` | Yes | API key from [resend.com](https://resend.com) |
| `RESEND_FROM` | No | Sender address (default: `mcp.build <onboarding@resend.dev>`) |
| `GROQ_MODEL` | No | Model id (default: `qwen/qwen3.6-27b`) |

**Local run**

```bash
cd send-email
pip install -r requirements.txt
export GROQ_API_KEY=...
export RESEND_API_KEY=...
echo "send email to you@example.com with text hello!" | python app.py
```

**Publish to the MCP Registry**

The hosted send-email MCP is published as a remote-only server to the [official MCP Registry](https://registry.modelcontextprotocol.io) under `io.github.hal9ai/send-email`. Metadata lives in [`send-email/server.json`](./send-email/server.json). On push to `main` (when `send-email/` changes), [`.github/workflows/publish-send-email.yaml`](./.github/workflows/publish-send-email.yaml) publishes it using GitHub OIDC — **no extra GitHub secrets**. The registry version is `version` in that file. If it is already published, the job skips. Bump `version` there to ship a new registry entry.

### run-python

Example prompt:

```text
install a package that calculates space orbits and compute the Hohmann transfer time from Earth to Mars and back, departing 2026-09-08
```

The agent:

1. Reads the prompt from stdin
2. Calls a Groq model with `install_packages` and `run_python` tool definitions
3. Installs requested PyPI packages into a sandbox directory
4. Executes the generated Python in a subprocess and captures stdout/stderr
5. Prints the result to stdout

**Environment variables**

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | API key from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | No | Model id (default: `qwen/qwen3.6-27b`) |
| `PYTHON_TIMEOUT` | No | Seconds allowed for each Python run (default: `60`) |
| `PIP_TIMEOUT` | No | Seconds allowed for pip install (default: `180`) |
| `PACKAGES_DIR` | No | Directory for installed packages (default: a temp dir) |

**Local run**

```bash
cd run-python
pip install -r requirements.txt
export GROQ_API_KEY=...
echo "print the first 10 primes" | python app.py
```

**Publish to the MCP Registry**

The hosted run-python MCP is published as a remote-only server to the [official MCP Registry](https://registry.modelcontextprotocol.io) under `io.github.hal9ai/run-python`. Metadata lives in [`run-python/server.json`](./run-python/server.json). On push to `main` (when `run-python/` changes), [`.github/workflows/publish-run-python.yaml`](./.github/workflows/publish-run-python.yaml) publishes it using GitHub OIDC. Bump `version` in `server.json` to ship a new registry entry.

## Hosting on cloudish.ai

`mcp.build` runs as **one Cloudish app** (`mcp-build`, container port `8080`). One container is required because a Cloudish custom domain binds a whole host: `/mcp/send-email` and `/mcp/run-python` share the `mcp.build` apex, and the same app also serves the static site from `docs/`.

```
mcp.build
├── /                    docs/index.html
├── /<id>/               docs/<id>/index.html
├── /agents.json         machine-readable catalog
├── /healthz             health check
└── /mcp/<id>            MCP Streamable HTTP, tool "chat"
```

[`mcp_server/server.py`](./mcp_server/server.py) reads [`docs/agents.json`](./docs/agents.json), builds one MCP server per agent that has an `<id>/app.py`, and runs the agent as a subprocess with the prompt on stdin — so agent code is unchanged from the Hal9 version.

### Run the gateway locally

```bash
pip install -r requirements.txt
for req in */requirements.txt; do pip install -r "$req"; done
uvicorn mcp_server.server:app --host 127.0.0.1 --port 8080
```

Then open <http://127.0.0.1:8080/> or point an MCP client at
`http://127.0.0.1:8080/mcp/send-email`.

### Deploy

On push to `main` touching `mcp_server/`, `docs/`, `send-email/`, `run-python/`, the `Dockerfile`, or `requirements.txt`, [`.github/workflows/deploy-cloudish.yaml`](./.github/workflows/deploy-cloudish.yaml):

1. Packages the committed tree with `git archive` (no `.git`, no local `.env`).
2. `POST https://cloudish.ai/api/v1/projects` with `name=mcp-build`, `port=8080`, `alwaysOn=true`, `runtimeClass=gvisor`, and the build context.
3. Polls the Cloudish build until it succeeds or fails.
4. Syncs the API keys and optional `RESEND_FROM` / `GROQ_MODEL` config to the project's encrypted secrets/env.
5. Waits for `<subdomain>/healthz`.

The app is `alwaysOn` so MCP clients do not hit cold starts (roughly **$7.84/month** at the Cloudish `shared` size).

**Required GitHub configuration**

| Name | Kind | Purpose |
| --- | --- | --- |
| `CLOUDISH_API_KEY` | secret | Cloudish API key (create/claim one at [cloudish.ai](https://cloudish.ai)) |
| `GROQ_API_KEY` | secret | Passed to the agents as a Cloudish project secret |
| `RESEND_API_KEY` | secret | Passed to send-email as a Cloudish project secret |
| `EXA_API_KEY` | secret | Passed to search-web as a Cloudish project secret |
| `RESEND_FROM` | variable | Optional sender, e.g. `mcp.build <send@mcp.build>`; must be on a Resend-verified domain |
| `GROQ_MODEL` | variable | Optional model override |
| `CLOUDISH_OWNER` | variable | Optional fallback for the Cloudish alias if it cannot be read from the deploy response |

### Custom domain (one-time)

After the first successful deploy, register the domain and add the records Cloudish returns:

```bash
export CLOUDISH_API_KEY=...
export OWNER=...   # your Cloudish alias

curl -X POST "https://cloudish.ai/api/v1/projects/${OWNER}/mcp-build/domains" \
  -H "Authorization: Bearer ${CLOUDISH_API_KEY}" \
  -H "content-type: application/json" \
  -d '{"host": "mcp.build"}'
```

Then, at the DNS provider:

1. Add the returned TXT record, e.g. `_cloudish-challenge.mcp.build = cloudish-verify=...`.
2. Point the apex `mcp.build` at `dig +short seattle.cloudish.ai` (`A` record, or CNAME flattening / ALIAS). Remove the old GitHub Pages `A` records for the apex.
3. In the GitHub repo, go to **Settings → Pages** and clear the custom domain (`mcp.build`) so Pages no longer claims the apex. Optionally disable Pages or keep it as the `hal9ai.github.io/mcp.build` mirror.
4. Cloudish verifies the records and issues TLS automatically.

Before the DNS cutover, the app is reachable at its `<name>.cloudish.app` URL printed by the deploy job.

### Security note

`run-python` executes model-generated code. In this deployment it runs inside the app container, so it shares a process tree with the gateway that holds API keys. Mitigations:

- Cloudish `runtimeClass=gvisor` for the container.
- The gateway passes each agent only the env it needs (`run-python` does not receive `RESEND_API_KEY`).
- `run-python/app.py` already strips API keys from the child process environment.

Full per-request UID/namespace isolation for generated code is a follow-up.

## Website

The site is served by the same Cloudish container from [`docs/`](./docs) — no build step. `docs/` is still a valid GitHub Pages folder, so a branch-based Pages deploy can serve a mirror at `https://hal9ai.github.io/mcp.build/`, but `https://mcp.build/` is now the Cloudish app.

| Path | Role |
| --- | --- |
| [`docs/index.html`](./docs/index.html) | Landing page — what mcp.build is + list of available MCPs |
| [`docs/send-email/index.html`](./docs/send-email/index.html) | Dedicated page per MCP (usage, "Add to Claude", etc.) — template for new MCPs |
| [`docs/run-python/index.html`](./docs/run-python/index.html) | run-python MCP page |
| [`docs/installing-mcps/index.html`](./docs/installing-mcps/index.html) | How to connect an MCP from Claude, Claude Code, and other clients |
| [`docs/css/styles.css`](./docs/css/styles.css) | Styles |
| [`docs/agents.json`](./docs/agents.json) | Machine-readable agent catalog (also drives the gateway) |
| [`docs/llms.txt`](./docs/llms.txt) | Short instructions for LLMs / agents |
| [`mcp_server/server.py`](./mcp_server/server.py) | MCP gateway + static site |
| [`Dockerfile`](./Dockerfile) | Cloudish build |

## Contributing an agent (MCP)

This repo is designed so **coding agents** (Claude Code, Grok Build, Cursor, Codex, …)
and humans can contribute a new MCP with minimal guesswork. Full checklist:
[`AGENTS.md`](./AGENTS.md). Use [`send-email/`](./send-email) as the reference
implementation.

### Expected layout

```text
# minimum
my-tool/
  app.py               # stdin → work → stdout
  requirements.txt     # optional
  server.json          # registry metadata (name, version, remotes)

# also update
.github/workflows/publish-my-tool.yaml   # MCP Registry publish
docs/agents.json                          # id, description, endpoint
docs/my-tool/index.html                   # dedicated docs page for the MCP
README.md
```

No per-agent deploy workflow is needed: the gateway discovers `<id>/app.py` from
`docs/agents.json` and [`deploy-cloudish.yaml`](./.github/workflows/deploy-cloudish.yaml)
redeploys the whole container.

### Minimal agent

```python
# my-tool/app.py
import sys

prompt = sys.stdin.read().strip()
# … call APIs, tools, models …
print(result)
```

### Steps

1. Create a new folder at the repo root, e.g. `my-tool/`. Keep the name short, kebab-case.
2. Add `app.py`. Read the prompt from stdin and write the result to stdout so the agent stays
   Hal9- and MCP-friendly. Prefer no `hal9` package unless you need session state.
3. Add a `requirements.txt` if you need third-party packages.
4. Optionally add `hal9.yaml` with a `welcome:` message.
5. Add `server.json` and a `.github/workflows/publish-my-tool.yaml` if you want the MCP Registry
   entry (copy `send-email/server.json` and `publish-send-email.yaml`).
6. Register the agent in [`docs/agents.json`](./docs/agents.json) with `id`, `name`,
   `description`, `docs_path`, and `endpoint` (`https://mcp.build/mcp/<id>`). The gateway reads this
   file, so the endpoint goes live on the next deploy.
7. Add a dedicated docs page at `docs/<my-tool>/index.html` so it shows up at
   `https://mcp.build/my-tool/`. Copy [`docs/send-email/index.html`](./docs/send-email/index.html)
   as a template — it covers what the MCP does, how agents use it, and how to add it to Claude and
   other MCP clients.
8. Do not commit secrets; document required env vars in this README and add them to the
   `AGENT_ENV` allowlist in [`mcp_server/server.py`](./mcp_server/server.py).

## License

Contributions are welcome. Individual agents may carry their own licenses; see each folder for details.
