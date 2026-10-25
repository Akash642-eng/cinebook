locals {
  subnet_config = {
    for index, az in var.availability_zones : az => {
      public_cidr  = var.public_subnet_cidrs[index]
      private_cidr = var.private_subnet_cidrs[index]
    }
  }

  ecr_publish_actions = [
    "ecr:BatchCheckLayerAvailability",
    "ecr:CompleteLayerUpload",
    "ecr:DescribeImages",
    "ecr:DescribeRepositories",
    "ecr:InitiateLayerUpload",
    "ecr:PutImage",
    "ecr:UploadLayerPart"
  ]
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.name_prefix}-vpc"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.name_prefix}-igw"
  }
}

resource "aws_subnet" "public" {
  for_each = local.subnet_config

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value.public_cidr
  availability_zone       = each.key
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.name_prefix}-public-${each.key}"
    Tier = "public-ingress"
  }
}

resource "aws_subnet" "private" {
  for_each = local.subnet_config

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value.private_cidr
  availability_zone       = each.key
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.name_prefix}-private-${each.key}"
    Tier = "private-workloads"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.name_prefix}-public"
  }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  for_each = aws_subnet.private

  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.name_prefix}-private-${each.key}"
  }
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "Public ingress only; intended for a future Application Load Balancer."
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTP ingress; redirect to HTTPS in the future ALB listener."
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS ingress for the future ALB listener."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Egress for future ALB target traffic."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-alb"
  }
}

resource "aws_security_group" "application" {
  name        = "${var.name_prefix}-application"
  description = "Application ports are reachable only from the future ALB security group."
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "CineBook backend API from ALB."
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "CineBook frontend from ALB."
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Outbound application dependencies; restrict further before production."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-application"
  }
}

resource "aws_security_group" "postgres" {
  name        = "${var.name_prefix}-postgres"
  description = "PostgreSQL is private and accepts traffic only from the application security group."
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "PostgreSQL from CineBook application."
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-postgres"
  }
}

resource "aws_security_group" "rabbitmq" {
  name        = "${var.name_prefix}-rabbitmq"
  description = "AMQP is private and accepts traffic only from the application security group; no public management port."
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "AMQP from CineBook application."
    from_port       = 5672
    to_port         = 5672
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-rabbitmq"
  }
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.name_prefix}-backend"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.name_prefix}-backend"
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.name_prefix}-frontend"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.name_prefix}-frontend"
  }
}

resource "aws_iam_role" "github_ecr_publisher" {
  count = var.github_oidc_provider_arn == "" ? 0 : 1

  name = "${var.name_prefix}-github-ecr-publisher"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = var.github_oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:ref:refs/heads/main"
        }
      }
    }]
  })

  tags = {
    Name = "${var.name_prefix}-github-ecr-publisher"
  }
}

resource "aws_iam_role_policy" "github_ecr_publish" {
  count = var.github_oidc_provider_arn == "" ? 0 : 1

  name = "${var.name_prefix}-ecr-publish-only"
  role = aws_iam_role.github_ecr_publisher[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "GetEcrLoginToken"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid      = "PublishOnlyCineBookImages"
        Effect   = "Allow"
        Action   = local.ecr_publish_actions
        Resource = [
          aws_ecr_repository.backend.arn,
          aws_ecr_repository.frontend.arn
        ]
      }
    ]
  })
}
