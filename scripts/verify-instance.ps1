<#
.SYNOPSIS
    Check the reference instance against the figures the documentation states.

.DESCRIPTION
    The three specification documents state the instance's content and its five
    verification results as facts. This confirms the files in data/instance/
    still match them.

    Run it after any change to the instance or the generator. A failure means
    either the instance changed or the documentation is now false.
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) { Write-Host "No python found." -ForegroundColor Red; exit 1 }

& $python (Join-Path $root 'data\verification\verify_instance.py')
exit $LASTEXITCODE
