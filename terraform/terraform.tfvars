# terraform/terraform.tfvars
# DO NOT commit this file to Git — add to .gitignore

project_id        = "smart-shop-ai-496616"
region            = "us-central1"
zone              = "us-central1-a"
cluster_name      = "smartshop-cluster"
node_machine_type = "n1-standard-4"
min_node_count    = 1
max_node_count    = 5
initial_node_count = 2
docker_image      = "aishwaryadheeru/smartshop-ai:v1"
bq_dataset        = "smartshop"
bq_location       = "US"
google_api_key    = "your-google-api-key-here"