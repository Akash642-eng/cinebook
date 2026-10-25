terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Used only by CI's offline plan. Never use placeholder credentials for apply.
  access_key = var.offline_plan_validation ? "offline-placeholder" : null
  secret_key = var.offline_plan_validation ? "offline-placeholder" : null

  skip_credentials_validation = var.offline_plan_validation
  skip_metadata_api_check     = var.offline_plan_validation
  skip_region_validation      = var.offline_plan_validation
  skip_requesting_account_id  = var.offline_plan_validation

  default_tags {
    tags = {
      Project     = "CineBook"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
