"""mcp.build gateway.

Serves every agent registered in ``docs/agents.json`` as a Streamable HTTP MCP
server at ``/mcp/<id>``, and serves the static site in ``docs/`` from the same
container. Run with::

    uvicorn mcp_server.server:app --host 0.0.0.0 --port 8080

The MCP surface matches the former Hal9 endpoints: one ``chat`` tool per agent
with ``message`` (required) and ``chat_id`` (optional), returning text.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
AGENTS_JSON = DOCS / "agents.json"

AGENT_TIMEOUT = float(os.environ.get("AGENT_TIMEOUT", "900"))

# Kept for every agent: process basics and TLS/proxy settings. Deliberately does
# not include API keys that belong to another agent.
COMMON_ENV = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
)

# Per-agent allowlist. run-python deliberately does not receive RESEND_API_KEY.
AGENT_ENV = {
    "send-email": ("GROQ_API_KEY", "GROQ_MODEL", "RESEND_API_KEY", "RESEND_FROM"),
    "run-python": (
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "PYTHON_TIMEOUT",
        "PIP_TIMEOUT",
        "MAX_ROUNDS",
        "PACKAGES_DIR",
    ),
    "search-web": ("EXA_API_KEY", "SEARCH_NUM_RESULTS"),
    "fetch-url": ("FETCH_MAX_CHARS", "FETCH_TIMEOUT"),
}


def _load_agents() -> list[dict[str, Any]]:
    """Read the catalog and keep entries that have an agent implementation."""
    data = json.loads(AGENTS_JSON.read_text(encoding="utf-8"))
    agents: list[dict[str, Any]] = []

    for entry in data.get("agents", []):
        agent_id = entry.get("id")
        if not agent_id:
            continue

        script = ROOT / agent_id / "app.py"
        if not script.is_file():
            print(f"mcp.build: skipping {agent_id} (no {script})", file=sys.stderr)
            continue

        agents.append({**entry, "_script": script})

    return agents


def _metadata(agent_id: str) -> dict[str, Any]:
    """Optional per-agent metadata from the folder's server.json."""
    path = ROOT / agent_id / "server.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _agent_env(agent_id: str) -> dict[str, str]:
    keys = COMMON_ENV + tuple(AGENT_ENV.get(agent_id, ()))
    env: dict[str, str] = {}
    for key in keys:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    return env


async def _run_agent(
    agent: dict[str, Any], message: str, lock: asyncio.Lock
) -> str:
    """Run the agent's app.py with the prompt on stdin and return stdout."""
    agent_id = agent["id"]
    script = agent["_script"]

    # run-python installs into a shared package directory, so serialize calls.
    async with lock:
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_agent_env(agent_id),
                cwd=str(ROOT),
            )
        except OSError as error:
            return f"Error: could not start {agent_id}: {error}"

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(message.encode("utf-8") + b"\n"),
                timeout=AGENT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            if process.returncode is None:
                process.kill()
            await process.wait()
            return f"Error: {agent_id} timed out after {AGENT_TIMEOUT:.0f}s."

    out = stdout.decode("utf-8", "replace").strip()
    err = stderr.decode("utf-8", "replace").strip()

    if process.returncode != 0:
        detail = "\n".join(part for part in (out, err) if part)
        suffix = f"\n{detail}" if detail else ""
        return f"Error: {agent_id} exited with code {process.returncode}.{suffix}"

    return out or err or "(no output)"


def _build_mcp(agent: dict[str, Any]) -> tuple[MCPServer, Starlette]:
    agent_id = agent["id"]
    meta = _metadata(agent_id)

    title = meta.get("title") or agent.get("connector_name") or agent_id
    description = (
        meta.get("description")
        or agent.get("description")
        or f"{agent_id} MCP server"
    )
    version = str(meta.get("version", ""))

    server = MCPServer(
        agent_id,
        title=title,
        description=description,
        version=version,
        website_url=f"https://mcp.build/{agent_id}/",
    )
    lock = asyncio.Lock()

    @server.tool(
        name="chat",
        title=title,
        description=description,
        structured_output=False,
    )
    async def chat(message: str, chat_id: str = "") -> str:
        # chat_id is accepted for compatibility with the old Hal9 surface. The
        # agents are stateless, so there is no conversation to resume.
        _ = chat_id
        return await _run_agent(agent, message, lock)

    inner = server.streamable_http_app(
        streamable_http_path=f"/mcp/{agent_id}",
        host="0.0.0.0",
    )
    return server, inner


async def _healthz(_request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok\n")


def create_app() -> Starlette:
    agents = _load_agents()
    built = [_build_mcp(agent) for agent in agents]
    inner_apps = [inner for _, inner in built]

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        # Each inner app owns a StreamableHTTPSessionManager; run them all.
        async with AsyncExitStack() as stack:
            for inner in inner_apps:
                await stack.enter_async_context(
                    inner.router.lifespan_context(inner)
                )
            yield

    routes: list[Route | Mount] = []

    # Reuse the inner apps' routes directly instead of Starlette Mount so the
    # canonical paths are exactly /mcp/<id> (no trailing-slash redirect).
    for _, inner in built:
        routes.extend(inner.routes)

    routes.append(Route("/healthz", _healthz))

    # Static site last, so MCP and health routes always win.
    routes.append(
        Mount("/", app=StaticFiles(directory=str(DOCS), html=True), name="docs")
    )

    for agent in agents:
        print(f"mcp.build: /mcp/{agent['id']} -> {agent['_script']}", file=sys.stderr)

    return Starlette(routes=routes, lifespan=lifespan)


app = create_app()
