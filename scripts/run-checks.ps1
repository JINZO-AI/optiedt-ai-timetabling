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
    Invoke-Step 'tests'            { uv run pytest -m "not solver and not database" }

    # ── The store contract, against real PostgreSQL ────────────────────
    # FAILS when Docker is running but no database was reached: that is a
    # forgotten `docker compose up -d`, it is actionable, and letting it pass
    # would mean green certified nothing about FR-19's persistence.
    #
    # SKIPS when Docker itself is absent, matching how the frontend steps skip
    # without node_modules. A machine with no Docker cannot be told to start a
    # container it has no way to run.
    #
    # ⚠️ The failing half did NOT work until 2026-08-05, and it failed in the
    # worst direction. This checked only whether the DAEMON was up. With the
    # daemon running and the container stopped, the session fixture in
    # tests/integration/test_store_contract.py skips, pytest exits 0, and this
    # step printed [ok] - so `run-checks.ps1` reported "All checks passed" while
    # FR-19's persistence was covered by nothing at all. Found by reading the
    # step's own output during Phase 6 M1: "38 skipped" under a green tick.
    #
    # The check is therefore on the RESULT, not on the daemon: the run must
    # report tests that actually passed. That also covers the case a container
    # check would miss - `docker compose up -d` succeeds while another
    # PostgreSQL owns the port, so a running container is not proof that the
    # suite reached the database this repository ships (see CLAUDE.md).
    $dockerUp = $false
    try { docker info 2>&1 | Out-Null; $dockerUp = ($LASTEXITCODE -eq 0) } catch { $dockerUp = $false }

    if ($dockerUp) {
        Write-Host "[..] database tests" -ForegroundColor Cyan
        $dbOutput = & { uv run pytest -m database } 2>&1
        $dbOutput | Out-Host
        $dbExit = $LASTEXITCODE
        $ranSomething = ($dbOutput | Out-String) -match '\d+\s+passed'

        if ($dbExit -ne 0) {
            Write-Host "[FAIL] database tests (exit $dbExit)" -ForegroundColor Red
            $failed.Add('database tests')
        } elseif (-not $ranSomething) {
            Write-Host "[FAIL] database tests - every test skipped, so nothing was verified" -ForegroundColor Red
            Write-Host "       Docker is running but no database was reached." -ForegroundColor Yellow
            $failed.Add('database tests')
        } else {
            Write-Host "[ok] database tests" -ForegroundColor Green
        }
    } else {
        Write-Host "[skip] database tests - Docker is not running" -ForegroundColor Yellow
        Write-Host "       FR-19's persistence is NOT covered by this run." -ForegroundColor Yellow
    }
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
    if ($failed -contains 'database tests') {
        Write-Host ""
        Write-Host "PostgreSQL is not reachable. Start it with:" -ForegroundColor Yellow
        Write-Host "    docker compose up -d" -ForegroundColor Yellow
        Write-Host "If another server already owns 5432, set OPTIEDT_POSTGRES_PORT in .env" -ForegroundColor Yellow
        Write-Host "and OPTIEDT_DATABASE_URL in backend/.env - see README.md." -ForegroundColor Yellow
    }
    exit 1
}
Write-Host "All checks passed." -ForegroundColor Green
