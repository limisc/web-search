# web-search

A provider-agnostic **Web Intelligence Layer** for agents and automation.

This repository exists to solve two core information problems:
- **fresh information**
- **authoritative information**

It aims to expose stable capabilities such as source discovery and extraction without tightly coupling callers to specific provider brands.

---

## Current public surface

### HTTP APIs
- `POST /api/web_search`
- `POST /api/web_extract`

### MCP tools
- `web_search`
- `web_extract`

### Not currently public
- monitoring / scheduled watch workflows
- alerting / diff workflows
- dedicated verification API

---

## Current implementation reality

Implemented today:
- Tavily-backed search
- Tavily-backed extract
- thin MCP facade
- HTTP APIs
- router / planner skeleton
- query cache

Not implemented yet:
- Exa / Brave / Firecrawl / Grok adapters
- true multi-provider fan-out
- true verification / agreement scoring
- structured extraction execution
- monitoring pipeline / scheduler integration / alerts

So the repository is currently **orchestrator-shaped**, but still **Tavily-backed in practice**.

---

## Why this project exists

In short:
- providers are not interchangeable
- providers change over time
- upper layers should ask for information capabilities, not vendor brands

Read the full purpose doc here:
- `docs/00-project-purpose.md`

---

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
uv run python -m web_search.app --transport stdio
```

### 4. Run locally over HTTP
```bash
uv run python -m web_search.app --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

### 5. Health check
```bash
curl http://127.0.0.1:8000/healthz
```

### 6. Run tests
```bash
uv run pytest -q
```

### 7. Run lint
```bash
uv run ruff check .
```

---

## Documentation map

Recommended reading order for future humans and AI agents:

1. `README.md`
   - quick understanding of purpose, public surface, and current reality
2. `docs/00-project-purpose.md`
   - architectural intent / north star
3. `docs/01-public-api.md`
   - stable contract surface
4. `docs/02-capability-model.md`
   - routing semantics independent of provider brands
5. `docs/03-error-model.md`
   - target failure semantics and examples
6. `docs/04-operations.md`
   - security / observability / deployment expectations
7. `docs/05-roadmap.md`
   - phase plan and execution status
8. `docs/06-development-workflow.md`
   - how to modify the repo safely
9. `docs/99-readme-structure-proposal.md`
   - why the docs were split this way

---

## Documentation source of truth

Use the focused docs under `docs/` as the primary source of truth:
- `docs/00-project-purpose.md`
- `docs/01-public-api.md`
- `docs/02-capability-model.md`
- `docs/03-error-model.md`
- `docs/04-operations.md`
- `docs/05-roadmap.md`
- `docs/06-development-workflow.md`

`README.md` is the entrypoint and navigation page.

---

## Project layout

```text
src/web_search/
  app.py
  config.py
  logging.py
  server.py
  tools/
    web_search.py
    web_extract.py
  services/
    search_service.py
    extract_service.py
    router.py
    planner.py
  providers/
    __init__.py
    base.py
    tavily.py
  models/
    requests.py
    responses.py
  utils/
    errors.py
    cache.py

docs/
  00-project-purpose.md
  01-public-api.md
  02-capability-model.md
  03-error-model.md
  04-operations.md
  05-roadmap.md
  06-development-workflow.md
  99-readme-structure-proposal.md
```
