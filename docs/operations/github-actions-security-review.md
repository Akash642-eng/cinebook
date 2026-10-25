# GitHub Actions Permissions and Secrets Review

Review date: 2026-10-25  
Repository: `Akash642-eng/cinebook`

## Workflow-level review

### `.github/workflows/ci.yml`

- Workflow default permission is `contents: read`.
- Backend tests and frontend lint/build do not require write permissions.
- Image-building and Trivy scanning run before publication.
- Only the `publish-images` job grants `packages: write`; it also has `contents: read`.
- GHCR publication authenticates with the job-scoped `secrets.GITHUB_TOKEN`; no personal access token is embedded in the workflow.
- Backend test credentials in workflow YAML are explicitly CI-only dummy values and must never be reused outside tests.
- Publication is dependent on backend tests, frontend checks, Docker builds, and both Trivy scan steps succeeding.

### `.github/workflows/deploy.yml`

- Workflow permission is `contents: read`; the deployment job does not grant package-write permissions.
- Deployment is manual (`workflow_dispatch`) and requires a full 40-character lowercase commit SHA.
- It checks that both matching GHCR images exist before changing Kubernetes deployments.
- The job uses the `production` environment and serializes production deployments with a concurrency group.
- It checks the Kubernetes context is `minikube`, records the previous image references, checks both rollout statuses, and attempts to restore previous image references on failure.
- No explicit `secrets.*` values or long-lived GHCR token are referenced in the workflow. Kubernetes access is supplied by the self-hosted runner's local Minikube/kubeconfig context, so host access is security-sensitive.

## Findings and decisions

| Area | Review result |
|---|---|
| Default token permissions | Least-privilege defaults are read-only |
| GHCR write permission | Scoped to the single publish job |
| CI test credentials | Dummy/test-only values; not production secrets |
| Deployment trigger | Manual only; full SHA validation present |
| Self-hosted runner | Trusted deployment boundary; restrict Windows host and runner administration |
| Image tags | Commit-SHA tags used for deployment; digest evidence is recorded separately |
| Third-party actions | Several actions use version tags rather than immutable full commit SHAs; pinning them to reviewed full SHAs is a recommended supply-chain hardening improvement |
| Production environment approvals | Workflow references the `production` environment, but its required-reviewer and deployment-branch rules are repository settings rather than YAML. Verify these settings in GitHub Settings → Environments → production; do not assume approvals are enabled merely because the environment is named |

## Operational controls to keep

1. Keep workflow default permissions read-only and grant write permissions only to the job that needs them.
2. Never print token values, kubeconfig contents, application secrets, or `.env` values in Actions logs.
3. Do not add GHCR credentials to deployment when the published packages are public; if package visibility changes, prefer a short-lived, narrowly scoped credential stored as an environment secret rather than a developer PAT.
4. Restrict who can modify `main`, run the production deployment workflow, administer the self-hosted runner, and access the Minikube host.
5. Review action version pins and production environment protection rules when changing the pipeline.

## Verification basis

This review is based on the checked-in workflow YAML and successful CI/deployment run records. It does not claim access to inspect secret values (which must remain private) or to confirm environment approval settings unless separately verified in GitHub repository settings.
