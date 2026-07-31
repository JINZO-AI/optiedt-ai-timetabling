<#
.SYNOPSIS
    Validate the modelling approach on the published ITC-2007 Track 3 instances.

.DESCRIPTION
    docs/testing-strategy.md 1: "no timetable produced violates a hard
    constraint, and the distance between the cost obtained and the best known
    results". Both are re-derived from the instances by
    optiedt.validation.itc2007, never taken from CP-SAT's own status.

    Deliberately NOT part of run-checks.ps1: 21 instances at a real budget take
    tens of minutes. The fast half - that the cost function reproduces seven
    published solutions exactly - runs there instead, in
    tests/integration/test_itc2007_validation.py.

    The archives are gitignored. Run scripts/check-reference-data.ps1 if this
    reports them missing.

.PARAMETER Budget
    Deterministic time per instance, NOT seconds (ADR-011). Wall clock varies by
    machine; the unit of work does not.

.PARAMETER Instances
    Instance names, e.g. comp01 comp05. Default: all 21.

.EXAMPLE
    scripts/validate-itc2007.ps1 -Budget 120
.EXAMPLE
    scripts/validate-itc2007.ps1 -Instances comp01,comp11 -Budget 30
#>
param(
    [double]$Budget = 60,
    [int]$Seed = 42,
    [string[]]$Instances = @()
)

$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root 'backend')
try {
    $arguments = @('run', 'python', '-m', 'optiedt.validation.itc2007')
    $arguments += $Instances
    $arguments += @('--budget', $Budget, '--seed', $Seed)
    & uv @arguments
    $code = $LASTEXITCODE
} finally { Pop-Location }

if ($code -eq 2) {
    Write-Host ""
    Write-Host "The ITC-2007 archive is not present. It is gitignored on purpose -" -ForegroundColor Yellow
    Write-Host "see data/reference/PROVENANCE.md and scripts/check-reference-data.ps1." -ForegroundColor Yellow
} elseif ($code -ne 0) {
    Write-Host ""
    Write-Host "A timetable violated a hard constraint. That is a modelling bug, not a" -ForegroundColor Red
    Write-Host "quality result - the cost figures above mean nothing until it is fixed." -ForegroundColor Red
}
exit $code
