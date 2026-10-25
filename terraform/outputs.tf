output "vpc_id" {
  description = "Created VPC ID, or null while infrastructure is disabled."
  value       = try(module.foundation[0].vpc_id, null)
}

output "public_subnet_ids" {
  description = "Public subnet IDs intended for a future load balancer."
  value       = try(module.foundation[0].public_subnet_ids, [])
}

output "private_subnet_ids" {
  description = "Private subnet IDs intended for future application and data services."
  value       = try(module.foundation[0].private_subnet_ids, [])
}

output "backend_ecr_repository_url" {
  description = "Private ECR repository URL for backend images."
  value       = try(module.foundation[0].backend_ecr_repository_url, null)
}

output "frontend_ecr_repository_url" {
  description = "Private ECR repository URL for frontend images."
  value       = try(module.foundation[0].frontend_ecr_repository_url, null)
}

output "github_ecr_publisher_role_arn" {
  description = "Least-privilege ECR publishing role ARN, or null until an OIDC provider ARN is supplied."
  value       = try(module.foundation[0].github_ecr_publisher_role_arn, null)
}
