# Roadmap

## Phase status overview

| Phase | Status      | Core goal                                                         | Notes                                                                                    |
| ----- | ----------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| V1    | in progress | unified interfaces + thin MCP + HTTP APIs + orchestrator skeleton | code already moved here, with Tavily plus Brave plus Exa plus NewsAPI execution in place |
| V1.5  | planned     | verification + future monitoring building blocks                  | depends on basic multi-provider capabilities landing first                               |
| V2    | planned     | intelligent routing, ranking, cost-awareness, health-awareness    | after V1.5 stabilizes                                                                    |

---

## Current implementation guardrail

This roadmap describes the direction of the repository, not a claim that every named mechanism already exists.

Important reality checks:

- Tavily-backed search and extract are implemented
- Brave-backed web search is implemented
- Exa-backed web search is implemented
- NewsAPI-backed fresh/news search is implemented
- Exa-backed content extract is implemented
- Firecrawl-backed content extract is available by provider override
- provider capability support is now explicit in code and docs
- structured extract is still disabled until a sane-cost path is chosen

---

## Phase V1

Goal: stabilize the public contract, HTTP API, MCP thin facade, and router/planner/cache skeleton first.

### Scope

- public interfaces
  - unified `web_search` schema
  - unified `web_extract` schema
- provider layer
  - keep `tavily` working
  - reserve adapter slots for `exa`, `brave`, `newsapi`, `firecrawl`, `grok`
- orchestration layer
  - rule-based router
  - planner modes
  - unified response models
- cache
  - query cache
  - URL content cache with SQLite persistence and stale-while-revalidate semantics for single-URL content extract
- APIs
  - `POST /api/web_search`
  - `POST /api/web_extract`
- token control
  - small defaults
  - default `extraction=false`
  - capped `max_results`

### Default budget rules

- `max_results` default: `5`
- public `max_results` hard cap: `10`
- `low_cost`: single provider by default
- `balanced`: at most 2 providers in future implementations
- `high_reliability`: at most 3 providers in future implementations
- extraction is off by default
- future extraction fan-out must stay limited to a small top-N set
- `debug=false` by default

### V1 checklist

- [x] unified `web_search` schema
- [x] unified `web_extract` schema
- [x] MCP tools aligned with HTTP contract
- [x] router skeleton
- [x] planner skeleton
- [x] query cache
- [x] Tavily provider adapted to the new request model
- [x] Brave web-search adapter
- [x] Exa web-search adapter
- [x] NewsAPI fresh-search adapter
- [x] Firecrawl content extract adapter
- [ ] structured extract execution
- [x] provider capability matrix finalized
- [x] HTTP API integration tests
- [x] URL content cache

### V1 Definition of Done

V1 should only be declared complete when all of the following are true:

- HTTP + MCP contract tests pass
- the Tavily primary path is stable, including timeout / failure degradation behavior
- docs and implementation have been checked for consistency
- default token / cost-control behavior has been both implemented and documented

---

## Phase V1.5

Goal: improve reliability and prepare the foundations for future scheduled watch / diff / alerts.

### Scope

- verification levels
  - `none`: single provider
  - `light`: future limited secondary verification behavior later
  - `medium`: future stronger multi-provider verification behavior later
  - `high`: future strongest verification + extract behavior later
- verifier module
  - URL canonicalization
  - domain diversity
  - duplicate collapse
  - source agreement score
  - conflict note
- future monitoring building blocks
  - initial state store
  - result hash / URL set tracking
  - diff detection for page changes / extracted-field changes
- alerts
  - webhook / log output first

### V1.5 checklist

- [ ] verification levels become real behavior, not just contract placeholders
- [ ] verifier module
- [ ] duplicate collapse / canonical URL handling
- [ ] future monitor state store
- [ ] future diff detection
- [ ] simple alerts

---

## Phase V2

Goal: evolve from a purely rule-based orchestrator into one with cost-awareness, health-awareness, and some learned behavior.

### Scope

- lightweight LLM router
  - small model
  - constrained route-plan JSON output
  - still bounded by rule guards
- learned ranking
  - simple later adjustments from feedback / usage data
- per-task cost budget
  - different limits for ad-hoc search vs future scheduled jobs
- provider health-aware routing
  - error-rate / latency tracking
  - automatic downgrade / fallback
- expanded provider graph
  - Firecrawl for extraction-heavy paths
  - Grok for freshness / social paths
  - richer verification / synthesis
- integration ideas worth borrowing from adjacent search repos
  - keep the top-level contract capability-first, while allowing explicit provider override only as a secondary control
  - add a typed route-decision layer between request parsing and provider execution so routing, caching, and fallback share the same decision object
  - keep fallback chains explicit for extraction and other multi-step lanes instead of scattering implicit provider switching across adapters
  - distinguish configured credentials from live provider health so routing can skip dead lanes without pretending they are available
  - continue favoring one core execution path reused across HTTP and MCP surfaces rather than growing separate implementations
  - avoid bundling unrelated control-plane surfaces into the core runtime unless a real shared deployment need appears

### V2 checklist

- [ ] lightweight LLM router
- [ ] learned ranking hooks
- [ ] per-task budget support
- [ ] provider health tracking
- [ ] health-aware routing
- [ ] Grok freshness/social lane
- [ ] richer verification / synthesis
- [ ] typed route-decision model shared by routing, cache policy, and fallback logic
- [ ] explicit provider live-health model separate from static config presence
- [ ] documented fallback chains for content extract and future structured extract

---

## External watchlist

These are not in the project yet.
They are being tracked because they may strengthen search, structured extraction, browser automation, or adjacent extraction lanes.

### High-priority watchlist

| Provider   | Primary lane                         | Free tier signal                                                                                                                                                           | Why watch it                                                                                     |
| ---------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Diffbot    | structured extract                   | free forever with 10,000 extract calls / credits per month on the free plan, based on pricing and rate-limit docs                                                          | strongest external structured extraction candidate with meaningful monthly reset capacity        |
| SerpApi    | Google / SERP search                 | official pricing and account docs indicate a small recurring monthly free allowance, with current external evidence pointing to roughly 100 to 250 free searches per month | strongest external Google SERP candidate and a likely search-lane supplement                     |
| Olostep    | AI-first scrape / extract / search   | public pages indicate a recurring free monthly scrape allowance, but current public wording is inconsistent between 500 and 3,000 successful scrapes                       | promising AI-oriented web data platform with low paid entry and multiple relevant lanes          |
| BrowserCat | browser automation                   | free plan exists, but the current public pages we checked do not state the monthly free credit number clearly enough yet                                                   | best browser-lane candidate for JS-heavy pages, login flows, and future interaction support      |
| Apify      | actor marketplace / niche extraction | free plan includes recurring monthly platform credits, commonly referenced as $5 per month                                                                                 | useful ecosystem option for niche or vertical extractors without committing to one core provider |

### Secondary watchlist

| Provider     | Primary lane                    | Free tier signal                                                                                                                                                | Why watch it                                                                                     |
| ------------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Jina Reader  | content transform / reader lane | basic usage is free and public materials reference free token buckets for new keys, but the exact long-term free allowance wording is inconsistent across pages | worth watching as a content-to-markdown / JSON transform layer rather than a traditional scraper |
| Serper       | Google / SERP search            | 2,500 free queries are publicly advertised, but the current public evidence does not cleanly prove a recurring monthly reset                                    | cheap Google SERP option, but the long-term free-tier shape is less clear than SerpApi           |
| SearchApi.io | Google / SERP search            | 100 free requests are publicly advertised, but the monthly reset story is weak                                                                                  | useful feature coverage, but the free tier is small and less compelling                          |
| Parseur      | document extraction             | 20 pages per month free forever                                                                                                                                 | mostly relevant if the project expands beyond websites into documents or email parsing           |
| Monkt        | HTML-to-JSON transform          | free plan signals exist, but public pricing details are still too weak to rely on                                                                               | keep on the radar, but do not prioritize without clearer official pricing and capability docs    |

### Watchlist rules

- prefer recurring monthly reset free tiers over one-time trial credits when choosing what to monitor closely
- do not treat this table as an integration commitment
- before any implementation decision, re-check the provider's official pricing, rate limits, and API shape because these products change quickly

### Repo and architecture watchlist

These are not integration commitments.
They are design references worth revisiting as this project grows.

| Repo                        | What looks worth borrowing                                                                                                                          | Why it matters here                                                                                                                               | Current stance                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `skernelx/MySearch-Proxy`   | capability-first request surface, typed route decision, explicit fallback chains, live-health aware routing, proxy-first deployment thinking        | closest match to this repo's orchestrator shape and multi-provider direction                                                                      | highest-value architecture watchlist item                                       |
| `searxng/searxng`           | mature metasearch backend, huge engine catalog, settings schema, limiter and bot-detection patterns, admin and deployment depth                     | strongest self-hosted `broad_search` backend reference if the project ever needs a serious local metasearch lane                                  | watch for engine architecture, ops guardrails, and result normalization lessons |
| `netlops/SoSearch`          | one core search execution path reused by both HTTP and MCP, thin adapter layer, simple normalized response shape, scraper-first multi-engine search | good reference for keeping surface area small while exposing multiple transports, and a candidate future self-hosted `broad_search` fallback lane | watch for simplicity, transport reuse, and low-cost self-hosted broad search    |
| `catlog22/codexlens-search` | MCP ergonomics, strong test coverage habits, staged search pipeline thinking                                                                        | useful patterns around MCP packaging and test discipline, but not a direct model for web-search capabilities                                      | watch only for tooling and test ideas                                           |

Notes:

- `SearXNG` looks most relevant as a high-priority future self-hosted metasearch backend under `broad_search`.
- Its strengths are breadth, plugin depth, settings discipline, and public-instance operations.
- It is much heavier than this repo, and its AGPL license matters for any code-level reuse.
- `SoSearch` looks more relevant as a lightweight self-hosted scraper-search lane under `broad_search`.
- Neither repo is a model for `authoritative_search`, `structured_extract`, or the main capability-first orchestrator shape.
- If explored later, treat both as bounded broad-search backends or fallback lanes, not as the default source of truth for docs-heavy tasks.

Use this list to inform design reviews and roadmap choices.
Do not treat it as proof that the repo should copy those systems wholesale.

## Future GitHub discovery and repo-reading lane

A missing capability in the current project is GitHub repository discovery plus repository digestion.
This matters because programming-related discovery often depends on GitHub more than websites alone.

Potential future workflow:

1. discover candidate repositories from broad web or GitHub-aware search
2. separate primary repos from wrappers, forks, integrations, and stale clones
3. digest the repo itself
   - README and examples
   - package and directory layout
   - release and maintenance signals
   - issues, discussions, and activity hints
4. feed that back into provider and tool evaluation

This is not a public API yet.
For now it should be treated as a research workflow or future capability area, not a committed surface.

## Relationship to other docs

Read next:

- `docs/02-capability-model.md`
- `docs/01-public-api.md`
- `docs/06-development-workflow.md`
- `README.md`
