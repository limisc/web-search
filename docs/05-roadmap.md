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

### V2 checklist

- [ ] lightweight LLM router
- [ ] learned ranking hooks
- [ ] per-task budget support
- [ ] provider health tracking
- [ ] health-aware routing
- [ ] Grok freshness/social lane
- [ ] richer verification / synthesis

---

## External watchlist

These are not in the project yet.
They are being tracked because they may strengthen search, structured extraction, browser automation, or adjacent extraction lanes.

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

### Watchlist rules

- prefer recurring monthly reset free tiers over one-time trial credits when choosing what to monitor closely
- do not treat this table as an integration commitment
- before any implementation decision, re-check the provider's official pricing, rate limits, and API shape because these products change quickly

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
