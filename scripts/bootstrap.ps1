<#
.SYNOPSIS
    Prepare a development environment for OptiEDT.

.DESCRIPTION
    Installs backend and frontend dependencies, creates .env from the example,
    and starts PostgreSQL. Safe to re-run.
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host "OptiEDT — bootstrap" -ForegroundColor Cyan
Write-Host ""

# ── Prerequisites ───────────────────────────────────────────────────
$missing = @()
foreach ($tool in 'uv', 'node', 'docker') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { $missing += $tool }
}
if ($missing.Count -gt 0) {
    Write-Host "Missing: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "  uv     https://docs.astral.sh/uv/getting-started/installation/"
    Write-Host "  node   https://nodejs.org  (20+)"
    Write-Host "  docker https://docs.docker.com/get-docker/"
    exit 1
}

# ── Environment file ────────────────────────────────────────────────
$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $root '.env.example') $envFile
    Write-Host "[ok] created .env — set OPTIEDT_SECRET_KEY before any real use" -ForegroundColor Yellow
} else {
    Write-Host "[skip] .env already exists"
}

# ── Backend ─────────────────────────────────────────────────────────
Write-Host "[..] backend dependencies"
Push-Location (Join-Path $root 'backend')
try { uv sync --all-extras } finally { Pop-Location }
Write-Host "[ok] backend" -ForegroundColor Green

# ── Frontend ────────────────────────────────────────────────────────
Write-Host "[..] frontend dependencies"
Push-Location (Join-Path $root 'frontend')
try { npm install } finally { Pop-Location }
Write-Host "[ok] frontend" -ForegroundColor Green

# ── Database ────────────────────────────────────────────────────────
# ⚠️ `docker compose up -d` SUCCEEDS when another PostgreSQL already owns the
# host port: the container starts, reports healthy, and every connection from
# the host still reaches the other server. So the port is checked BEFORE
# starting, and the check names the fix rather than leaving a silent
# misconnection to be discovered by a migration.
Write-Host "[..] postgres"
$hostPort = if ($env:OPTIEDT_POSTGRES_PORT) { [int]$env:OPTIEDT_POSTGRES_PORT } else { 5432 }
$occupied = @(Get-NetTCPConnection -State Listen -LocalPort $hostPort -ErrorAction SilentlyContinue)
if ($occupied -and -not (docker ps --filter 'name=optiedt-postgres' --format '{{.Names}}')) {
    Write-Host "[!!] port $hostPort is already in use by another process." -ForegroundColor Yellow
    Write-Host "     Compose would start anyway and host connections would reach THAT server." -ForegroundColor Yellow
    Write-Host "     Set OPTIEDT_POSTGRES_PORT in .env, and OPTIEDT_DATABASE_URL in backend/.env." -ForegroundColor Yellow
}
Push-Location $root
try { docker compose up -d postgres } finally { Pop-Location }
Write-Host "[ok] postgres (container is PostgreSQL 17 - verify with:" -ForegroundColor Green
Write-Host "     docker exec optiedt-postgres psql -U optiedt -d optiedt -tAc ""select version();"")" -ForegroundColor Green

Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  cd backend  ; uv run alembic upgrade head"
Write-Host "  cd backend  ; uv run uvicorn optiedt.api.main:app --reload"
Write-Host "  cd frontend ; npm run dev"
Write-Host ""
Write-Host "Before changing anything structural, read CLAUDE.md and docs/status.md."
