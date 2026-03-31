# Development Workflow

## Purpose

This document tells future humans and AI agents how to change the repository safely.

---

## Change discipline

Any change that affects the public contract should update documentation in the same PR.

At minimum, check whether you need to update:

- `README.md`
- `docs/01-public-api.md`
- `docs/02-capability-model.md`
- `docs/03-error-model.md`
- `docs/05-roadmap.md`

Before every commit, do a self-audit:

- inspect `git status`
- review changed code for leftovers, stale branches, or transition scaffolding
- review `README.md` and relevant `docs/*.md` for stale statements
- confirm tests, lint, and type checks for the batch are clean
- confirm whether `pyproject.toml`, `uv.lock`, and a new git tag also need to move together

---

## PR discipline

### If a PR changes public request/response schema

Update:

- `README.md`
- `docs/01-public-api.md`
- tests
- `docs/05-roadmap.md` if roadmap status or scope changed

### If a PR changes provider support or routing semantics

Update:

- `docs/02-capability-model.md`
- `docs/05-roadmap.md`
- `docs/03-error-model.md` if failure behavior changes
- README current-status summary if user-visible behavior changes

### If a PR changes deployment/security/ops behavior

Update:

- `docs/04-operations.md`
- `README.md` if quick-start or deployment expectations changed

---

## Local dogfooding workflow

This repository is expected to be used while it is still being developed.

When coding here and also relying on this project's own search or extract capability, use a stable-service workflow:

- keep a separate stable checkout or git worktree for the callable service
- do active edits in the current checkout
- point routine search and extract usage at the stable service, not the actively edited checkout
- avoid watch-mode reload and file-by-file auto-restart as the default workflow
- AI-driven edits often touch many files at once, so restart only after a logical batch is ready

Recommended shape:

- `dev`: current checkout where edits happen
- `live`: separate worktree, usually `../web-search-live`, serving the stable local instance on `127.0.0.1:8000`
- optional `preview`: temporary instance from `dev`, usually on `127.0.0.1:8001`, for validating a batch before promotion

Create the stable worktree once:

```bash
git worktree add --detach ../web-search-live HEAD
```

Start the stable HTTP service from the live worktree:

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

The default `.env.example` now pins `UVICORN_WS_PROTOCOL=wsproto` so local startup avoids the deprecated `websockets.legacy` import path.

That keeps service logs, pid files, and temp files under `../web-search-live/.runtime/` instead of `/tmp`.

Check status or stop it with:

```bash
./scripts/local_service.sh status live
./scripts/local_service.sh stop live
```

Use that stable instance for local dogfooding, for example:

```bash
curl -X POST http://127.0.0.1:8000/api/web_search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Model Context Protocol authorization",
    "intent": "general",
    "max_results": 3
  }'
```

Keep making code changes in `dev`.
After a logical batch is ready, validate there with:

```bash
uv run pytest -q
uv run ruff check .
```

If the batch changes versioned release state, also:

```bash
uv sync --extra dev
git tag <new-tag>
git push origin HEAD
git push origin <new-tag>
```

If runtime validation is needed before promotion, start a temporary preview instance from `dev`:

```bash
./scripts/local_service.sh start preview
```

That binds to `127.0.0.1:8001` by default and uses `./.runtime/preview.log`, `./.runtime/preview.pid`, and `./.runtime/tmp/`.

Only after the batch looks good should it be promoted to `live`, followed by a manual restart of the live service.

Before stopping, explicitly note the next highest-value step so the project state stays legible across sessions.

Prefer HTTP over stdio for local dogfooding because one stable HTTP process can serve both the REST API and MCP-over-HTTP callers. Use stdio only when a caller explicitly requires it.

## Code quality rules

When editing Python in this repository, keep these rules:

- validate external inputs at the edge, then pass typed request models through the service layer
- keep the root request contract capability-first; if a knob is only meaningful for one provider, put it in provider-specific options or keep it inside the adapter instead of exposing it at the top level
- prefer direct cleanup over compatibility scaffolding when there are no real external callers to preserve; do not keep deprecated fields, transition shims, or duplicate paths just for hypothetical migrations
- when refactoring, simplify the structure instead of layering adapters on adapters; rewrite the local model or flow if that is the cleaner shape
- if tool-layer inputs are wider than model field types, add an explicit adapter or factory method instead of scattering coercion or broad casts through the code
- do not add `Any` or `cast(...)` just to suppress type checker complaints when the boundary can be modeled properly
- avoid mutating cached response objects after they are stored; copy them before adding request-specific metadata such as cache-hit markers
- keep network client lifecycles explicit; if a client is long-lived, wire startup and shutdown cleanly, otherwise keep it request-scoped
- add or update tests in the same batch as behavior changes
- keep docs aligned to current reality and concise for private use; avoid rollout-style deprecation language unless a real migration path exists

## Validation steps

Before considering a change complete, run:

```bash
uv run pytest -q
uv run ruff check .
```

Also perform a documentation consistency review:

- does README still match current public behavior?
- does `docs/01-public-api.md` still match the real contract?
- does `docs/05-roadmap.md` still reflect phase status honestly?
- do `pyproject.toml`, `uv.lock`, git tags, and pushed GitHub tags still match if this batch changed release state?

---

## Recommended reading order before making changes

1. `README.md`
2. `docs/00-project-purpose.md`
3. `docs/01-public-api.md`
4. `docs/02-capability-model.md`
5. `docs/05-roadmap.md`
6. relevant code

---

## Documentation source of truth

The repository uses focused docs under `docs/` as the main source of truth.

Use these as the primary references:

- `docs/00-project-purpose.md`
- `docs/01-public-api.md`
- `docs/02-capability-model.md`
- `docs/03-error-model.md`
- `docs/04-operations.md`
- `docs/05-roadmap.md`
- `docs/06-development-workflow.md`

`README.md` remains the entrypoint and navigation page.

## Relationship to other docs

Read next:

- `README.md`
- `docs/01-public-api.md`
- `docs/05-roadmap.md`
- relevant code
