# travel-support-agent v2 — Roadmap & Progress

Companion to [`PLAN.md`](./PLAN.md). Phases come from `PLAN.md §10`, broken into trackable steps.
This file is the **single source of truth** for progress, maintained by the coaching assistant and
updated in the same commit that lands each step.

**Updated:** 2026-05-31
**Legend:** ✅ Done · 🔄 In progress · ⬜ Todo

| Phase | # | Step | Status |
|---|---|---|---|
| **0 · Scaffold + infra** | 0.1 | uv package scaffold (src layout, `pyproject.toml`, smoke test) | ✅ |
| | 0.2 | `.gitignore` (self-contained repo) | ✅ |
| | 0.3 | ADR-0001 — Kubernetes golden path | ✅ |
| | 0.4 | Toolchain config (ruff + pyright + pytest) | ✅ |
| | 0.5 | CI pipeline — GitHub Actions, 3 parallel jobs, green | ✅ |
| | 0.6 | pre-commit hooks + `.editorconfig` | ✅ |
| | 0.7 | Container engine — colima (Docker Desktop org-locked) | ✅ |
| | 0.8 | `PLAN.md` — canonical engineering plan | 🔄 |
| | 0.9 | ADR-0002 — no vector DB in refund path | ⬜ |
| | 0.10 | Docker Compose spine — Postgres + Phoenix (walking skeleton) | ⬜ |
| | 0.11 | Terraform skeleton — kind, AKS-ready, *not applied* | ⬜ |
| | — | **Exit gate:** `docker compose up` healthy · CI green · plan + ADRs committed | ⬜ |
| **1 · Data + state** | 1.1 | Synthetic fixtures — bookings + refund policies | ⬜ |
| | 1.2 | Pandera schemas (data contracts at the boundary) | ⬜ |
| | 1.3 | Presidio PII scan in the validation step | ⬜ |
| | 1.4 | Postgres schema + Alembic migrations | ⬜ |
| | 1.5 | Seed / ingestion script | ⬜ |
| | — | **Exit gate:** seeded DB + validation passing in CI | ⬜ |
| **2 · Agent core** | 2.1 | LiteLLM gateway (provider-swappable, retries/budget) | ⬜ |
| | 2.2 | LangGraph state machine — REFUND flow | ⬜ |
| | 2.3 | Deterministic safety gates — IDOR, injection/PII, confirmation | ⬜ |
| | 2.4 | Structured output schema + repair/retry (fail-closed) | ⬜ |
| | 2.5 | Refund calculation — deterministic, policy-encoded, tested | ⬜ |
| | — | **Exit gate:** end-to-end refund happy-path + gates demoable | ⬜ |
| **3 · Eval** | 3.1 | Inspect AI golden suite (100–300 cases) | ⬜ |
| | 3.2 | PyRIT adversarial suite (200–1000 attacks) | ⬜ |
| | 3.3 | SS016–SS018 invariant tests (must pass 100%) | ⬜ |
| | 3.4 | Wire eval gates into CI | ⬜ |
| | — | **Exit gate:** eval gates block a bad deploy | ⬜ |
| **4 · Deploy + observe** | 4.1 | Phoenix + OTel tracing wired through the agent | ⬜ |
| | 4.2 | Grafana service dashboards (latency/error/cost) | ⬜ |
| | 4.3 | Helm chart | ⬜ |
| | 4.4 | Argo Rollouts canary on kind | ⬜ |
| | 4.5 | Rollback drill (< 5 min) | ⬜ |
| | 4.6 | Close the offline↔online flywheel | ⬜ |
| | — | **Exit gate:** canary deploy + rollback + live traces | ⬜ |

## Where we are

Phase 0 ~64% (7/11). The only step *blocking* the Phase 0 exit gate is the Compose spine (0.10),
now unblocked by colima. Active: **0.8** (commit `PLAN.md`) → **0.9** (ADR-0002) → **0.10** (Compose).

## Maintenance

The Status column changes in the same commit that does the work. This file passes through the same
pre-commit hooks and CI as source code, so progress can't silently drift out of sync.
