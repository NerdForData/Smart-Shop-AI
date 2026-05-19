# terraform/variables.tf

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "smart-shop-ai-496616"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "cluster_name" {
  description = "GKE Cluster name"
  type        = string
  default     = "smartshop-cluster"
}

variable "node_machine_type" {
  description = "GKE node machine type"
  type        = string
  default     = "n1-standard-4"   # 4 vCPU, 15GB RAM — enough for ML model
}

variable "min_node_count" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of nodes"
  type        = number
  default     = 5
}

variable "initial_node_count" {
  description = "Initial number of nodes"
  type        = number
  default     = 2
}

variable "docker_image" {
  description = "Docker image for SmartShop AI"
  type        = string
  default     = "aishwaryadheeru/smartshop-ai:v1"
}

variable "google_api_key" {
  description = "Google API key for Gemini"
  type        = string
  sensitive   = true
}

variable "bq_dataset" {
  description = "BigQuery dataset name"
  type        = string
  default     = "smartshop"
}

variable "bq_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}