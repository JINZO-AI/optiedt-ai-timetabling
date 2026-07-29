<#
.SYNOPSIS
    Report which benchmark archives are present, and re-check the known defects.

.DESCRIPTION
    These archives are gitignored, never loaded into the database, and never
    merged with the generated instance (ADR-008). They exist so the engine can
    be validated on instances it was not built around — an engine validated only
    on its own generated instance has demonstrated nothing.

    The Kaggle checks below re-measure defects already recorded in
    data/reference/PROVENANCE.md. They are re-run rather than trusted, because
    that archive describes itself as clean and is not.
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$ref = Join-Path $root 'data\reference'

Write-Host "Reference archives - $ref" -ForegroundColor Cyan
Write-Host ""

# ── Presence ────────────────────────────────────────────────────────
$itc = Join-Path $ref 'itc2007-cct-master\itc2007-cct-master\datasets'
if (Test-Path $itc) {
    $n = (Get-ChildItem $itc -Filter 'comp*.ctt').Count
    Write-Host "[ok]   ITC-2007 Track 3     $n comp instances" -ForegroundColor Green
} else {
    Write-Host "[--]   ITC-2007 Track 3     absent - blocks engine validation" -ForegroundColor Yellow
}

$xhstt = Join-Path $ref 'XHSTT-2014\XHSTT-2014.xml'
if (Test-Path $xhstt) {
    $n = ([regex]::Matches((Get-Content $xhstt -Raw), '<Instance\s+Id=')).Count
    Write-Host "[ok]   XHSTT-2014           $n instances in the version held" -ForegroundColor Green
} else {
    Write-Host "[--]   XHSTT-2014           absent" -ForegroundColor Yellow
}

$kaggle = Join-Path $ref 'Kaggle University Exam Scheduling'
if (Test-Path $kaggle) {
    Write-Host "[!!]   Kaggle exam           present - 2 of 6 files INVALID, see below" -ForegroundColor Yellow
} else {
    Write-Host "[--]   Kaggle exam          absent" -ForegroundColor Yellow
}

Write-Host "[--]   ITC-2007 Track 1     not present, not opened - increment 2 only" -ForegroundColor DarkGray
Write-Host "       Verify it before assuming any property of it."

# ── Re-measure the Kaggle defects ───────────────────────────────────
if (Test-Path $kaggle) {
    Write-Host ""
    Write-Host "Kaggle - re-measuring recorded defects" -ForegroundColor Cyan

    $slots = Import-Csv (Join-Path $kaggle 'timeslots.csv')
    $bad = @($slots | Where-Object { $_.end_time -le $_.start_time }).Count
    $pct = [math]::Round(100 * $bad / $slots.Count)
    Write-Host "  timeslots.csv : $bad of $($slots.Count) rows have end <= start ($pct%)"

    $sched = Import-Csv (Join-Path $kaggle 'schedule.csv')
    $byRoomSlot = $sched | Group-Object { "$($_.classroom_id)|$($_.timeslot_id)" }
    $clash = @($byRoomSlot | Where-Object { ($_.Group.course_id | Select-Object -Unique).Count -gt 1 }).Count
    $pct2 = [math]::Round(100 * $clash / $byRoomSlot.Count)
    Write-Host "  schedule.csv  : $clash of $($byRoomSlot.Count) room+slot pairs host >1 course ($pct2%)"

    Write-Host ""
    Write-Host "  Keep: classrooms.csv, enrolments. Drop: schedule.csv, timeslots.csv." -ForegroundColor Yellow
    Write-Host "  students.csv holds names, emails, phones, addresses - see PROVENANCE.md" -ForegroundColor Yellow
    Write-Host "  before using any part of it." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Full record: data/reference/PROVENANCE.md"
