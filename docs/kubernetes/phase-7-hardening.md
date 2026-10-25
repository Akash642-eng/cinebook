# CineBook Phase 7 — Kubernetes Deployment & Hardening

## Live baseline observed

The read-only Minikube audit confirmed:

- Backend and frontend: each 1/1 Ready and sharing the same Git-SHA image tag.
- PostgreSQL and RabbitMQ: each 1/1 Ready and each mounts its existing PVC.
- PostgreSQL PVC: `Bound`, 2Gi, `ReadWriteOnce`, storage class `standard`.
- RabbitMQ PVC: `Bound`, 1Gi, `ReadWriteOnce`, storage class `standard`.
- Backend, PostgreSQL and RabbitMQ had startup/readiness/liveness probes and CPU/memory requests/limits.
- Frontend had readiness/liveness probes and resource requests/limits but no startup probe.
- The app containers reference `cinebook-secrets`; secret values were never printed.
- No Ingress resource or tracked Kubernetes/Helm definitions existed at audit time.

The Phase 7 validation workflow tracks a Helm chart, adds the frontend startup probe, lints/renders the chart, configures NGINX Ingress, checks the health route, tests PostgreSQL backup/restore in a temporary database, verifies PostgreSQL row-count fingerprints across a pod restart, verifies a durable RabbitMQ marker message survives a pod restart, and tests an actual app-image rollback to a prior known-good SHA followed by restoration of the originally active images.

## Safety boundaries

- Never delete `cinebook-postgres-pvc`, `cinebook-rabbitmq-pvc`, or their PVs as a recovery shortcut.
- PostgreSQL backup files are temporary runner files; contents are not printed and the file is removed in `finally`.
- Restore testing uses a temporary database whose name begins with `phase7r`, compares table-by-table row counts, and drops only that temporary database.
- RabbitMQ persistence is tested with a uniquely named durable queue and persistent marker message, then the queue is removed.
- The live image rollback test may cause a short application interruption, but it restores the exact original backend/frontend image pair and does not alter database or RabbitMQ volumes.
- The chart is linted/rendered but intentionally not installed over existing live resources, since those resources do not have Helm release ownership metadata.

See [Phase 7 Audit](../../.github/workflows/phase7-audit.yml), [Phase 7 Validation](../../.github/workflows/phase7-validation.yml), and [the Helm chart README](../../helm/cinebook/README.md). Add the successful validation run link after the first clean run.
