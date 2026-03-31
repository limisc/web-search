# Roadmap

## Current planning stance

This roadmap needs to follow the repository as it actually exists now.
It should not preserve early guesses when code, docs, and operating assumptions have moved.

The current priority order is:
- finish V1 honestly
- use V1.5 for lightweight verification and normalization work
- keep V2 for later routing intelligence and heavier ideas

This repo is a search and extraction layer for agents.
It is not trying to become a provider-monitoring console or a general upstream-control plane.
So any provider-health work should stay minimal and in service of routing or error clarity, not expand into a management product.

## Phase status overview

| Phase | Status | Core goal | Notes |
| --- | --- | --- | --- |
| V1 | nearly complete | stable `web_search` and `web_extract` contract plus current provider lanes | only the structured-extract question still needs a clean product decision |
| V1.5 | next | lightweight verification, normalization, and partial-results foundations | this is the highest-value product step now |
| V2 | later | smarter routing, ranking, richer synthesis, and broader provider graph | do not pull this forward before V1.5 becomes real |

---

## Current implementation guardrail

This roadmap describes direction, not a claim that every named mechanism already exists.

Important reality checks:

- Tavily-backed search and extract are implemented
- Brave-backed web search is implemented
- Exa-backed web search is implemented
- NewsAPI-backed fresh/news search is implemented
- Exa-backed content extract is implemented
- Firecrawl-backed content extract is available by provider override
- provider capability support is explicit in code and docs
- route-decision metadata is exposed in successful responses
- route context is now attached to provider-facing HTTP errors
- a minimal provider live-health snapshot exists only to distinguish configured vs missing-config states
- structured extract is still disabled until a sane-cost path is chosen

## Fresh external signals

This section is for periodically refreshed outside input.
It is here so the project does not only follow an old roadmap snapshot.

How to use it:
- do a broad search refresh regularly
- verify promising ideas with official or canonical sources
- if those findings change priorities, update the roadmap in the same batch
- keep this section concise and current

### Refresh loop

1. broad search for new provider options, architecture patterns, testing ideas, and operational lessons
2. narrow to official docs, pricing pages, or canonical repo sources
3. decide whether the evidence changes near-term priorities
4. if yes, update this roadmap before or with the implementation batch

### Things worth refreshing often

- structured extraction providers and pricing
- verification and dedupe designs in adjacent search orchestrators
- self-hosted broad-search backends
- Google and SERP lane options
- lightweight monitoring and diff ideas
- MCP and transport reuse patterns

### Current read on outside options

- `SerpApi` still looks like the strongest premium Google/SERP supplement if Google coverage becomes important enough to justify cost.
- `Serper` still looks attractive for budget Google-only broad search, but it is not a strong reason to expand the root contract yet.
- `SearchApi.io` remains watchable, but it is less compelling than the top two SERP candidates right now.
- `Diffbot` remains the strongest structured-extract candidate worth watching closely.
- `BrowserCat` still looks like the cleanest browser-lane candidate for JS-heavy pages and interactive extraction later.
- `Apify` still looks better as an ecosystem escape hatch than as a core near-term lane.
- `Olostep` remains interesting, but it is still not strong enough to become a near-term roadmap driver.
- `Jina Reader` is more useful as a transform helper than as a core search or extract lane.

### Recording rule

When a refresh materially changes what this repo should do next, capture:
- what changed
- why it matters here
- whether it changes the next batch, a later phase, or just the watchlist

---

## Phase V1

Goal: stabilize the public contract, HTTP API, MCP thin facade, and current provider lanes without growing accidental surfaces.

### Scope

- public interfaces
  - unified `web_search` schema
  - unified `web_extract` schema
- provider layer
  - Tavily, Brave, Exa, NewsAPI, and Firecrawl in their current capability lanes
- orchestration layer
  - rule-based router
  - planner modes
  - typed route-decision model
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
- [x] typed route-decision model
- [x] query cache
- [x] Tavily provider adapted to the new request model
- [x] Brave web-search adapter
- [x] Exa web-search adapter
- [x] NewsAPI fresh-search adapter
- [x] Firecrawl content extract adapter
- [x] provider capability matrix finalized
- [x] HTTP API integration tests
- [x] URL content cache
- [ ] decide whether `structured_extract` stays as a contract-only placeholder for now or moves to a later phase explicitly

### V1 Definition of Done

V1 should only be declared complete when all of the following are true:

- HTTP + MCP contract tests pass
- the Tavily primary path is stable, including timeout / failure degradation behavior
- docs and implementation have been checked for consistency
- default token / cost-control behavior has been both implemented and documented
- the roadmap tells the truth about structured extract instead of treating it as an almost-done implementation item

---

## Phase V1.5

Goal: improve result quality with lightweight verification and normalization, without turning the project into a large monitoring system.

### Scope

- verification levels become real in small steps
  - `none`: current single-provider behavior
  - `light`: dedupe and canonicalization first
  - `medium`: limited source-diversity and agreement checks later
  - `high`: reserved until the lighter levels prove useful
- verifier module
  - URL canonicalization
  - duplicate collapse
  - domain diversity notes
  - source agreement hints where practical
- partial-results semantics
  - clearer behavior when fallback succeeds after upstream failures
  - honest error or meta signals instead of silent degradation
- minimal monitoring building blocks only if they directly support search quality work
  - do not build a provider dashboard
  - do not build a separate upstream control plane yet

### V1.5 checklist

- [ ] verification levels become real behavior, not just contract placeholders
- [ ] duplicate collapse / canonical URL handling
- [ ] verifier module with lightweight diversity and agreement signals
- [ ] partial-results semantics become explicit behavior
- [ ] decide whether any minimal state store is truly needed before adding monitor or diff machinery

---

## Phase V2

Goal: evolve from a rule-based orchestrator into one with smarter routing, broader provider options, and richer synthesis only after V1.5 is real.

### Scope

- lightweight LLM router
  - small model
  - constrained route-plan JSON output
  - still bounded by rule guards
- learned ranking
  - simple later adjustments from feedback or usage data
- per-task cost budget
  - different limits for ad-hoc search vs future scheduled jobs
- health-aware routing
  - if this grows beyond configured-vs-missing-config, keep it strictly in service of routing quality
  - do not turn it into an operator-facing provider-status product
- expanded provider graph
  - Google/SERP supplement if justified
  - browser lane for JS-heavy pages if justified
  - future social or richer freshness lanes later
- richer verification and synthesis

### V2 checklist

- [ ] lightweight LLM router
- [ ] learned ranking hooks
- [ ] per-task budget support
- [ ] richer health-aware routing beyond static config presence, only if it improves routing decisions materially
- [ ] Google/SERP supplement decision
- [ ] browser-lane decision
- [ ] richer verification / synthesis
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
