# CineBook Phase 7 — Kubernetes Deployment & Hardening

**Status: COMPLETE — validation run [#40198960374](https://github.com/Akash642-eng/cinebook/actions/runs/40198960374) passed on 2026-10-25.**

## Live baseline and final validation

The read-only Minikube audit and Phase 7 hardening workflow confirmed:

| Requirement | Result |
|---|---|
| Backend/frontend Deployments and same immutable Git-SHA tag | **PASS** — both initially deployed as `c70ebd7e524bfdfb6eb1263fb516e89fc43cd18f`; exact image pair restored after rollback test |
| Backend/frontend/PostgreSQL/RabbitMQ rollouts | **PASS** — all four rollouts succeeded |
| Backend Service discovery and API health | **PASS** — backend EndpointSlice existed; `/api/health` returned healthy through Ingress routing |
| PostgreSQL/RabbitMQ persistent claims | **PASS** — `cinebook-postgres-pvc` Bound (2Gi) and `cinebook-rabbitmq-pvc` Bound (1Gi), both ReadWriteOnce, `standard` class |
| Helm chart from clean checkout | **PASS** — `helm lint` and `helm template` succeeded with existing-claim defaults and with `persistence.createClaims=true` |
| Startup/readiness/liveness probes | **PASS** — all live containers have all three; the missing frontend startup probe was added and the frontend rollout succeeded |
| CPU/memory requests and limits | **PASS** — required requests and limits exist for all four live workloads; the full rollout completed. No separate load/stress benchmark was performed |
| Secret handling | **PASS** — required `cinebook-secrets` keys were present; chart render creates no Secret object or credential literals; values were not printed |
| Ingress/stable route | **PASS** — NGINX Ingress for host `cinebook.local` was applied; `/api/health` passed through the controller using a local port-forward and matching Host header. Direct browser access through a Windows hosts-file entry was not separately tested |
| PostgreSQL backup/restore | **PASS** — `pg_dump` restored into a temporary `phase7r*` database; table-by-table row-count fingerprints matched, and the temporary database was dropped |
| PostgreSQL restart/persistence | **PASS** — pod restarted, `pg_isready` passed, and source database table row-count fingerprints were unchanged |
| RabbitMQ restart/persistence | **PASS** — durable queue and persistent marker were read before restart; after pod restart the queue and marker payload remained; test queue was removed |
| Previous-image rollback | **PASS** — both apps rolled back to known-good SHA `746df1897d553ef170d180d7f676ef033da9b2e0`; Ingress health passed; exact original `c70ebd7e524bfdfb6eb1263fb516e89fc43cd18f` image pair was restored and health passed again |

## Evidence

- [Phase 7 Helm and live hardening run #40198960374](https://github.com/Akash642-eng/cinebook/actions/runs/40198960374) — **success**
- [Read-only Kubernetes audit run #40197360606](https://github.com/Akash642-eng/cinebook/actions/runs/40197360606) — **success**
- [Phase 6 release evidence](../releases/2026-10-25-phase6-release-evidence.md)

The live validation run logs show the PostgreSQL restore and restart checks, RabbitMQ message recovery, previous-release health check, and restoration of the original application image pair all passed.

## Safety boundaries retained

- Never delete `cinebook-postgres-pvc`, `cinebook-rabbitmq-pvc`, or their PVs as a recovery shortcut.
- The PostgreSQL dump was kept in temporary runner storage, not printed, and removed during cleanup.
- The restore validation created and dropped only a unique temporary database named with the `phase7r` prefix; it did not overwrite the live `cinebook` database.
- RabbitMQ validation used a uniquely named durable test queue and removed it after verification.
- The rollback check temporarily changed only the backend/frontend image references; it restored the exact original pair. PostgreSQL/RabbitMQ storage was not deleted or replaced.
- The chart is linted/rendered but intentionally not installed over existing live resources because those resources do not have Helm release ownership metadata. A Helm adoption/migration needs a separately reviewed change.

## Reusable configuration

- [Phase 7 read-only audit workflow](../../.github/workflows/phase7-audit.yml)
- [Phase 7 hardening workflow](../../.github/workflows/phase7-validation.yml)
- [CineBook Helm chart README](../../helm/cinebook/README.md)

**Operational note:** this phase validates a single-node Minikube setup. It is not a multi-node high-availability or production disaster-recovery drill; backup retention/off-cluster storage, resource-load testing and direct Windows browser hostname validation remain separate production-readiness improvements.
