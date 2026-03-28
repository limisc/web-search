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
