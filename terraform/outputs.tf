# terraform/outputs.tf

output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.smartshop_cluster.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.smartshop_cluster.endpoint
  sensitive   = true
}

output "cluster_location" {
  description = "GKE cluster location"
  value       = google_container_cluster.smartshop_cluster.location
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.smartshop.dataset_id
}

output "storage_bucket" {
  description = "Cloud Storage bucket name"
  value       = google_storage_bucket.smartshop_data.name
}

output "connect_to_cluster" {
  description = "Command to connect kubectl to the cluster"
  value       = "gcloud container clusters get-credentials ${var.cluster_name} --zone ${var.zone} --project ${var.project_id}"
}

output "node_machine_type" {
  description = "Node machine type"
  value       = var.node_machine_type
}
