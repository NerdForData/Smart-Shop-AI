# terraform/main.tf

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# ── Provider ───────────────────────────────────────

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable Required APIs ───────────────────────────

resource "google_project_service" "container" {
  service            = "container.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "bigquery" {
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

# ── VPC Network ────────────────────────────────────

resource "google_compute_network" "smartshop_vpc" {
  name                    = "smartshop-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.container]
}

resource "google_compute_subnetwork" "smartshop_subnet" {
  name          = "smartshop-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.smartshop_vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# ── GKE Cluster ────────────────────────────────────

resource "google_container_cluster" "smartshop_cluster" {
  name     = var.cluster_name
  location = var.zone

  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.smartshop_vpc.name
  subnetwork = google_compute_subnetwork.smartshop_subnet.name

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Enable workload identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  depends_on = [google_project_service.container]
}

# ── GKE Node Pool ──────────────────────────────────

resource "google_container_node_pool" "smartshop_nodes" {
  name     = "smartshop-node-pool"
  location = var.zone
  cluster  = google_container_cluster.smartshop_cluster.name

  # Auto-scaling
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  initial_node_count = var.initial_node_count

  node_config {
    machine_type = var.node_machine_type   # n1-standard-4 = 15GB RAM
    disk_size_gb = 50
    disk_type    = "pd-standard"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      app = "smartshop-ai"
    }

    tags = ["smartshop-node"]
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# ── BigQuery Dataset ───────────────────────────────

resource "google_bigquery_dataset" "smartshop" {
  dataset_id = var.bq_dataset
  location   = var.bq_location

  labels = {
    environment = "production"
    project     = "smartshop-ai"
  }

  depends_on = [google_project_service.bigquery]
}

# ── BigQuery Tables ────────────────────────────────

resource "google_bigquery_table" "products" {
  dataset_id          = google_bigquery_dataset.smartshop.dataset_id
  table_id            = "products"
  deletion_protection = false

  schema = jsonencode([
    { name = "product_id",   type = "STRING"  },
    { name = "name",         type = "STRING"  },
    { name = "category",     type = "STRING"  },
    { name = "price",        type = "FLOAT"   },
    { name = "description",  type = "STRING"  },
    { name = "weight_grams", type = "FLOAT"   }
  ])
}

resource "google_bigquery_table" "orders" {
  dataset_id          = google_bigquery_dataset.smartshop.dataset_id
  table_id            = "orders"
  deletion_protection = false

  schema = jsonencode([
    { name = "order_id",                 type = "STRING"    },
    { name = "customer_id",              type = "STRING"    },
    { name = "order_status",             type = "STRING"    },
    { name = "order_purchase_timestamp", type = "TIMESTAMP" },
    { name = "total_amount",             type = "FLOAT"     },
    { name = "review_score",             type = "FLOAT"     }
  ])
}

resource "google_bigquery_table" "fraud_transactions" {
  dataset_id          = google_bigquery_dataset.smartshop.dataset_id
  table_id            = "fraud_transactions"
  deletion_protection = false

  schema = jsonencode([
    { name = "transaction_id", type = "STRING"  },
    { name = "amount",         type = "FLOAT"   },
    { name = "merchant",       type = "STRING"  },
    { name = "category",       type = "STRING"  },
    { name = "state",          type = "STRING"  },
    { name = "fraud_label",    type = "INTEGER" }
  ])
}

# ── Cloud Storage Bucket ───────────────────────────

resource "google_storage_bucket" "smartshop_data" {
  name          = "smartshop-data-${var.project_id}"
  location      = "US"
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.storage]
}