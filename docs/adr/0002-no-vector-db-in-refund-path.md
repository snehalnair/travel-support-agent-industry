# ADR-0002: No vector database in the refund decision path

- Status: Accepted
- Date: 2026-05-31
- Deciders: Snehal Nair

## Context

The refund/cancellation flow must retrieve two things for a request: the booking record and the
cancellation policy that applies to it. The default reflex in LLM/agent systems is to reach for a
vector database (e.g., Qdrant) and semantic/RAG retrieval. We must decide whether retrieval in the
refund *decision path* is similarity-based or structured.

Facts that drive the decision:
- Bookings and policies are **structured records with stable keys** (booking_id, product_id, policy_id).
  A booking maps to exactly one applicable policy via a deterministic key, not by fuzzy resemblance.
- Refund correctness is a **hard, money-adjacent invariant**. Retrieving a *similar* policy instead of
  the *correct* one is a correctness/safety failure, not a relevance nuisance.
- The corpus is bounded and synthetic — there is no large unstructured body of text to search.

## Decision

Retrieve bookings and policies via **structured keyed lookups in PostgreSQL** (exact joins on IDs).
**No vector database is in the refund decision path.** Qdrant and semantic search are cut on principle
there, not deferred for effort.

**Permitted extension (non-authoritative).** A read-only `KnowledgeSearchPort` may use a vector store
(Qdrant / Weaviate / pgvector) for support-document retrieval — help-center QA, supplier notes,
explanation drafting. It may *explain or cite* policy context but may **not** select the applicable
policy, compute refunds, authorize access, or trigger state changes. Retrieved text is untrusted
context, subject to the same injection rules as customer input. The ban is scoped to the decision
path, not the whole system. See PLAN.md, "Vector DB experience / extension point".

## Consequences

Positive:
- **Deterministic, auditable retrieval** — a booking always resolves to exactly one policy; no
  approximate-nearest-neighbor nondeterminism in a money path.
- **Simpler stack** — one datastore instead of Postgres + vector DB + embedding model + indexing/sync
  pipeline. Fewer failure modes, lower cost, faster CI.
- **Testable** — retrieval correctness is a relational assertion against fixtures, not a recall@k metric.
- Aligns with the Constitution's deterministic-decides principle.

Negative:
- The optional knowledge-search sidecar, if built, adds its own surface (index freshness, reranking,
  retrieval eval) — but outside the decision path, where its failures are advisory, not financial.
- We forgo "demonstrating RAG" in the core flow — mitigated by the sidecar and by making the judgment
  explicit (this ADR).

## Alternatives considered

- **Vector DB + RAG (Qdrant) for policy *selection*** — Rejected: injects approximate retrieval and
  nondeterminism into a correctness-critical path, and adds an embedding model + index + sync pipeline
  to solve what is a primary-key lookup. Structure-first beats similarity here.
- **No vector DB anywhere (blanket ban)** — Rejected: too broad. Forfeits legitimate help-center /
  agent-assist retrieval and signals absolutism rather than scoped judgment.
- **In-memory dict / flat files for the decision path** — Rejected: loses transactional integrity,
  migrations, and the production-realistic state story Postgres provides.

## Revisit when

The knowledge-search sidecar moves from optional to required, or a new authoritative lookup appears
that genuinely needs similarity matching. Add it as a *separate, non-authoritative* path; the
deterministic policy lookup stays. A material change supersedes this ADR rather than editing it.
