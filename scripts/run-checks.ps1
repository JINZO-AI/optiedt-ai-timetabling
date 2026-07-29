<#
.SYNOPSIS
    Run every check CI runs, in the order that fails fastest.

.DESCRIPTION
    Layer boundaries come first. They encode the system's central invariants
    (SRS §2.1, §7.5), and a violation there is a design error rather than a
    style problem — there is no point running tests against a build that has
    already broken the architecture.
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$failed = @()

function Invoke-Step($name, $script) {
    Write-Host "[..] $name" -ForegroundColor Cyan
    try { & $script; Write-Host "[ok] $name" -ForegroundColor Green }
    catch { Write-Host "[FAIL] $name" -ForegroundColor Red; $script:failed += $name }
}

Push-Location (Join-Path $root 'backend')
try {
    Invoke-Step 'layer boundaries' { uv run lint-imports }
    Invoke-Step 'ruff'             { uv run ruff check . }
    Invoke-Step 'format'           { uv run ruff format --check . }
    Invoke-Step 'types'            { uv run mypy }
    Invoke-Step 'tests'            { uv run pytest }
} finally { Pop-Location }

Push-Location (Join-Path $root 'frontend')
try {
    if (Test-Path 'node_modules') {
        Invoke-Step 'frontend types' { npm run typecheck }
    } else {
        Write-Host "[skip] frontend — run scripts/bootstrap.ps1 first" -ForegroundColor Yellow
    }
} finally { Pop-Location }

Write-Host ""
if ($failed.Count -gt 0) {
    Write-Host "Failed: $($failed -join ', ')" -ForegroundColor Red
    if ($failed -contains 'layer boundaries') {
        Write-Host ""
        Write-Host "A layer boundary was violated. Do not relax .importlinter to make" -ForegroundColor Yellow
        Write-Host "this pass — those contracts are the system's invariants. See CLAUDE.md." -ForegroundColor Yellow
    }
    exit 1
}
Write-Host "All checks passed." -ForegroundColor Green
