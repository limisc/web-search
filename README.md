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
```

## Docker
```bash
docker compose up --build
```

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

### `web_extract`
Inputs:
- `urls`
- `provider` (`tavily` only for now)
- `extract_depth`
- `query`
- `max_chunks`
- `format`

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
- For production, put this behind Caddy or Nginx and prefer private access or authenticated HTTPS.
