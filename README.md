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
- Brave-backed web search
- Exa-backed web search
- NewsAPI-backed fresh/news search
- Exa-backed content extract
- Firecrawl-backed content extract with provider override
- thin MCP facade
- HTTP APIs
- router / planner skeleton
- query cache

Not implemented yet:
- Firecrawl-backed search
- Firecrawl-backed structured extract
- default-routed Firecrawl content extract lane
- Grok adapters
- true multi-provider fan-out
- true verification / agreement scoring
- monitoring pipeline / scheduler integration / alerts

So the repository is currently **orchestrator-shaped** with **Tavily + Brave + Exa + NewsAPI search paths** and **Tavily + Exa + Firecrawl extract paths**, while broader routing and verification are still in progress.

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
# optionally set BRAVE_SEARCH_API_KEY for Brave web search
# optionally set EXA_API_KEY for Exa web search
# optionally set NEWSAPI_API_KEY for NewsAPI fresh/news search
# optionally set FIRECRAWL_API_KEY for Firecrawl extract
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
./scripts/local_service.sh start live
```

This starts the service in the background and keeps runtime state under `.runtime/` inside the checkout instead of scattering logs, pid files, and uv temp locks into `/tmp`.

Direct foreground run still works when needed:
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

## Local development and dogfooding

When developing this repository and also using its own search capability, do not run your day-to-day searches against the actively edited checkout.

Use a stable local service from a separate git worktree and keep the current checkout for edits. A practical default is:
- `dev`: current checkout for coding
- `live`: `../web-search-live` for the stable callable instance on `127.0.0.1:8000`
- optional `preview`: temporary instance from `dev` on `127.0.0.1:8001`

Create the stable worktree once:
```bash
git worktree add --detach ../web-search-live HEAD
```

Then run the stable service from there over HTTP and keep routine usage pointed at it. A simple default is:

```bash
cd ../web-search-live
cp .env.example .env
# then set TAVILY_API_KEY in .env
# optionally set BRAVE_SEARCH_API_KEY in .env
# optionally set EXA_API_KEY in .env
# optionally set NEWSAPI_API_KEY in .env
# optionally set FIRECRAWL_API_KEY in .env
uv sync --extra dev
./scripts/local_service.sh start live
```

That keeps service logs, pid files, and temp files under `../web-search-live/.runtime/`. Use `./scripts/local_service.sh status live` or `./scripts/local_service.sh stop live` to inspect or stop it.

This avoids file-watch churn and constant restarts while AI-driven edits are changing many files.

The full workflow lives in:
- `docs/06-development-workflow.md`
- `AGENTS.md`

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
    brave.py
    exa.py
    firecrawl.py
    newsapi.py
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
