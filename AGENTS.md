# web-search agent instructions

This repository can be used while it is being developed. Keep the callable local service stable.

## Mandatory workflow for local dogfooding

When coding in this repo and also using its own `web_search` or `web_extract` capability:

- keep a stable local service separate from the actively edited checkout
- prefer a separate git worktree for the stable service, usually `../web-search-live`
- keep routine calls pointed at the stable HTTP service, usually `127.0.0.1:8000`
- make code changes in the current checkout only
- do not use watch-mode reload, file-triggered rebuilds, or auto-promotion as the default workflow
- AI-driven edits often touch many files; restart only after a logical batch is ready

## Code development requirements

When changing Python code in this repository:

- keep boundary validation explicit at the edge; parse tool and HTTP inputs into typed request models before service logic
- keep the root request contract capability-first; do not leak provider-specific knobs into top-level schema fields when they belong in provider-specific option objects or adapter internals
- prefer the current clean shape over transition scaffolding; do not keep compatibility shims, deprecated fields, or dual paths unless an active caller really needs them
- during refactors, reduce moving parts; do not stack patch-on-patch adapters when rewriting the section or model directly is cleaner
- do not silence the type system with broad `Any` or `cast(...)` just to make editor warnings disappear; if an input boundary is wider than the internal model, add a dedicated typed adapter or factory method
- prefer small typed helpers over implicit coercion spread across handlers and services
- avoid mutating shared cached objects after storing them; return copies when cached state needs request-specific metadata
- own resource lifecycles explicitly; do not keep long-lived network clients around unless startup and shutdown are also wired cleanly
- keep docs concise and aligned to current reality; avoid public-rollout or deprecation-heavy wording unless a real migration path is needed
- if behavior changes, add or update tests in the same batch
- finish each logical batch with `uv run pytest -q` and `uv run ruff check .`
- before every commit, do a self-audit of code, docs, tests, versioning, and runtime behavior; do not commit if there are known leftovers, stale docs, editor-type errors, or unreviewed behavior changes
- when a logical batch changes public behavior, routing, provider capability support, cache semantics, or docs, re-read `README.md` and the relevant `docs/*.md` files and update them in the same batch
- when preparing a release-style commit or version bump, update `pyproject.toml`, refresh `uv.lock`, create the matching git tag, and push both the commit and the tag to GitHub
- after each completed batch, explicitly review what the next highest-value step should be before stopping

## Default loop

1. Start or reuse the stable `live` service from the separate worktree.
2. Do code changes in `dev`.
3. Before committing, run a self-check:
   - inspect `git status`
   - review changed code for leftovers or hacky transition paths
   - review `README.md` and relevant `docs/*.md` for stale statements
   - run type and test checks appropriate to the batch
   - confirm whether version, tag, and `uv.lock` also need updates
4. After a logical batch, run:

```bash
uv run pytest -q
uv run ruff check .
```

5. If runtime validation is needed, start a temporary `preview` instance from `dev` on another port, usually `8001`, with `./scripts/local_service.sh start preview`.
6. Only after the batch passes, manually promote the chosen commit to the `live` worktree and restart the live service.
7. If the batch also bumps the release version, update `pyproject.toml`, refresh `uv.lock`, create the matching git tag, and push both the branch and tag to GitHub.
8. Unless the user explicitly asks to test preview, keep other tools, scripts, and agents pointed at `live`, not `preview`.
9. Before stopping, state the next highest-value step.

## Preferred transport

For local dogfooding, prefer HTTP over stdio. One stable HTTP process can serve:
- `/api/web_search`
- `/api/web_extract`
- `/mcp`

Use stdio only when a caller explicitly needs stdio.

## Setup reference

If no stable local worktree exists yet, create one with:

```bash
git worktree add --detach ../web-search-live HEAD
```

For local HTTP runs, prefer `./scripts/local_service.sh` so logs, pid files, and temp files stay under `.runtime/` inside the checkout instead of spilling into `/tmp`.

See `docs/06-development-workflow.md` for the full procedure and command examples.

## Maintenance rule

If this workflow changes, update both:
- `AGENTS.md`
- `docs/06-development-workflow.md`
