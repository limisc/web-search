# mcp-search

Minimal MCP search server scaffold for VPS deployment.

## Features
- `web_search` tool backed by Tavily Search
- `web_extract` tool backed by Tavily Extract
- FastMCP server
- Local `stdio` mode for development
- Remote `http` mode for VPS deployment
- `/healthz` endpoint
- `uv`-first local workflow
- Docker Compose deployment for VPS / Ansible handoff

## Requirements
- Python 3.12+
- `uv`
- Tavily API key

## Quick start

### 1. Create env file
```bash
cp .env.example .env
# then edit .env and set TAVILY_API_KEY
```

### 2. Create virtualenv and install
```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync --extra dev
```

### 3. Run locally with stdio
```bash
uv run python -m mcp_search.app --transport stdio
```

### 4. Run locally over HTTP
```bash
uv run python -m mcp_search.app --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

Health check:
```bash
curl http://127.0.0.1:8000/healthz
```

### 5. Run tests
```bash
uv run pytest
```

### 6. Run lint
```bash
uv run ruff check .
```

### 7. Makefile shortcuts
```bash
make setup
make lint
make test
make run-http
make run-stdio
make stop-local
```

## Docker Compose

### Local / VPS application-only deployment
```bash
cp .env.example .env
# edit .env

docker compose up -d --build
```

Check health:
```bash
curl http://127.0.0.1:8000/healthz
```

Follow logs:
```bash
docker compose logs -f
```

Stop:
```bash
docker compose down
```

### Compose-controlled variables
The compose setup is intentionally configurable via `.env` so your Ansible repo can template it.

Important variables:
- `TAVILY_API_KEY`
- `TAVILY_BASE_URL`
- `REQUEST_TIMEOUT_SECONDS`
- `RETRY_MAX_ATTEMPTS`
- `LOG_LEVEL`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_PATH`
- `FASTMCP_STATELESS_HTTP`
- `HOST_BIND`
- `HOST_PORT`

Example defaults:
```env
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_PATH=/mcp
HOST_BIND=127.0.0.1
HOST_PORT=8000
```

### Notes for Ansible integration
This repo is intentionally responsible only for the **web-search MCP application** itself.
Recommended split:
- **This repo**: app code, Dockerfile, docker-compose.yml, env contract, healthcheck
- **Ansible repo**: Docker installation, server setup, `.env` templating, reverse proxy, TLS, firewall, service rollout

Current compose is designed so Ansible can control both:
- application runtime settings
- host port binding

without editing compose YAML itself.

## Tool overview

### `web_search`
Inputs:
- `query`
- `provider` (`tavily` only for now)
- `max_results`
- `topic`
- `time_range`
- `include_domains`
- `exclude_domains`
- `search_depth`
- `include_answer`
- `include_raw_content`
- `debug`

### `web_extract`
Inputs:
- `urls`
- `provider` (`tavily` only for now)
- `extract_depth`
- `query`
- `max_chunks`
- `format`
- `debug`

## Security notes
- Do **not** expose this MCP server directly to the public internet without authentication.
- Prefer binding host ports to `127.0.0.1` and placing a controlled reverse proxy in front of it.
- Keep provider API keys server-side only.
- Reverse proxy / TLS / external ingress should be managed in your Ansible repo, not here.

## Transport support
- `stdio`: supported and recommended for local tool-style usage
- `http`: supported and recommended for VPS / remote deployment

## Project structure
```text
src/mcp_search/
  app.py
  config.py
  server.py
  tools/
  services/
  providers/
  models/
  utils/
```

## Notes
- Current scaffold is intentionally Tavily-only.
- Future providers can be added under `src/mcp_search/providers/`.
