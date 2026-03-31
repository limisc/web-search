# Operations

## Purpose

This document captures deployment and runtime expectations that are not purely part of the public API contract.

---

## Security responsibility boundary

Current default assumptions:

- authentication is enforced at the deployment edge (reverse proxy / private network / tunnel), not by an in-app auth system yet
- rate limiting and abuse protection are primarily deployment-layer responsibilities unless explicitly implemented in-app later
- this repository should **not** be treated as safe for direct public exposure by default

---

## Deployment posture

Recommended baseline:

- bind the app to localhost where possible
- if running in Docker, bind inside the container to `0.0.0.0` but keep the published host port on `127.0.0.1` unless remote access is intentional
- place a controlled reverse proxy in front if remote access is needed
- keep provider API keys server-side only
- handle TLS and external ingress in infrastructure / deployment tooling

---

## Observability minimums

The system should eventually emit or record at least:

- `request_id`
- route decision
- provider latency
- cache hit / miss
- partial-failure counters

Current status:

- some latency, route, capability, and cache metadata already exist
- single-URL content extract now uses a local SQLite cache under `.runtime/content_cache.sqlite` by default
- cache path and entry cap can now be tuned with `CONTENT_CACHE_DB_PATH` and `CONTENT_CACHE_MAX_ENTRIES`
- expired rows are pruned on write and the cache trims least-recently-used rows when it exceeds the local entry cap
- the full observability contract is not complete yet

---

## Timeout and retry expectations

The current system already has timeout and retry configuration hooks.

Current runtime note:

- local startup uses Uvicorn with `UVICORN_WS_PROTOCOL=wsproto` by default to avoid the deprecated `websockets.legacy` path on current dependency versions

Operationally, the service should continue to move toward:

- explicit upstream timeout behavior
- retry only for transient failures
- clear distinction between invalid requests and upstream failures
- predictable degradation behavior on provider instability

---

## Relationship to other docs

Read next:

- `docs/03-error-model.md`
- `docs/05-roadmap.md`
- `docs/06-development-workflow.md`
- `README.md`
