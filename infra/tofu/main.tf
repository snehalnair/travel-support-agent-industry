# Local kind cluster — the OSS golden-path target for the Kubernetes demo.
#
# NOT APPLIED in Phase 0. This is a validated skeleton (`tofu validate`) only.
# `tofu apply` is deferred to Phase 4.4 (Argo Rollouts canary on kind), where the
# cluster is actually stood up. Applying here would need Docker + the kind binary
# and would create real local infrastructure we don't use yet.
#
# Cloud swap-in: replace this resource (and the provider in versions.tf) with the
# azurerm `azurerm_kubernetes_cluster` (AKS) resource. Everything downstream — the
# Helm releases and Argo Rollouts manifests — targets the kubeconfig this module
# emits, so the swap stays local to this file. See README.md.
resource "kind_cluster" "this" {
  name           = var.cluster_name
  node_image     = "kindest/node:${var.kubernetes_version}"
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }

    # One node block per worker. range(0) yields no blocks (control-plane only).
    dynamic "node" {
      for_each = range(var.worker_count)
      content {
        role = "worker"
      }
    }
  }
}
