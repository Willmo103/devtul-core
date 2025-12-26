# Stop on first error
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   DEVTUL CORE - DOCKER RELAUNCHER" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check if container exists and stop it
$ContainerName = "devtul-core-docs-1"
if (docker ps -a -q -f name=$ContainerName) {
    Write-Host "Stopping and removing existing container..." -ForegroundColor Yellow
    docker compose down
} else {
    Write-Host "No running container found." -ForegroundColor Green
}

# 2. Rebuild cleanly
Write-Host "`nBuilding Docker image (no-cache recommended for fresh builds)..." -ForegroundColor Yellow
docker compose build --no-cache

# 3. Launch
Write-Host "`nLaunching stack..." -ForegroundColor Green
docker compose up -d

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8080"
Write-Host "==========================================" -ForegroundColor Cyan
