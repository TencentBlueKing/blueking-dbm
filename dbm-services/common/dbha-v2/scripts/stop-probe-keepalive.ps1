# dbha-probe keepalive Windows stop script (equivalent of stop-probe-keepalive.sh).
# Two-stage stop: first set the keepalive named stop event (graceful), then a
# force-kill fallback validated by executable path + StartTime to avoid killing a
# process that reused a recycled PID. Finally remove the periodic guard task and
# the pid/addr state files.
#
# The keepalive Go process holds no pid file, so its stop event name is derived
# from the ping-http-addr, keyed identically to the Go side (see
# pkg/process/namedevent_windows.go deriveEventName): the event name is
#   Local\dbha-probe-<first16 hex chars of sha1(pingAddr)>-stop
# This must stay byte-for-byte in sync with the Go derivation.
#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

. (Join-Path $ScriptDir "lib\probe-event-utils.ps1")

$BinaryPath = Join-Path $ScriptDir "bin\dbha-probe.exe"
$RuntimeDir = Join-Path $ScriptDir "runtime"
$PidFile    = Join-Path $RuntimeDir "probe-keepalive.pid"
$AddrFile   = Join-Path $RuntimeDir "probe-keepalive.addr"
$TaskName   = "DBHA_PROBE_KEEPALIVE_GUARD"

function Write-Log {
    param([string]$Level, [string]$Message)
    Write-Host ("{0} [{1}] {2}" -f (Get-Date -Format o), $Level, $Message)
}

if (-not (Test-Path $BinaryPath)) {
    Write-Log "ERROR" "binary missing, path: $BinaryPath"
    exit 1
}

$ExpectedExe = (Resolve-Path $BinaryPath).Path

$targetAddr = ""
if (Test-Path $AddrFile) {
    $targetAddr = (Get-Content -Path $AddrFile -Raw).Trim()
}

Write-Log "INFO" "stopping dbha-probe keepalive"

# Stage 1: graceful stop via named event (only possible if we know the addr).
if (-not [string]::IsNullOrWhiteSpace($targetAddr)) {
    if (Set-KeepaliveStopEvent $targetAddr) {
        Write-Log "INFO" "keepalive stop event set, addr: $targetAddr"
    } else {
        Write-Log "INFO" "keepalive stop event not found (not running?), addr: $targetAddr"
    }
}

function Get-KeepaliveProcesses {
    Get-CimInstance Win32_Process -Filter "Name='dbha-probe.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            ((Resolve-Path $_.ExecutablePath -ErrorAction SilentlyContinue).Path -eq $ExpectedExe) -and
            $_.CommandLine -and ($_.CommandLine -match [regex]::Escape("--ping-http-addr")) -and
            ([string]::IsNullOrWhiteSpace($targetAddr) -or ($_.CommandLine -match [regex]::Escape($targetAddr)))
        }
}

# Snapshot pid -> StartTime before waiting (PID-reuse guard).
$snapshot = @{}
foreach ($p in Get-KeepaliveProcesses) {
    $proc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
    if ($proc) { $snapshot[$p.ProcessId] = $proc.StartTime }
}

Start-Sleep -Seconds 1

# Stage 2: force-kill survivors, validating exe path + StartTime.
foreach ($procId in @($snapshot.Keys)) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if (-not $proc) { continue }

    $ci = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    if (-not $ci -or -not $ci.ExecutablePath) { continue }
    if ((Resolve-Path $ci.ExecutablePath -ErrorAction SilentlyContinue).Path -ne $ExpectedExe) { continue }
    if ($proc.StartTime -ne $snapshot[$procId]) { continue }

    Write-Log "WARN" "force killing surviving keepalive, pid: $procId"
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
Remove-Item -Force -ErrorAction SilentlyContinue $PidFile, $AddrFile

if (@(Get-KeepaliveProcesses).Count -gt 0) {
    Write-Log "ERROR" "keepalive still running after stop"
    exit 1
}

Write-Log "INFO" "dbha-probe keepalive stopped"
