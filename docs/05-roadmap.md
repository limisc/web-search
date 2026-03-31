# Roadmap

## Phase status overview

| Phase | Status | Core goal | Notes |
|---|---|---|---|
| V1 | in progress | unified interfaces + thin MCP + HTTP APIs + orchestrator skeleton | code already moved here, with Tavily plus Brave plus Exa execution in place |
| V1.5 | planned | verification + future monitoring building blocks | depends on basic multi-provider capabilities landing first |
| V2 | planned | intelligent routing, ranking, cost-awareness, health-awareness | after V1.5 stabilizes |

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
- structured extract is still disabled until a sane-cost path is chosen
- names such as `balanced`, `high_reliability`, or `top-2` are roadmap semantics unless explicitly implemented
- future monitoring is roadmap-only, not part of the current public surface
- provider abstraction exists structurally, but most of its long-term value is still ahead of the codebase

---

## Phase V1

Goal: stabilize the public contract, HTTP API, MCP thin facade, and router/planner/cache skeleton first.

### Scope
- public interfaces
  - unified `web_search` schema
  - unified `web_extract` schema
- provider layer
  - keep `tavily` working
  - reserve adapter slots for `exa`, `brave`, `firecrawl`, `grok`
- orchestration layer
  - rule-based router
  - planner modes
  - unified response models
- cache
  - query cache
  - reserve URL content cache for later
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
- [ ] provider capability matrix finalized
- [x] HTTP API integration tests
- [ ] URL content cache

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

## Relationship to other docs

Read next:
- `docs/02-capability-model.md`
- `docs/01-public-api.md`
- `docs/06-development-workflow.md`
- `README.md`
