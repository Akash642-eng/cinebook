output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = [for subnet in aws_subnet.public : subnet.id]
}

output "private_subnet_ids" {
  value = [for subnet in aws_subnet.private : subnet.id]
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "application_security_group_id" {
  value = aws_security_group.application.id
}

output "postgres_security_group_id" {
  value = aws_security_group.postgres.id
}

output "rabbitmq_security_group_id" {
  value = aws_security_group.rabbitmq.id
}

output "backend_ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "github_ecr_publisher_role_arn" {
  value = try(aws_iam_role.github_ecr_publisher[0].arn, null)
}
