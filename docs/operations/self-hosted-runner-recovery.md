# CineBook Self-Hosted Runner Recovery (Windows + Minikube)

Last verified: 2026-10-25, during successful deployment run [#7](https://github.com/Akash642-eng/cinebook/actions/runs/40186647971).  
Runner labels required by `.github/workflows/deploy.yml`: `self-hosted`, `Windows`, `X64`.

## What the runner needs

- The Windows runner service is online in repository Settings → Actions → Runners.
- Docker is running and can inspect the published GHCR images.
- Minikube is running and the current kubectl context is exactly `minikube`.
- The runner account has access to the intended Minikube kubeconfig.
- The GitHub Actions runner installation and its `_diag` logs remain accessible to the runner administrator.

## Recovery steps

### 1. Check runner availability

In GitHub, open **Akash642-eng/cinebook → Settings → Actions → Runners**. Confirm the Windows x64 runner is online and not busy with a stuck job. Review the most recent failed job and its log before restarting anything.

### 2. Check the Windows runner service

Run PowerShell on the Windows machine that hosts the runner:

```powershell
$runnerServices = Get-CimInstance Win32_Service | Where-Object {
    $_.Name -like "actions.runner*" -or
    $_.DisplayName -like "*GitHub Actions Runner*"
}

$runnerServices | Select-Object Name, State, StartName, PathName
```

If a runner service is found but is stopped or unresponsive, restart the exact service shown above in an elevated PowerShell session:

```powershell
$runner = Get-Service | Where-Object {
    $_.Name -like "actions.runner*" -or
    $_.DisplayName -like "*GitHub Actions Runner*"
} | Select-Object -First 1

if (-not $runner) { throw "No installed GitHub Actions runner service found." }

Restart-Service -Name $runner.Name
Get-Service -Name $runner.Name
```

If the service is absent, do not guess the installation path or blindly reinstall. Locate the existing runner directory and inspect its `_diag` folder first.

### 3. Validate Docker and Minikube

Run these commands under the same Windows account/context used by the runner:

```powershell
docker version
minikube status
kubectl config current-context
kubectl get nodes -o wide
kubectl get deployments -n cinebook
```

The deployment workflow must report current context `minikube`. If Docker or Minikube is stopped, restore it through the normal local service/startup procedure and re-run the checks. Do not delete the cluster, namespaces, PVCs, or persistent volumes as a runner-recovery shortcut.

### 4. Inspect runner diagnostics

In the runner installation directory, open the most recent files under `_diag`, especially `Runner_*.log` and `Worker_*.log`. Check for service startup errors, network connectivity, job pickup failures, and command-path differences between interactive PowerShell and the service account.

Never paste registration tokens, access tokens, kubeconfig contents, or secret values into an issue or chat.

### 5. Resume deployment safely

1. Confirm CI passed and the full 40-character commit SHA has published backend and frontend images to GHCR.
2. In **Actions → Deploy CineBook to Minikube → Run workflow**, enter the full lowercase commit SHA; do not use `latest`.
3. Verify the deployment job reports both backend and frontend rollouts succeeded.
4. If rollout fails, inspect the rollback output and verify the previous images are restored before attempting another deploy.

## Escalation / re-registration

Only reconfigure or remove/re-register the runner if normal service restart and diagnostics show the runner registration is broken. Obtain a fresh registration token from repository settings when re-registering; never store that token in source control. Keep the runner restricted to this trusted repository and trusted contributors because its kubeconfig grants access to the local cluster.
