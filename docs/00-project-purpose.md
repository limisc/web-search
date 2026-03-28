# Project Purpose

## What this repository is for

This repository exists to build a provider-agnostic **Web Intelligence Layer** for agents and automation.

Its purpose is not to expose a pile of provider-specific APIs.
Its purpose is to give upper-layer systems a stable way to ask for web information without being tightly coupled to whichever provider happens to be popular today.

---

## The two core information problems

This project is designed around two primary information needs.

### 1. Fresh, recent, real-time information
Examples:
- what changed recently
- latest news
- recent product or ecosystem updates
- fast-moving web information
- possibly discourse-heavy or social-aware information later

### 2. Accurate, authoritative, citeable information
Examples:
- official documentation
- API / reference pages
- pricing pages
- product pages
- canonical sources

These are different information problems and often require different retrieval strategies.

---

## Why not design around provider names

Providers are not interchangeable.

Different providers are good at different things:
- some are stronger at authoritative / docs retrieval
- some are stronger at broad search
- some are stronger at freshness
- some are stronger at extraction or structured extraction

Providers also change:
- pricing changes
- quality changes
- APIs change
- providers may disappear

So this repository should not force callers to think in terms of:
- Exa
- Tavily
- Brave
- Firecrawl
- Grok
- or any future brand name

Instead, it should offer stable semantic capabilities and route to implementations behind the scenes.

---

## Why V1 is intentionally small

V1 should expose only two foundational primitives:
- `web_search`
- `web_extract`

Why this is enough:
- authoritative retrieval starts by discovering the right source
- fresh retrieval also starts by discovering the right source
- verification can later be built on top of multiple search results
- monitoring can later be built on top of repeated search/extract + diff workflows

So `search + extract` is not a shortcut. It is the correct lowest stable abstraction.

---

## MCP's role

MCP is intentionally a **thin entry layer**.

It should expose only a small number of stable tools:
- `web_search`
- `web_extract`

The real orchestration logic belongs in the service layer:
- routing
- fallback
- provider selection
- normalization
- caching
- future verification

This keeps token overhead lower and keeps the public surface stable.

---

## Long-term goal

The long-term goal is to become a private orchestration layer that:
- serves interactive agents through a thin MCP facade
- serves applications directly through HTTP APIs
- routes by information need, not by provider brand
- survives provider churn by keeping contracts stable and implementations replaceable

---

## Relationship to the rest of the docs

Read next:
- `docs/01-public-api.md`
- `docs/02-capability-model.md`
- `docs/05-roadmap.md`
- `docs/06-development-workflow.md`
- `README.md`
