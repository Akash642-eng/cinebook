# CineBook Phase 6 Release Evidence

## Release identity

- Release commit: `c70ebd7e524bfdfb6eb1263fb516e89fc43cd18f`
- Commit message: `fix: update frontend NGINX base image`
- Release date: 2026-10-25
- CI run: [CineBook CI #9](https://github.com/Akash642-eng/cinebook/actions/runs/40186161986) — **success**
- Deployment run: [Deploy CineBook to Minikube #7](https://github.com/Akash642-eng/cinebook/actions/runs/40186647971) — **success**

## Published container images

Both images were built and pushed by the successful CI run, tagged with the full commit SHA and `latest`.

| Image | Commit-SHA tag | Registry digest |
|---|---|---|
| Backend | `ghcr.io/akash642-eng/cinebook-backend:c70ebd7e524bfdfb6eb1263fb516e89fc43cd18f` | `sha256:7d438b43a045f89ca131ed1cd494beb25f6b9f6beea44da2f9d2567bb2e667cc` |
| Frontend | `ghcr.io/akash642-eng/cinebook-frontend:c70ebd7e524bfdfb6eb1263fb516e89fc43cd18f` | `sha256:aaa064e84b0ef642e8eb73a64fc6d2950274da392bc4d8fb12b9c975b22c8f3e` |

Digest source: successful GHCR publishing job logs in [CI run #9](https://github.com/Akash642-eng/cinebook/actions/runs/40186161986). Deployments should use commit-SHA tags, not `latest`. For stricter immutability, use the recorded digest in the Kubernetes image reference when the deployment workflow is upgraded to accept digest references.

## Verification

- Backend unit/integration test job: passed.
- Frontend lint/build job: passed.
- Docker image build job: passed.
- Trivy backend image scan: passed configured gate.
- Trivy frontend image scan: passed configured gate after updating the NGINX base image.
- GHCR backend and frontend publication: passed.
- Minikube deployment of the release commit: passed both backend and frontend rollout status checks. The deployment job also queried pods and the backend Endpoint resource.
- Failed-CI release gate: verified. [CI run #8](https://github.com/Akash642-eng/cinebook/actions/runs/40184954510) failed in the image-build/security job and the GHCR publish job was skipped.

Trivy gate configuration: scan OS and library vulnerabilities at HIGH/CRITICAL severity; `ignore-unfixed: true`; nonzero findings at the configured gate fail the build.

## Rollback test evidence

The isolated rollback-recovery test creates a unique temporary namespace, starts a healthy frontend probe deployment, switches only that probe to the backend image to force an unhealthy rollout, restores the original frontend image, verifies one available replica, and deletes the temporary namespace. It does not modify the live `cinebook` namespace or persistent data.

- Rollback test run: [CineBook Rollback Recovery Test](https://github.com/Akash642-eng/cinebook/actions/runs/40187774563) — **success**
- Observed sequence: healthy baseline confirmed; backend-image rollout timed out as expected; original frontend image restored; one available replica verified; temporary namespace cleaned up.
- Outcome: **PASS** for the isolated image-restoration/rollback procedure. This simulates the failed-rollout recovery action without deliberately changing the live application's images.

## Scope and limitations

This record captures the CI/CD pipeline and deployment verification observed for the commit above. It is not a claim that the live application has undergone a deliberate failed production rollout; the failure-path test is isolated in a temporary namespace to avoid risking user data or service availability.
