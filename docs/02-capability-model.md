# Capability Model

## Purpose

This document defines the semantic capability model of the repository.

It exists so the project can evolve independently of any specific provider brand.

The system should route by **capability**, not by provider name.

---

## Current implementation guardrail

This document describes the semantic model the repository is converging toward.

It should **not** be read as proof that all listed routing lanes already exist in production.

At the moment:

- Tavily-backed search and extract are implemented
- Brave-backed web search is implemented
- Exa-backed web search is implemented
- NewsAPI-backed fresh/news search is implemented
- the current provider capability matrix below is the live implementation truth for existing providers
- multi-provider routing semantics beyond the current lanes are still mostly design-time abstractions

---

## Core capabilities

### `authoritative_search`

Use for:

- official docs
- canonical product pages
- pricing pages
- API / reference material

### `fresh_search`

Use for:

- recent developments
- recent news
- recent changes
- time-sensitive information

### `broad_search`

Use for:

- general web discovery
- broad fact gathering
- wide candidate-source retrieval

### `social_search`

Use for:

- discourse-heavy lookups
- community conversation
- future social-aware retrieval paths

### `content_extract`

Use for:

- readable text extraction from known URLs
- chunked page content retrieval
- known-page content access

### `structured_extract`

Use for:

- extracting fields according to a schema
- future structured page parsing workflows

---

## Public intent -> capability mapping

| Public surface                   | Meaning                                        | Internal capability    |
| -------------------------------- | ---------------------------------------------- | ---------------------- |
| `web_search(intent="docs")`      | authoritative / official / canonical retrieval | `authoritative_search` |
| `web_search(intent="fresh")`     | recent updates / recent news / recent changes  | `fresh_search`         |
| `web_search(intent="general")`   | broad web discovery                            | `broad_search`         |
| `web_search(intent="social")`    | social / discourse-heavy lookup                | `social_search`        |
| `web_extract(mode="content")`    | readable content extraction                    | `content_extract`      |
| `web_extract(mode="structured")` | structured field extraction                    | `structured_extract`   |

---

## Query -> intent -> capability -> provider mapping

| User need                                              | Public intent / API              | Internal capability    | Likely providers over time                        |
| ------------------------------------------------------ | -------------------------------- | ---------------------- | ------------------------------------------------- |
| official docs / API reference / canonical product info | `web_search(intent="docs")`      | `authoritative_search` | Exa first, possibly others later                  |
| recent changes / recent news / latest updates          | `web_search(intent="fresh")`     | `fresh_search`         | NewsAPI first today, Grok or others later         |
| broad fact gathering / normal web discovery            | `web_search(intent="general")`   | `broad_search`         | Tavily, Brave, maybe Exa in some cases            |
| social / discourse-heavy lookup                        | `web_search(intent="social")`    | `social_search`        | Grok, future social-aware providers               |
| known URL, fetch readable content                      | `web_extract(mode="content")`    | `content_extract`      | Tavily, Firecrawl, Exa contents                   |
| known URL(s), fetch structured fields                  | `web_extract(mode="structured")` | `structured_extract`   | Firecrawl, future structured extraction providers |

This table defines semantic lanes, not current implementation guarantees.

---

## Example current provider-to-capability mapping

| Provider  | Capabilities                                              | Current status                                 |
| --------- | --------------------------------------------------------- | ---------------------------------------------- |
| Exa       | `authoritative_search`, `broad_search`, `content_extract` | implemented for web search and content extract |
| Tavily    | `broad_search`, `content_extract`                         | implemented                                    |
| Brave     | `broad_search`                                            | implemented for web search                     |
| NewsAPI   | `fresh_search`                                            | implemented for fresh/news search              |
| Firecrawl | `content_extract`                                         | implemented for content extract                |
| Grok      | `fresh_search`, `social_search`                           | planned                                        |

---

## Current degraded routing behavior

Because only part of the multi-provider graph is really implemented right now, actual behavior should currently be understood as:

| Intent    | Target routing design                       | Current actual behavior                                      |
| --------- | ------------------------------------------- | ------------------------------------------------------------ |
| `general` | Tavily or Brave, with broader routing later | Brave first when configured, otherwise Tavily                |
| `docs`    | Exa-oriented lane later                     | Exa first when configured, then Brave or Tavily fallback     |
| `fresh`   | Grok + Brave lane later                     | NewsAPI first when configured, then Brave or Tavily fallback |
| `social`  | Grok-oriented lane later                    | Brave or Tavily fallback, no social-specialized lane yet     |

Current extract behavior is more limited:

- `mode="content"` with `query` or `max_chunks` prefers Exa when configured, then falls back to Tavily
- plain `mode="content"` still prefers Tavily, with Exa available as fallback when configured
- single-URL `mode="content"` requests now reuse a local URL content cache before hitting upstream extract providers
- `provider="firecrawl"` supports content extract today
- overriding `provider` to a service that does not implement extract returns `provider_not_supported`
- default `mode="structured"` returns `provider_not_implemented`
- no provider currently implements `mode="structured"`

---

## Result quality semantics

Before true multi-provider fan-out can be considered complete, the service should define and document minimum normalization rules for:

- URL canonicalization
- duplicate collapse
- score meaning and range
- merge / ranking behavior across providers

Current status:

- normalized fields exist
- full dedupe / canonicalization rules are not yet documented
- provider `score` should currently be treated as provider-native unless documented otherwise

---

## Relationship to other docs

Read next:

- `docs/01-public-api.md`
- `docs/05-roadmap.md`
- `docs/03-error-model.md`
- `README.md`
