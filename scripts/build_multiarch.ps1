# Build multi-platform images (amd64 + arm64) for Oracle Cloud Ampere.
# Requires Docker Desktop buildx. Does NOT push unless -Push is set.
param(
  [string]$Registry = "",
  [switch]$Push
)

$ErrorActionPreference = "Stop"
Set-Location "D:\CyberSecurity_FYP"

docker buildx inspect sentinel-multi 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  docker buildx create --name sentinel-multi --use | Out-Null
} else {
  docker buildx use sentinel-multi
}

$backendTag = if ($Registry) { "$Registry/sentinel-x-backend:latest" } else { "sentinel-x-backend:multi" }
$frontendTag = if ($Registry) { "$Registry/sentinel-x-frontend:latest" } else { "sentinel-x-frontend:multi" }

$pushFlag = if ($Push -and $Registry) { "--push" } else { "--load" }
# --load only works for single platform; for multi-arch without registry use --push or bake separately.
if (-not $Push) {
  Write-Host "Building linux/amd64 only for local load (multi-arch requires registry push)."
  docker buildx build --platform linux/amd64 -f Dockerfile.backend -t sentinel-x-backend:local --load .
  docker buildx build --platform linux/amd64 -f Dockerfile.frontend -t sentinel-x-frontend:local --load .
  Write-Host "To build amd64+arm64 and push: .\scripts\build_multiarch.ps1 -Registry YOUR_REG -Push"
  exit 0
}

docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.backend -t $backendTag --push .
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.frontend -t $frontendTag --push .
Write-Host "Pushed $backendTag and $frontendTag"
