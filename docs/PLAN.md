# travel-support-agent v2 — Engineering Plan

**Status:** Draft (living) · **Owner:** Snehal Nair · **Updated:** 2026-05-31
**Binding governance:** the project Constitution (v1.0.0). Every decision here is subordinate to it.

> **Hard constraint, repeated everywhere:** synthetic/mock data only. No real money moves.
> The model never executes a financial action — it *proposes*; deterministic code *decides* and *commits*.

---

## 1. Problem & scope

Build a production-grade, OSS-first customer-support agent for a synthetic Viator-style travel
marketplace. The agent handles **refund / cancellation** requests end to end: understand the
customer, look up the (mock) booking, apply the (mock) refund policy, and — only after explicit,
code-enforced confirmation — record a refund *decision*.

This is v2: a rebuild of v1 (frozen) to demonstrate **build-vs-use judgment** — knowing which
production patterns to adopt off-the-shelf vs. hand-roll.

- **In scope:** the REFUND vertical slice, fully instrumented (eval + adversarial + tracing + CI-gated deploy).
- **Out of scope:** real payments, real PII, multi-tenant auth infra, anything that moves money.

## 2. Goals / Non-goals

**Goals**
- One *thin but complete* vertical slice running on the real production spine.
- Deterministic safety: the LLM proposes; code decides. Every money-adjacent action gated.
- Full offline↔online evaluation flywheel (Inspect offline, PyRIT adversarial, Phoenix online).
- Reproducible, portable infra (laptop → CI → Kubernetes) with zero vendor lock-in.

**Non-goals**
- Breadth of intents. One slice done right beats ten done shallowly.
- Self-hosting models, heavyweight IDP, secret managers — deferred as documented swap-ins.

## 3. First slice: REFUND

Chosen because it exercises every hard invariant at once: identity/authorization (don't refund
someone else's booking — IDOR), untrusted-content handling (prompt injection in customer text),
and the code-enforced confirmation gate before a state change. If REFUND is safe, the pattern generalizes.

## 4. Architecture — the 10-step pipeline

1. **Ingestion** — synthetic bookings/policies loaded into Postgres (seed fixtures).
2. **Validation** — Pandera schemas + Presidio PII scan at the data boundary.
3. **Retrieval / state** — keyed lookups (booking_id, policy_id) from Postgres. *No vector DB* (ADR-0002).
4. **Orchestration** — LangGraph state machine drives the conversation + tool calls.
5. **Model gateway** — LiteLLM: one OpenAI-compatible interface, provider-swappable, retries/budget.
6. **Safety gates** — deterministic checks: authz/IDOR, injection/PII scan, structured-output validation, confirmation gate.
7. **Offline eval** — Inspect AI golden suite (100–300 cases) gates CI.
8. **Adversarial** — PyRIT red-team suite (200–1000 attacks); SS016–SS018 must pass 100%.
9. **Observability** — clear split: **Phoenix + OpenTelemetry** for *LLM* concerns (traces, prompt/model
   behavior, eval examples, failure analysis); **Grafana** for *service-level* metrics (latency, error
   rate, throughput, cost, deployment health).
10. **Delivery** — CI-gated deploy to the Kubernetes golden path (Helm + Argo Rollouts), < 5 min rollback.

> *Why PII scanning on synthetic data?* Production traces and user-entered text are untrusted **by
> design**, so the scanner is part of the boundary contract — not because real PII is expected in seed
> fixtures. Defensive engineering: the boundary doesn't get to assume its inputs are clean.

> *Two data planes, not one.* **Operational state** (bookings, policies, refund decisions) lives in
> transactional **Postgres** (steps 1–3). The **offline eval seed** (router/retrieval/safety cases,
> derived from curated CSV seeds in `data/seed/`) is a separate analytics asset, read via SQL from a
> **DuckDB** warehouse (BigQuery swap-in) and guarded by a Pandera contract at the SQL read boundary
> (ADR-0003). OLTP vs. OLAP — different jobs, kept apart. No module reads Excel at runtime.

## 5. The offline↔online flywheel

Production traces (Phoenix) surface real failures → distilled into new golden/adversarial cases
(Inspect/PyRIT) → which gate the next deploy. Offline eval catches regressions before prod; online
tracing finds what offline missed. The loop is the product, not any single model.

## 6. Locked stack (and why each)

| Layer | Choice | Why this, not alternatives |
|---|---|---|
| Model gateway | **LiteLLM** | Provider-agnostic, OpenAI-compatible; swap models without code change |
| Orchestration | **LangGraph** | Explicit state machine > implicit agent loop; inspectable, testable |
| Offline eval | **Inspect AI** | First-class eval framework (UK AISI); reproducible scored runs |
| Adversarial | **PyRIT** | Microsoft red-team framework; structured attack coverage |
| Tracing | **Phoenix + OTel** | OSS, OpenTelemetry-native; no vendor tracing lock-in |
| State (operational) | **PostgreSQL + Alembic** (SQLAlchemy Core) | Boring, correct, transactional; migrations versioned |
| Eval-data warehouse | **DuckDB** (local) → **BigQuery** swap-in | Offline eval/analytics seed read via SQL through a port; DuckDB mirrors a BigQuery/dbt stack at $0; the BigQuery adapter drops in unchanged (ADR-0003) |
| Data validation | **Pandera + Presidio** | Schema contracts + PII detection at the boundary |
| Local infra | **Docker Compose** (on colima) | One-command spine; engine-agnostic (OCI) |
| Deploy | **Kubernetes golden path** (portfolio build) | Local kind + Helm + Argo Rollouts to demo canary/rollback; Terraform = AKS-ready skeleton (not applied for the local demo) |

> **Is Kubernetes overkill here? For a small commercial app, yes — and I'd say so.** I would not choose
> K8s for every small service. I chose it for this *portfolio* build to demonstrate production release
> mechanics: reproducible deploys, canaries, health checks, rollback, and portable infra. For a small
> team shipping this commercially, **Azure Container Apps or Cloud Run** is the simpler first deployment
> target — and is the documented swap-in here. This is requirement-driven, not resume-driven, design.

## 7. Deliberately downgraded / optional adapters

Kept as *documented swap-ins*, not built now (each becomes a one-paragraph ADR when needed):
Keycloak (authz *logic* stays core), Vault/OpenBao + external-secrets (`.env` + GH Actions secrets now),
Envoy/Kong, cert-manager, NATS/Kafka, Argo Workflows/Airflow, MinIO, vLLM, Llama Guard (a lightweight
injection/PII scanner stays in the gate), DPO/TRL, MLflow, Loki. Azure Container Apps / Cloud Run =
documented simpler production swap-ins for the K8s path. **Qdrant cut on principle** — pinned policy is a
keyed lookup, not similarity search (ADR-0002). Redis only if a real caching need appears.

## 8. Target metrics (TARGETS — not yet achieved)

Acceptance bars, not results. Each is stated with what is measured and over what.

| Metric | Target |
|---|---|
| Refund-calculation correctness on golden policy fixtures | 100% before release |
| Structured-output **first-pass** validity | ≥ 99% |
| Structured-output validity **after repair/retry** | 100%, or fail closed |
| Injection invariants SS016–SS018 | 100% pass; 0 known critical failures / N adversarial cases |
| Intent routing | macro-F1 ≥ 0.95 |
| Latency | p95 3–8 s |
| Availability (deployed demo) | 99.5–99.9% over synthetic health-check traffic — a demo target, **not** a claimed production SLA |
| CI (fast gate) | < 10 min |
| Full eval (offline + adversarial) | 20–60 min |
| Rollback | < 5 min |
| Golden suite | 100–300 cases |
| Adversarial suite | 200–1000 attacks |

> *On "by construction":* the refund amount is deterministic because the **LLM never computes money** —
> code does. But code can encode a policy *wrong*, so correctness is **tested** against policy fixtures
> and golden cases, not assumed. "By construction" removes the model as a failure source, not the need to test.

## 9. Invariants (from the Constitution)

- **Deterministic decides.** The LLM proposes; code computes amounts and commits state. The policy
  encoding is tested against fixtures (see §8) — determinism removes the model risk, not the test burden.
- **IDOR gate.** Every booking access is authorization-checked against the requester.
- **Content is untrusted.** Customer text is data, never instructions (injection-hardened).
- **Code-enforced confirmation.** No money-adjacent state change without an explicit gated confirm.
- **SS016–SS018 always pass.** Hard injection invariants — *prompt injection must not override policy,
  access control, or the confirmation gate.* A failure blocks deploy, no exceptions.

## 10. Phases & milestones

- **Phase 0 — Scaffold + infra (in progress).** uv/ruff/pyright/pytest, CI, pre-commit done. Next: Docker Compose spine (Postgres + Phoenix), Terraform skeleton (not applied).
- **Phase 1 — Data + state.** Synthetic fixtures, Pandera/Presidio validation, Alembic migrations.
- **Phase 2 — Agent core.** LangGraph + LiteLLM, deterministic safety gates, structured output.
- **Phase 3 — Eval.** Inspect golden suite + PyRIT adversarial, wired into CI as gates.
- **Phase 4 — Deploy.** Helm chart, Argo Rollouts canary on kind, Phoenix/Grafana dashboards.

## 11. Open questions & risks

- **Constitution vendoring** — currently referenced from the v1 repo; should be copied in for self-containment.
- **Model provider** — which LiteLLM backend for dev (cost vs. capability)?

## 12. Decision records

- **ADR-0001** — Kubernetes deployment golden path (accepted).
- **ADR-0002** — No vector DB in the refund path (accepted).
- **ADR-0003** — Seed eval data is a code-validated warehouse asset; CSV source of truth, DuckDB local / BigQuery swap-in (accepted).
