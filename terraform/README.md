# CineBook AWS Terraform Foundation (plan-only by default)

This is a **foundation**, not a live AWS deployment. It prepares a VPC with two public ingress subnets and two isolated private subnets, security groups for a future ALB/application/PostgreSQL/RabbitMQ architecture, immutable ECR repositories, and an optional GitHub Actions OIDC role with ECR-publish-only permissions.

## Important guardrails

- `enable_infrastructure` defaults to `false`. A normal plan creates no AWS resources.
- The CI plan uses `offline_plan_validation=true`, dummy provider credentials, `-refresh=false`, and no `apply`; it validates Terraform structure and displays the proposed resource graph without authenticating to AWS or calling AWS APIs. This is **not** an account-aware cost or drift plan.
- Never use offline placeholder credentials or a CI plan file for `terraform apply`.
- No AWS resources are created by this repository workflow. The actual AWS account has not been inspected because no AWS account/credentials were provided or configured.
- No NAT Gateway, ALB, ECS/EKS compute, RDS instance, or Amazon MQ broker is included in this cost-conscious foundation. Private subnets intentionally have no default internet route. Future workloads need a reviewed egress strategy (for example VPC endpoints or NAT) before deployment.
- Do not apply until cost, region/AZ support, state storage/locking, IAM trust, rollback and teardown have been reviewed.

## Local commands (PowerShell)

From the repository root:

```powershell
Set-Location "$HOME\Projects\cinebook\terraform"
Copy-Item dev.tfvars.example dev.tfvars
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -refresh=false -var="enable_infrastructure=false"
```

The last command is a safe empty plan. To inspect the proposed foundation without AWS credentials, use the same offline-only mode as CI:

```powershell
terraform plan -refresh=false -var="enable_infrastructure=true" -var="offline_plan_validation=true" -out=phase8-plan.tfplan
terraform show -no-color phase8-plan.tfplan
```

The generated plan is for review only. It must not be applied: placeholder credentials are deliberately not valid for AWS.

## Network boundaries

- Public subnets are reserved for a future internet-facing ALB; no public IP is auto-assigned to subnet workloads.
- Private subnets have only the VPC-local route. No workloads can be deployed there with outbound registry/dependency access until a separate egress design is approved.
- Application ports 8000 and 8080 accept traffic only from the ALB security group.
- PostgreSQL port 5432 and RabbitMQ AMQP port 5672 accept traffic only from the application security group. RabbitMQ management port 15672 is not opened in the planned SG.
- The ALB security group allows HTTP/HTTPS ingress; a future ALB should redirect HTTP to HTTPS and use ACM-managed TLS. Security groups alone do not create or expose an ALB.
- Subnets/AZs are sample defaults for `ap-south-1`; confirm the chosen account and region before a real plan.

## GitHub Actions and IAM

The optional IAM role is disabled until `github_oidc_provider_arn` is set to the existing provider for `token.actions.githubusercontent.com`. Its trust restricts the subject to `repo:Akash642-eng/cinebook:ref:refs/heads/main` and audience to `sts.amazonaws.com`; its policy only authorizes image pushes to the two CineBook ECR repositories plus ECR login-token retrieval. It is **not** an infrastructure-provisioning role and is not yet wired into the current GHCR deployment workflow.

For real AWS automation, create/verify the GitHub OIDC provider in IAM, define a separate narrowly scoped Terraform plan/apply role, store role ARNs as GitHub configuration variables, and use `aws-actions/configure-aws-credentials` with `id-token: write`. Do not store long-lived AWS access keys in GitHub secrets. Set up versioned remote Terraform state and locking before allowing shared or production applies.

## Cost gate

The CI renders an architecture plan only; nothing is created. The foundation omits the commonly significant recurring services (NAT Gateway, ALB, container compute, managed database and message broker). ECR charges for stored image data, and internet data transfer can be billed when used; do not push images or create traffic until costs are accepted. Use the [AWS Pricing Calculator](https://calculator.aws/) for the exact region, hours, storage and expected traffic.

Do not interpret the default empty plan as proof of zero spend in an existing AWS account. Inventory that account's Billing, EC2, VPC, RDS, ECS/EKS, Elastic Load Balancing, NAT Gateway, ECR, CloudWatch, and public IPv4 resources before claiming no paid resources are running.

## State and teardown

No remote backend is configured or bootstrapped. State is local by default and is ignored by Git. Never commit `terraform.tfstate`, plan files, credentials, or `dev.tfvars`.

Before any future apply: configure protected/versioned remote state and locking, authenticate via reviewed OIDC, run a real account-aware `terraform plan`, inspect every create/update/destroy, review costs, and obtain explicit approval.

For a deployment that has actually been applied and whose correct state backend is configured, the controlled teardown sequence is:

```powershell
terraform plan -destroy -out=destroy.tfplan
terraform show -no-color destroy.tfplan
# Only after reviewing every deletion and receiving approval:
terraform apply destroy.tfplan
```

That teardown was **not tested**, because this project has not applied AWS resources. Never run destroy against an empty/local state while real resources exist outside that state, and never delete CineBook's Minikube PVCs as part of AWS teardown.
