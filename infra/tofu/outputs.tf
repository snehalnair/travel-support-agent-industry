output "cluster_name" {
  description = "Name of the kind cluster. The kubeconfig context is kind-<name>."
  value       = kind_cluster.this.name
}

output "kubeconfig_path" {
  description = "Filesystem path to the generated kubeconfig. Helm and Argo Rollouts target this."
  value       = kind_cluster.this.kubeconfig_path
}

output "endpoint" {
  description = "Kubernetes API server endpoint of the kind cluster."
  value       = kind_cluster.this.endpoint
}
