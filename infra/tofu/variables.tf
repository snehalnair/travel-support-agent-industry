variable "cluster_name" {
  description = "Name of the local kind cluster. The kubeconfig context becomes kind-<name>."
  type        = string
  default     = "tsa-dev"
}

variable "kubernetes_version" {
  description = "Kubernetes version tag for the kind node image (e.g. \"v1.31.0\"). Pin to an image digest before the Phase 4 apply."
  type        = string
  default     = "v1.31.0"
}

variable "worker_count" {
  description = "Number of worker nodes, in addition to the single control-plane node."
  type        = number
  default     = 1

  validation {
    condition     = var.worker_count >= 0
    error_message = "worker_count must be zero or greater."
  }
}
