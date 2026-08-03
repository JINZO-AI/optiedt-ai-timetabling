<#
.SYNOPSIS
    Run every check CI runs, in the order that fails fastest.

.DESCRIPTION
    Layer boundaries come first. They encode the system's central invariants
    (SRS 2.1, 7.5), and a violation there is a design error rather than a style
    problem - there is no point running tests against a build that has already
    broken the architecture.
#>

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$failed = New-Object System.Collections.Generic.List[string]

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command,
        [int[]]$AllowExit = @(0)
    )
    Write-Host "[..] $Name" -ForegroundColor Cyan
    & $Command 2>&1 | Out-Host
    # Native executables do not throw on failure, so check the exit code
    # explicitly rather than relying on try/catch.
    if ($AllowExit -contains $LASTEXITCODE) {
        Write-Host "[ok] $Name" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Name (exit $LASTEXITCODE)" -ForegroundColor Red
        $failed.Add($Name)
    }
}

Push-Location (Join-Path $root 'backend')
try {
    Invoke-Step 'layer boundaries' { uv run lint-imports }
    Invoke-Step 'ruff'             { uv run ruff check . }
    Invoke-Step 'format'           { uv run ruff format --check . }
    Invoke-Step 'types'            { uv run mypy }
    # Solver-marked tests are excluded here: they invoke CP-SAT against the
    # real reference instance and can legitimately take minutes (see C-13,
    # docs/open-questions.md) - a check meant to fail fast must not wait on
    # one. Run them explicitly with `uv run pytest -m solver` when needed.
    #
    # Exit 5 (pytest collected nothing) is NOT tolerated. It was, while the
    # scaffold had no tests; allowing it now would let a broken collection -
    # an import error in conftest, a renamed directory - pass as success.
    Invoke-Step 'tests'            { uv run pytest -m "not solver" }
} finally { Pop-Location }

Invoke-Step 'instance' { & (Join-Path $root 'scripts\verify-instance.ps1') }

Push-Location (Join-Path $root 'frontend')
try {
    if (Test-Path 'node_modules') {
        Invoke-Step 'frontend types' { npm run typecheck }
        # The display-layer tests. `tsc` cannot cover what these check: the
        # acceptance criterion says the *displayed* contributions sum to the
        # *displayed* score difference, and rounding happens in the component.
        Invoke-Step 'frontend tests' { npm run test }
    } else {
        Write-Host "[skip] frontend - run scripts/bootstrap.ps1 first" -ForegroundColor Yellow
    }
} finally { Pop-Location }

Write-Host ""
if ($failed.Count -gt 0) {
    Write-Host "Failed: $($failed -join ', ')" -ForegroundColor Red
    if ($failed -contains 'layer boundaries') {
        Write-Host ""
        Write-Host "A layer boundary was violated. Do not relax .importlinter to make" -ForegroundColor Yellow
        Write-Host "this pass - those contracts are the system's invariants. See CLAUDE.md." -ForegroundColor Yellow
    }
    if ($failed -contains 'instance') {
        Write-Host ""
        Write-Host "The instance no longer matches its documentation. Either the data" -ForegroundColor Yellow
        Write-Host "changed or the documents are now false - fix both." -ForegroundColor Yellow
    }
    exit 1
}
Write-Host "All checks passed." -ForegroundColor Green
