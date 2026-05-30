# ADR-0001: Kubernetes as the deployment golden path

- Status: Accepted
- Date: 2026-05-31
- Deciders: Snehal Nair

## Context
[Why a decision is needed. Hit: this is a solo, $0-budget portfolio rebuild that
must actually ship; the original plan was incoherent — it claimed "Kubernetes-native"
but Phase 8 said "Azure Container Apps", which are two different deployment stories;
the two interview targets are MS ISE (Azure-leaning) and Cohere (OSS/research-leaning);
we need ONE golden path with a swap-in story, not two half-built ones.]

## Decision
[What we chose. Hit: Kubernetes golden path —
Docker → Helm → Terraform (written AKS-ready) → local kind/k3d cluster →
Argo Rollouts canary with auto-rollback. Azure Container Apps is documented as a
swap-in, not built.]

## Consequences
[The trade-offs — both directions.
Positive: gives the canary + rollback process numbers (rollback <5 min on error-rate
spike); matches my real K8s background so I can speak to it authentically; more portable
story for both targets; runs on local kind so cost = $0 and "going live is one
`terraform apply`".
Negative: more ops surface than Container Apps; no permanently-live public URL on local
kind (demo via port-forward / recording); I have to maintain Helm + Terraform.]

## Alternatives considered
[- **Azure Container Apps**: lower ops, gives a live URL, Azure-aligned for ISE — but
  weaker CD narrative (no Helm/Argo canary) and a weaker portability claim. Rejected as
  primary; kept as the documented swap-in.
- **Pure cloud-agnostic, no named cloud**: cleanest OSS story but nothing concrete to
  point at. Rejected.]