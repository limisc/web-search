# README / docs split proposal

Goal: make the repository easier for both future humans and AI agents to understand quickly.

## Current state

Right now:

- `README.md` is the root landing page
- focused docs exist under `docs/`
- the old single-file planning approach has already been retired

The main job now is not to design the split anymore. The main job is to keep future updates centered on the focused docs instead of letting large overlapping root documents grow back.

---

## Problem the split was solving

Previously, project purpose, current state, capability model, public contract, roadmap, and workflow guidance were mixed into a very small number of large documents.

That made convergence easier in the short term, but it created long-term maintenance risks:

- purpose, current state, and workflow were mixed together
- updates could easily drift between files
- both humans and AI had to scan too much before finding the right section

---

## Resulting structure

## 1. `README.md`

Purpose:

- act as the landing page
- explain what the repo is in a small number of paragraphs
- show the current public surface
- provide quick start instructions
- point readers to the deeper docs

README should stay short and stable.

---

## 2. `docs/00-project-purpose.md`

Purpose:

- preserve the north star
- explain why this project exists
- explain why it is not just a provider aggregator

---

## 3. `docs/01-public-api.md`

Purpose:

- define the stable external contract
- define the current public surface
- document compatibility expectations

---

## 4. `docs/02-capability-model.md`

Purpose:

- define the semantic model independent of provider brands
- document routing lanes and degraded behavior

---

## 5. `docs/03-error-model.md`

Purpose:

- standardize failure handling semantics
- make client and agent behavior more predictable

---

## 6. `docs/04-operations.md`

Purpose:

- capture security, deployment, and observability expectations

---

## 7. `docs/05-roadmap.md`

Purpose:

- hold phase planning and current roadmap status in one place

---

## 8. `docs/06-development-workflow.md`

Purpose:

- tell future humans and AI agents how to change the repo safely

---

## 9. `docs/99-readme-structure-proposal.md`

Purpose:

- record why the split happened
- preserve the documentation design rationale
- prevent the repository from drifting back to oversized overlapping root docs

---

## Best reading order for humans / AI

### For quick understanding

1. `README.md`
2. `docs/00-project-purpose.md`
3. `docs/01-public-api.md`
4. `docs/02-capability-model.md`

### For making changes

1. `README.md`
2. `docs/06-development-workflow.md`
3. `docs/01-public-api.md`
4. `docs/05-roadmap.md`
5. relevant code

### For debugging behavior

1. `docs/01-public-api.md`
2. `docs/03-error-model.md`
3. `docs/04-operations.md`
4. relevant provider / service code

---

## Concrete recommendation going forward

### Keep in `README.md`

- project purpose summary
- current public surface summary
- current implementation summary
- quick start
- links to docs

### Keep in `docs/`

- detailed capability model
- provider support / degraded behavior
- error semantics
- roadmap / phase planning
- development discipline
- operations / security / observability

### Avoid reintroducing

- large root planning documents
- duplicated detailed specs in both README and deeper docs
- roadmap detail mixed into the landing page

---

## Maintenance rule

If a future change adds detail, prefer updating the focused document under `docs/` instead of growing `README.md`.

README should remain the entrypoint.
The focused docs should remain the source of truth.
