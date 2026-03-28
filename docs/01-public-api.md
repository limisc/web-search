# Public API

## Stable public surface

The current stable public surface is intentionally small.

### HTTP
- `POST /api/web_search`
- `POST /api/web_extract`

### MCP
- `web_search`
- `web_extract`

Everything outside this set should be treated as one of:
- internal implementation detail
- future roadmap concept
- experimental code path

Unless explicitly documented here, it is **not** a compatibility promise.

---

## Current implementation note

The docs in this repository intentionally avoid promising provider behavior that is not actually implemented yet.

At the moment:
- Tavily is the only real execution provider
- routing abstractions exist, but they should be read as internal structure, not as proof of multi-provider support
- labels such as `balanced`, `high_reliability`, or future verification levels should be read as design targets unless explicitly marked as implemented

---

## `web_search`

Unified source-discovery entrypoint.

### Request shape
```json
{
  "query": "latest MCP authorization docs",
  "intent": "general",
  "freshness": "week",
  "include_domains": ["modelcontextprotocol.io"],
  "exclude_domains": [],
  "max_results": 5,
  "verification_level": "none",
  "extraction": false,
  "debug": false,
  "provider": null
}
```

### Request fields
- `query`: search text
- `intent`: `docs | fresh | general | social`
- `freshness`: `day | week | month | year | any`
- `domains`: shorthand allowlist merged into `include_domains`
- `include_domains`: explicit allowlist
- `exclude_domains`: denylist
- `max_results`: `1..10`
- `verification_level`: `none | light | medium | high`
- `extraction`: whether search should request content-heavy results
- `debug`: include provider raw payloads
- `provider`: optional override, primarily for testing / debugging / controlled rollout

### Intent semantics
- `docs`: authoritative / official / canonical retrieval
- `fresh`: recent updates / recent news / recent changes
- `general`: broad web discovery
- `social`: discourse-heavy / social-aware lookup later

### Current implementation note
- Tavily-backed search is implemented
- the public contract is intentionally broader than today's execution reality
- `docs`, `fresh`, and `social` are valid contract intents, but their preferred provider lanes are not implemented yet
- `verification_level` is currently a contract field, not proof of real cross-provider verification
- `provider` override exists mainly to force the currently available path during the transition period

### Example
```bash
curl -X POST http://127.0.0.1:8000/api/web_search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Model Context Protocol authorization",
    "intent": "general",
    "include_domains": ["modelcontextprotocol.io"],
    "max_results": 3,
    "verification_level": "none"
  }'
```

---

## `web_extract`

Unified known-URL extraction entrypoint.

### Request shape
```json
{
  "urls": ["https://modelcontextprotocol.io/docs/learn/architecture"],
  "mode": "content",
  "schema": null,
  "query": null,
  "max_chunks": null,
  "format": "markdown",
  "debug": false,
  "provider": null
}
```

### Request fields
- `urls`: one or more absolute HTTP(S) URLs
- `mode`: `content | structured`
- `schema`: optional structured extraction schema placeholder
- `query`: optional reranking query
- `max_chunks`: optional chunk count
- `format`: `markdown | text`
- `debug`: include raw payloads
- `provider`: optional override

### Current implementation note
- currently backed by Tavily Extract
- `mode=structured` is part of the contract, but true structured extraction is not implemented yet
- provider-aware extract routing is not implemented yet

### Example
```bash
curl -X POST http://127.0.0.1:8000/api/web_extract \
  -H 'Content-Type: application/json' \
  -d '{
    "urls": ["https://modelcontextprotocol.io/docs/learn/architecture"],
    "mode": "content",
    "format": "text"
  }'
```

---

## Compatibility and deprecation policy

- additive request/response fields are preferred and treated as backward-compatible
- field renames or removals should go through a documented deprecation window of at least one minor version
- default behavior changes should be documented in both `README.md` and `docs/05-roadmap.md`
- `provider` override is not the long-term primary contract surface

---

## Stability promise table

| Surface | Current status |
|---|---|
| `web_search` request/response contract | stable target surface |
| `web_extract` request/response contract | stable target surface |
| MCP `web_search` / `web_extract` names | stable target surface |
| `provider` override | debug / rollout aid, not long-term primary contract |
| multi-provider verification behavior | planned, not stable yet |
| monitoring workflows | future / non-public |
| provider-specific routing behavior | implementation detail unless documented otherwise |

---

## Relationship to other docs

Read next:
- `docs/03-error-model.md`
- `docs/02-capability-model.md`
- `docs/06-development-workflow.md`
- `README.md`
