# CineBook Helm chart

This chart defines the CineBook backend, frontend, PostgreSQL, RabbitMQ, their ClusterIP Services, optional PVCs, and an NGINX Ingress.

## Secret prerequisites

The namespace must contain an externally managed Kubernetes Secret named `cinebook-secrets` with keys `POSTGRES_PASSWORD`, `JWT_SECRET`, and `RABBITMQ_PASSWORD`. No credential values belong in this chart, values files, committed manifests, or rendered output. The chart uses `secretKeyRef` only.

## Render and lint

```powershell
helm lint .\helm\cinebook
helm template cinebook .\helm\cinebook --namespace cinebook
helm template cinebook .\helm\cinebook --namespace cinebook --set persistence.createClaims=true
```

## Existing cluster safety

The current Minikube namespace already has deployments and bound claims. The default `persistence.createClaims=false` is deliberate, and the chart points at `cinebook-postgres-pvc` and `cinebook-rabbitmq-pvc`. **Do not run `helm install` or `helm upgrade` against the live namespace yet.** Existing resources were not created with Helm ownership metadata; a safe adoption/migration needs its own reviewed change. Phase 7 validation renders/lints this chart but does not replace live workloads with Helm.

For a brand-new namespace, set `persistence.createClaims=true` and provision `cinebook-secrets` separately before install.

## Local Ingress

The chart renders an Ingress for host `cinebook.local` and class `nginx`. Minikube's ingress addon must be enabled and ready. Map the current `minikube ip` to `cinebook.local` in the Windows hosts file to browse the domain directly; CI tests the Ingress rule with the matching Host header. The frontend NGINX proxies `/api/` to the in-cluster `cinebook-backend` Service.
