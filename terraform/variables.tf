variable "aws_region" {
  description = "AWS Region for the future CineBook foundation."
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name used in resource tags."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "name_prefix" {
  description = "Lowercase prefix for AWS resource names."
  type        = string
  default     = "cinebook-dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.name_prefix))
    error_message = "name_prefix must be 3-21 lowercase letters, digits, or hyphens and start with a letter."
  }
}

variable "enable_infrastructure" {
  description = "Explicit opt-in to plan/create the AWS foundation. Keep false until cost and apply approvals are complete."
  type        = bool
  default     = false
}

variable "offline_plan_validation" {
  description = "Use dummy credentials and provider validation skips for CI-only planning without AWS API calls. Never use for apply."
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "CineBook VPC CIDR."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "Two Availability Zones. Confirm they are supported in aws_region before any real plan/apply."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]

  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "Supply exactly two distinct Availability Zones."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public ingress subnets, ordered to match availability_zones."
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Supply exactly two public subnet CIDRs."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDRs for private application/data subnets, ordered to match availability_zones."
  type        = list(string)
  default     = ["10.20.11.0/24", "10.20.12.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Supply exactly two private subnet CIDRs."
  }
}

variable "github_repository" {
  description = "Exact GitHub repository allowed to assume the ECR publishing role."
  type        = string
  default     = "Akash642-eng/cinebook"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/repository form."
  }
}

variable "github_oidc_provider_arn" {
  description = "Existing IAM OIDC provider ARN for token.actions.githubusercontent.com. Empty disables the GitHub publishing role."
  type        = string
  default     = ""

  validation {
    condition = var.github_oidc_provider_arn == "" || can(regex(
      "^arn:[a-z0-9-]+:iam::[0-9]{12}:oidc-provider/token[.]actions[.]githubusercontent[.]com$",
      var.github_oidc_provider_arn
    ))
    error_message = "Use the ARN of the existing GitHub Actions OIDC provider, or leave empty to disable the role."
  }
}
