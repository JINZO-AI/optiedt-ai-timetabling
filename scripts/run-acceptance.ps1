<#
.SYNOPSIS
    Run the acceptance suite - one test per requirement, against its criterion.

.DESCRIPTION
    NOT part of run-checks.ps1, and for the same reason the solver-marked tests
    are not: the criteria about the ENGINE need real solves at production
    settings, and a portfolio takes 147-150 s (docs/status.md). A check meant
    to fail fast must not wait on one.

    The fast half - criteria about the APPLICATION rather than the engine -
    DOES run in run-checks.ps1, because those need no solver at all.

    Run this before claiming a requirement is met, and before a demonstration.

.PARAMETER FastOnly
    Skip the solver-marked tests. Same subset run-checks.ps1 covers; useful for
    a quick check that the suite still collects and passes.
#>

param(
    [switch]$FastOnly
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $root 'backend')
try {
    if ($FastOnly) {
        Write-Host "[..] acceptance, fast half only (no solver)" -ForegroundColor Cyan
        uv run pytest -m "acceptance and not solver" -v
    } else {
        Write-Host "[..] acceptance, all of it - the solver-marked tests take" -ForegroundColor Cyan
        Write-Host "     several minutes each and that is expected, not a hang." -ForegroundColor Cyan
        Write-Host "     A portfolio at production settings is measured at 147-150 s." -ForegroundColor DarkGray
        uv run pytest -m acceptance -v
    }
    $code = $LASTEXITCODE
} finally { Pop-Location }

Write-Host ""
if ($code -ne 0) {
    Write-Host "Acceptance FAILED (exit $code)." -ForegroundColor Red
    Write-Host "A failure here is a requirement not met, not a flaky test:" -ForegroundColor Yellow
    Write-Host "every solver-marked test fixes a seed AND a deterministic budget," -ForegroundColor Yellow
    Write-Host "so it cannot vary with the machine (ADR-011)." -ForegroundColor Yellow
    exit 1
}
Write-Host "Acceptance passed." -ForegroundColor Green
