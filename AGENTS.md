# AGENTS.md — contributing with coding agents

Instructions for **Claude Code**, **Grok Build**, Cursor, Codex, and other coding agents working in this repository.

## What this repo is

**mcp.build** is a community monorepo of open source MCPs that use the [Hal9](https://github.com/hal9ai/hal9) agent structure:

- One folder = one agent
- Prefer `input()` / `print()` (stdin / stdout)
- Deploy to Hal9 with GitHub Actions when that folder changes

Site (GitHub Pages from `/docs`): see `docs/index.html`, `docs/llms.txt`, `docs/agents.json`.

## Before you edit

1. Read `docs/llms.txt` and `docs/agents.json`
2. Look at `send-email/` as the reference implementation
3. Look at `.github/workflows/send-email.yaml` as the deploy pattern

## Adding a new agent (checklist)

- [ ] Create top-level folder `<kebab-name>/`
- [ ] Add `app.py` using only `input()` and `print()` when possible (no `hal9` package unless needed)
- [ ] Add `requirements.txt` if third-party packages are required
- [ ] Optionally add `hal9.yaml` with `welcome:`
- [ ] Add `.github/workflows/<kebab-name>.yaml` that deploys when that folder changes
- [ ] Register in `docs/agents.json`
- [ ] Document briefly in root `README.md`
- [ ] Do not commit secrets; document env vars in README

### `app.py` shape

```python
prompt = input()
# parse prompt, call APIs / models / tools
print(result)
```

### Workflow shape

Mirror `.github/workflows/send-email.yaml`:

- Trigger: `push` to `main` with `paths` limited to the agent folder and its workflow file
- Steps: Python 3.10, `pip install hal9`, checkout, `tj-actions/changed-files`, then `hal9 deploy <path> --name ...`
- Secret name: `HAL9_TOKEN`

## Editing the website

Static site lives in `docs/` for GitHub Pages (branch deploy, `/docs` folder).

| File | Purpose |
| --- | --- |
| `docs/index.html` | Landing page |
| `docs/css/styles.css` | Styles |
| `docs/agents.json` | Machine-readable catalog (UI loads this) |
| `docs/llms.txt` | Short instructions for LLMs / agents |
| `docs/.nojekyll` | Disable Jekyll on Pages |

Keep the site minimal: no build step, no framework.

## PR hygiene

- One agent (or one focused docs change) per PR when possible
- No unrelated refactors
- No `__pycache__`, `.env`, or credentials
- Match style of existing agents: small, readable Python

## Reference agent: send-email

- Path: `send-email/`
- Stack: Groq (tool use) + Resend
- Env: `GROQ_API_KEY`, `RESEND_API_KEY`, optional `RESEND_FROM`, `GROQ_MODEL`
- Example prompt: `send email to javier@hal9.ai with text hello!`
