# CineBook Phase 8 — Terraform & AWS Infrastructure

**Status: PARTIAL / PLAN-ONLY.** Terraform source, safe defaults, architecture boundaries and automated formatting/validation/plan review are prepared. No AWS resource has been applied by this project.

## Verification status

| Requirement | Status | Evidence / boundary |
|---|---|---|
| Terraform project structure committed | ✅ | `terraform/` root plus `modules/foundation/` |
| AWS provider and variables configured safely | ✅ | AWS provider pinned to `~> 6.0`; region and network variables; infrastructure disabled by default; no credential literals |
| Terraform formatting and validation pass | ✅ | [Terraform CI run #40204539102](https://github.com/Akash642-eng/cinebook/actions/runs/40204539102) passed `terraform fmt -diff -check -recursive`, `terraform init -backend=false`, and `terraform validate` |
| Terraform plan inspected before applying | ✅ (offline plan only) | [Run #40204539102](https://github.com/Akash642-eng/cinebook/actions/runs/40204539102) uploaded artifact `cinebook-phase8-terraform-plan`: **20 to add, 0 to change, 0 to destroy**. This is a simulated offline plan, not an account-aware cost/drift plan |
| Networking/security boundaries documented | ✅ | Public ingress subnets, isolated private subnets, ALB/app/PostgreSQL/RabbitMQ security groups |
| Deployment resources match intended architecture | ✅ (foundation only) | VPC, subnets, route tables, security groups, ECR; no application compute or managed data services yet |
| IAM roles follow least privilege | ✅ (optional ECR role) | Role is disabled until the existing GitHub OIDC provider ARN is supplied; it is scoped to main branch and two ECR repositories |
| GitHub Actions AWS auth uses OIDC | 🟡 | Trust policy template documented, but no real AWS OIDC provider/role has been configured or exercised; current deploy workflow still targets Minikube/GHCR |
| AWS deployment path tested, if in scope | 🟡 Out of scope for free-only phase | No AWS account or budget was connected; only offline Terraform CI is tested. No `apply`, paid service, or AWS deployment was run |
| Cost estimate and billing risks reviewed | ✅ Design review | Common recurring resources (NAT, ALB, ECS/EKS, RDS, Amazon MQ) intentionally omitted from foundation. Use AWS Pricing Calculator before expanding |
| Teardown instructions tested/safely verified | 🟡 Documented, not executed | No applied AWS resources exist in Terraform state, so destruction is not testable without an actual approved deployment |
| No unnecessary paid AWS resources left running | ⚠️ Not verifiable from this repo | This workflow created none, but the user's AWS account inventory has not been checked; don't claim the account is empty |

## Architecture and controls

The initial plan is a minimal foundation, not a running service:
- One VPC with two public and two private subnets in two AZs.
- Public subnets are reserved for a future ALB; no public IP auto-assignment on subnet workloads.
- Private subnets intentionally have no NAT/default Internet route. A separately reviewed egress design is needed before private workloads can pull images or reach dependencies.
- App SG accepts TCP 8000/8080 only from the ALB SG; PostgreSQL 5432 and RabbitMQ AMQP 5672 only from the app SG; RabbitMQ management 15672 is not opened.
- Private ECR repositories for immutable backend/frontend image tags.
- An optional GitHub OIDC ECR publisher role with a trust condition restricted to the exact repository's `main` branch and `sts.amazonaws.com` audience. This role only pushes ECR images; it cannot provision infrastructure.

## Cost decision

The Terraform CI uses `enable_infrastructure=true` only to display the proposed base-resource graph in a dummy-credential offline plan. The configuration itself defaults to `enable_infrastructure=false`. CI uses no AWS credentials and never executes `terraform apply`.

The foundation has no NAT Gateway, ALB, ECS/EKS workloads, RDS instance or Amazon MQ broker. Those resources can generate ongoing charges, and are deliberately deferred. Empty ECR repositories have no image-storage volume, but ECR storage and data transfer can be charged when used. Review [AWS Fargate pricing](https://aws.amazon.com/fargate/pricing/) and the [AWS Pricing Calculator](https://calculator.aws/) before any compute/database/broker decisions.

No existing AWS account was provided for inventory, so the checklist item about pre-existing paid resources remains **unverified**. The project didn't create any.

## Commands for local review

```powershell
Set-Location "$HOME\Projects\cinebook\terraform"
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -refresh=false -var="enable_infrastructure=false"
```

The offline populated plan is for review only and cannot be applied because it uses dummy credentials:
`terraform plan -refresh=false -var="enable_infrastructure=true" -var="offline_plan_validation=true" -out=phase8-plan.tfplan`

## Gate before a real AWS apply

1. Confirm AWS account, region and a monthly cost limit.
2. Review the complete resource plan and a region-specific Pricing Calculator estimate.
3. Configure protected/versioned remote state and locking in a separately reviewed bootstrap step.
4. Configure the GitHub OIDC provider and a dedicated least-privilege plan/deploy role. Keep the infrastructure-creation role separate from the ECR publisher role.
5. Run a real authenticated `terraform plan` with the real state backend; inspect every create/update/destroy and get explicit approval.
6. Only then apply. Test teardown against that same real state after documenting the resources to be deleted.

The offline CI artifact is not a substitute for a real account-aware plan and must never be applied.
