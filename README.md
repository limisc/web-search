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
- successful responses expose `meta.route`, `meta.capability`, and `meta.provider_override_applied`
- provider-facing HTTP errors can include route context and minimal provider-health snapshots
- `verification_level="light"` now canonicalizes URLs, removes duplicate search hits that collapse to the same canonical URL, and reports source domains as a lightweight diversity hint
- successful fallback search responses can expose `meta.partial_failures`
- query cache
- URL content cache with stale-while-revalidate semantics for single-URL content extract
- extract responses expose `meta.cache_state` as `miss | fresh | stale` when the local URL content cache is used
- cache path and entry cap are configurable through `CONTENT_CACHE_DB_PATH` and `CONTENT_CACHE_MAX_ENTRIES`
- expired cache rows are pruned on write and oversized caches trim least-recently-used rows
- provider capability support is explicit now: Tavily=`broad_search + content_extract`, Brave=`broad_search`, Exa=`authoritative_search + broad_search + content_extract`, NewsAPI=`fresh_search`, Firecrawl=`content_extract`

Not implemented yet:
- Firecrawl-backed structured extract
- default-routed Firecrawl content extract lane
- Grok adapters
- true multi-provider fan-out
- medium and high verification behavior
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

The default runtime now tells Uvicorn to use `wsproto` for WebSocket handling so startup stays quiet with current `websockets` releases.

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

### 8. Run type check
```bash
uv run pyright
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

## External watchlist

These are not in the project yet.
They are being tracked because they may strengthen search, structured extraction, browser automation, or adjacent extraction lanes.

## Architecture watchlist

These are repositories, not providers.
They are worth keeping on a short list because they expose design patterns relevant to this project.

| Repo | Watch for | Why it is interesting |
| --- | --- | --- |
| `skernelx/MySearch-Proxy` | capability-first search surface, route-decision layer, explicit fallback chains, live provider health, proxy-first deployment shape | closest outside reference for a multi-provider search orchestrator |
| `searxng/searxng` | mature self-hosted metasearch backend, large engine plugin system, settings schema, limiter and bot-detection patterns, admin and ops depth | strongest self-hosted `broad_search` backend reference, but much heavier than this repo and AGPL-licensed |
| `netlops/SoSearch` | shared core execution across HTTP and MCP, thin provider adapters, very small public surface, scraper-first broad-search lane | useful reference for transport reuse and a possible lightweight self-hosted `broad_search` fallback, not a template for docs or structured extract lanes |
| `catlog22/codexlens-search` | MCP packaging quality, staged search pipeline patterns, strong test posture | useful for tooling and test ideas even though the domain is code search |

### High-priority watchlist

| Provider | Primary lane | Free tier signal | Why watch it |
| --- | --- | --- | --- |
| Diffbot | structured extract | free forever with 10,000 extract calls / credits per month on the free plan, based on pricing and rate-limit docs | strongest external structured extraction candidate with meaningful monthly reset capacity |
| SerpApi | Google / SERP search | official pricing and account docs indicate a small recurring monthly free allowance, with current external evidence pointing to roughly 100 to 250 free searches per month | strongest external Google SERP candidate and a likely search-lane supplement |
| Olostep | AI-first scrape / extract / search | public pages indicate a recurring free monthly scrape allowance, but current public wording is inconsistent between 500 and 3,000 successful scrapes | promising AI-oriented web data platform with low paid entry and multiple relevant lanes |
| BrowserCat | browser automation | free plan exists, but the current public pages we checked do not state the monthly free credit number clearly enough yet | best browser-lane candidate for JS-heavy pages, login flows, and future interaction support |
| Apify | actor marketplace / niche extraction | free plan includes recurring monthly platform credits, commonly referenced as $5 per month | useful ecosystem option for niche or vertical extractors without committing to one core provider |

### Secondary watchlist

| Provider | Primary lane | Free tier signal | Why watch it |
| --- | --- | --- | --- |
| Jina Reader | content transform / reader lane | basic usage is free and public materials reference free token buckets for new keys, but the exact long-term free allowance wording is inconsistent across pages | worth watching as a content-to-markdown / JSON transform layer rather than a traditional scraper |
| Serper | Google / SERP search | 2,500 free queries are publicly advertised, but the current public evidence does not cleanly prove a recurring monthly reset | cheap Google SERP option, but the long-term free-tier shape is less clear than SerpApi |
| SearchApi.io | Google / SERP search | 100 free requests are publicly advertised, but the monthly reset story is weak | useful feature coverage, but the free tier is small and less compelling |
| Parseur | document extraction | 20 pages per month free forever | mostly relevant if the project expands beyond websites into documents or email parsing |
| Monkt | HTML-to-JSON transform | free plan signals exist, but public pricing details are still too weak to rely on | keep on the radar, but do not prioritize without clearer official pricing and capability docs |

### Current interpretation rules

- prefer recurring monthly reset free tiers over one-time trial credits when choosing what to monitor closely
- do not treat this table as an integration commitment
- before any implementation decision, re-check the provider's official pricing, rate limits, and API shape because these products change quickly

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
