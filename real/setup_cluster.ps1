# Jalankan di PowerShell (Docker Desktop harus sudah running). Dari root repo.
$ErrorActionPreference = "Stop"
docker info *> $null; if ($LASTEXITCODE -ne 0) { throw "Docker belum jalan. Buka Docker Desktop dulu." }
docker pull python:3.11-slim
if (-not (kind get clusters | Select-String -Pattern '^soka$')) {
    kind create cluster --config real/kind-config.yaml
}
kind load docker-image python:3.11-slim --name soka
kubectl label node soka-worker  soka-host=host-1 --overwrite
kubectl label node soka-worker2 soka-host=host-2 --overwrite
kubectl get nodes -o wide
