# dbha-probe Windows stop script (PowerShell equivalent of stop-probe.sh).
# Two-stage stop: first a graceful stop via the named stop event (dbha-probe.exe
# stop), then a force-kill fallback. Before force-killing, both the executable
# path AND the process StartTime are validated to avoid killing an unrelated
# process that reused a recycled PID (mirrors stop-probe.sh validate_pid_target +
# safe_kill_after_term). Finally the periodic guard scheduled task is removed.
#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$BinaryPath = Join-Path $ScriptDir "bin\dbha-probe.exe"
$ConfigPath = Join-Path $ScriptDir "etc\probe.yaml"
$TaskName   = "DBHA_V2_PROBE_GUARD"

function Write-Log {
    param([string]$Level, [string]$Message)
    Write-Host ("{0} [{1}] {2}" -f (Get-Date -Format o), $Level, $Message)
}

if (-not (Test-Path $BinaryPath)) {
    Write-Log "ERROR" "binary missing, path: $BinaryPath"
    exit 1
}

$ExpectedExe = (Resolve-Path $BinaryPath).Path

function Get-ProbeProcesses {
    Get-CimInstance Win32_Process -Filter "Name='dbha-probe.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            ((Resolve-Path $_.ExecutablePath -ErrorAction SilentlyContinue).Path -eq $ExpectedExe)
        }
}

Write-Log "INFO" "stopping dbha-probe"

# Stage 1: graceful stop through the named stop event (guard + worker share it).
& $BinaryPath stop -c $ConfigPath 2>$null | Out-Null

# Snapshot pid -> StartTime BEFORE waiting, so the force-kill stage can detect
# PID reuse (a different process now holding the same PID).
$snapshot = @{}
foreach ($p in Get-ProbeProcesses) {
    $proc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
    if ($proc) { $snapshot[$p.ProcessId] = $proc.StartTime }
}

Start-Sleep -Seconds 1

# Stage 2: force-kill any survivor, but only if it is still OUR binary with the
# SAME StartTime as snapshotted (guards against PID recycling).
foreach ($procId in @($snapshot.Keys)) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if (-not $proc) { continue }

    $ci = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    if (-not $ci -or -not $ci.ExecutablePath) { continue }
    if ((Resolve-Path $ci.ExecutablePath -ErrorAction SilentlyContinue).Path -ne $ExpectedExe) { continue }
    if ($proc.StartTime -ne $snapshot[$procId]) { continue }

    Write-Log "WARN" "force killing surviving process, pid: $procId"
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

# Remove the periodic guard scheduled task (idempotent).
schtasks /Delete /TN $TaskName /F 2>$null | Out-Null

if (@(Get-ProbeProcesses).Count -gt 0) {
    Write-Log "ERROR" "dbha-probe still running after fallback"
    exit 1
}

Write-Log "INFO" "dbha-probe stopped successfully"
