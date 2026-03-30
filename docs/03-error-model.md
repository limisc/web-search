# Error Model

## Purpose

This document defines the target error vocabulary and example response shapes for the repository.

The goal is to make failures easier for both humans and AI agents to handle consistently.

---

## Stable error vocabulary

The project should converge toward a small stable set of semantic error types:
- `invalid_request`
- `provider_not_supported`
- `provider_not_implemented`
- `provider_not_configured`
- `provider_timeout`
- `provider_unavailable`
- `budget_exceeded`
- `partial_results`

Some of these already exist in code. The full HTTP + MCP normalization layer is not finished yet.

---

## Target HTTP error shape

```json
{
  "error": {
    "type": "provider_timeout",
    "message": "Upstream provider request timed out",
    "provider": "tavily"
  }
}
```

### Fields
- `error.type`: stable semantic error name
- `error.message`: human-readable explanation
- `error.provider`: optional provider identifier when relevant

---

## Example errors

### Validation-style error
```json
{
  "error": {
    "type": "invalid_request",
    "message": "Field 'intent' must be one of: docs, fresh, general, social"
  }
}
```

### Provider timeout
```json
{
  "error": {
    "type": "provider_timeout",
    "message": "Upstream provider request timed out",
    "provider": "tavily"
  }
}
```

### Budget exceeded
```json
{
  "error": {
    "type": "budget_exceeded",
    "message": "Brave Search rate limit exceeded",
    "provider": "brave"
  }
}
```

### Provider not implemented
```json
{
  "error": {
    "type": "provider_not_implemented",
    "message": "Provider not implemented yet: grok",
    "provider": "grok"
  }
}
```

### Future partial-results shape
```json
{
  "error": {
    "type": "partial_results",
    "message": "One or more providers failed; returning partial results"
  },
  "meta": {
    "providers_used": ["tavily", "brave"]
  }
}
```

---

## MCP mapping

Current status:
- MCP tool errors are already normalized by the tool layer
- HTTP API errors are now normalized into the semantic error shape for validation, malformed JSON, and provider failures
- future partial-success behavior should not be hidden as a full success or a full failure

---

## Relationship to other docs

Read next:
- `docs/01-public-api.md`
- `docs/04-operations.md`
- `docs/06-development-workflow.md`
- `README.md`
