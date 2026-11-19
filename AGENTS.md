# AGENTS.md — contributing with coding agents

Instructions for **Claude Code**, **Grok Build**, Cursor, Codex, and other coding agents working in this repository.

## What this repo is

**mcp.build** is a community monorepo of open source MCPs that use the [Hal9](https://github.com/hal9ai/hal9) agent structure:

- One folder = one agent
- Read the prompt from **stdin**, write the result to **stdout**
- One [cloudish.ai](https://cloudish.ai) container serves every agent at `https://mcp.build/mcp/<id>` and the static site from `/docs`

## Before you edit

1. Read `docs/llms.txt` and `docs/agents.json`
2. Look at `send-email/` as the reference implementation
3. Look at `mcp_server/server.py` and `.github/workflows/deploy-cloudish.yaml` as the gateway + deploy pattern

## Adding a new agent (checklist)

- [ ] Create top-level folder `<kebab-name>/`
- [ ] Add `app.py` that reads the prompt from stdin and prints the result (no `hal9` package unless needed)
- [ ] Add `requirements.txt` if third-party packages are required
- [ ] Optionally add `hal9.yaml` with `welcome:`
- [ ] Add `server.json` with the MCP Registry metadata (copy `send-email/server.json`, bump `version`, set the remote to `https://mcp.build/mcp/<kebab-name>`)
- [ ] Add `.github/workflows/publish-<kebab-name>.yaml` that publishes `server.json` to the MCP Registry when that folder changes
- [ ] Register in `docs/agents.json` (`id`, `name`, `description`, `docs_path: "<kebab-name>/"`, `endpoint: "https://mcp.build/mcp/<kebab-name>"`)
- [ ] Add a dedicated docs page at `docs/<kebab-name>/index.html` (copy `docs/send-email/index.html`) so it shows up on the landing page and at its own route
- [ ] Document briefly in root `README.md` (full contribution checklist lives there, not on the website)
- [ ] Add any required env vars to the `AGENT_ENV` allowlist in `mcp_server/server.py`
- [ ] Do not commit secrets; document env vars in README

There is **no per-agent deploy workflow**. `mcp_server/server.py` discovers `<id>/app.py` from `docs/agents.json`, and `deploy-cloudish.yaml` redeploys the single container when any agent, the gateway, or `docs/` changes.

### `app.py` shape

```python
import sys

prompt = sys.stdin.read().strip()
# parse prompt, call APIs / models / tools
print(result)
```

`sys.stdin.read()` (rather than `input()`) is preferred so multi-line prompts are not truncated. It still works with `echo "..." | python app.py`.

### `server.json` shape

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.hal9ai/<kebab-name>",
  "title": "Human Name",
  "description": "One sentence.",
  "version": "0.0.1",
  "websiteUrl": "https://mcp.build/<kebab-name>/",
  "repository": {
    "url": "https://github.com/hal9ai/mcp.build",
    "source": "github",
    "id": "1327233276",
    "subfolder": "<kebab-name>"
  },
  "remotes": [
    { "type": "streamable-http", "url": "https://mcp.build/mcp/<kebab-name>" }
  ]
}
```

Bump `version` whenever the registry entry should be republished.

## Editing the website

The static site lives in `docs/` and is served by the same Cloudish container. There is no framework or build step — every "route" is a plain folder with an `index.html`.

| File | Purpose |
| --- | --- |
| `docs/index.html` | Landing page — explains what mcp.build is and lists available MCPs, each with its endpoint URL, an "Add to Claude" button, and a link to its own page. No agent-contribution instructions here anymore; that content lives in root `README.md` / this file. |
| `docs/<mcp-id>/index.html` | Dedicated page per MCP, e.g. `docs/send-email/index.html` → served at `/send-email/`. Covers: the endpoint URL + "Add to Claude" button at the top, description, how agents use it, self-host instructions. Does **not** repeat generic connector setup steps — link to `docs/installing-mcps/` instead. Copy `docs/send-email/index.html` as the template for a new MCP. |
| `docs/installing-mcps/index.html` | Single reference page for "how to connect any MCP" (Add to Claude, Claude Code, other MCP clients, troubleshooting). Every MCP page links here instead of repeating the instructions. |
| `docs/css/styles.css` | Shared styles (reuse existing classes: `card`, `steps`, `callout`, `meta`, `pre-wrap`, `btn`, `btn-sm`, `endpoint`, `endpoint-copy`) |
| `docs/js/copy.js` | Shared "copy to clipboard" behavior for `[data-copy]` buttons (used by the `endpoint-copy` button) |
| `docs/agents.json` | Machine-readable catalog (landing page JS loads this to render/override the MCP list, and the MCP gateway builds its servers from it). Each entry should include `id`, `name`, `description`, `docs_path` (e.g. `"send-email/"`), and `endpoint` (e.g. `https://mcp.build/mcp/send-email`). |
| `docs/llms.txt` | Short instructions for LLMs / agents |
| `mcp_server/server.py` | Starlette gateway: `/mcp/<id>` MCP endpoints, `/healthz`, and the static site |
| `Dockerfile` | Container build used by Cloudish |

Keep the site minimal: no build step, no framework. When adding a new MCP page,
mirror the section structure of `docs/send-email/index.html` so pages stay consistent
and easy to generate. Nav on every page should link to `#mcps` (or `../#mcps`) and
to `docs/installing-mcps/`.

Every page footer credits **cloudish.ai** as the hosting provider:
`Hosted by <a href="https://cloudish.ai">cloudish.ai</a>`. Keep that credit when
editing pages.

## Deployment

Hosting is [cloudish.ai](https://cloudish.ai). `.github/workflows/deploy-cloudish.yaml`
uploads the committed tree as a build context, creates/updates the `mcp-build` app
(`port=8080`, `alwaysOn=true`, `runtimeClass=gvisor`), polls the build, syncs the
agent secrets, and checks `/healthz`.

Required GitHub configuration: `CLOUDISH_API_KEY`, `GROQ_API_KEY`, `RESEND_API_KEY`
(secrets), and optionally `CLOUDISH_OWNER` (variable). See README for the custom-domain
and DNS steps. The old per-agent Hal9 deploy workflows were removed when the repo
migrated; do not reintroduce `hal9 deploy` into CI.

## PR hygiene

- One agent (or one focused docs change) per PR when possible
- No unrelated refactors
- No `__pycache__`, `.env`, or credentials
- Match style of existing agents: small, readable Python

## Reference agent: send-email

- Path: `send-email/`
- Stack: Groq (tool use) + Resend
- Env: `GROQ_API_KEY`, `RESEND_API_KEY`, optional `RESEND_FROM`, `GROQ_MODEL`
- Endpoint: `https://mcp.build/mcp/send-email`
- Example prompt: `send email to javier@hal9.ai with text hello!`
