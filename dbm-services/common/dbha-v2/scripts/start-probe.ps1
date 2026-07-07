# dbha-probe Windows start script (PowerShell equivalent of start-probe.sh).
# Starts the probe in daemon-start (guard+worker) mode and registers a periodic
# Scheduled Task that re-runs this script with -FromCron to auto-restart if the
# guard dies (equivalent to the Linux crontab guard).
#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$FromCron
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

. (Join-Path $ScriptDir "lib\probe-event-utils.ps1")

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
if (-not (Test-Path $ConfigPath)) {
    Write-Log "ERROR" "config missing, path: $ConfigPath"
    exit 1
}

$ExpectedExe = (Resolve-Path $BinaryPath).Path

# Return CIM process records for dbha-probe.exe whose executable is our binary.
function Get-ProbeProcesses {
    Get-CimInstance Win32_Process -Filter "Name='dbha-probe.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            ((Resolve-Path $_.ExecutablePath -ErrorAction SilentlyContinue).Path -eq $ExpectedExe)
        }
}

function Test-IsGuard {
    param($Proc)
    return ($Proc.CommandLine -and ($Proc.CommandLine -match "daemon-start"))
}

function Register-Guard {
    # Periodic (every minute) scheduled task, idempotent via /F. Mirrors the Linux
    # crontab periodic guard rather than a one-shot ONSTART task.
    $action = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$ScriptDir\start-probe.ps1`" -FromCron"
    schtasks /Create /SC MINUTE /MO 1 /TN $TaskName /TR $action /F | Out-Null
}

$procs  = @(Get-ProbeProcesses)
$guards  = @($procs | Where-Object { Test-IsGuard $_ })

# Guard-first: if a guard is running, keep current state and avoid duplicate daemon-start.
if ($guards.Count -gt 0) {
    Write-Log "INFO" "guard already running, keep current state"
    if (-not $FromCron) { Register-Guard }
    exit 0
}

# Only a worker (no guard): stop stale worker(s) and recover to guard+worker shape.
$workers = @($procs | Where-Object { -not (Test-IsGuard $_) })
if ($workers.Count -gt 0) {
    $pidFile = Get-PidFileFromProbeConfig -ConfigPath $ConfigPath -BaseDir $ScriptDir
    if (Set-ProbeStopEventByPidFile -PidFile $pidFile -BaseDir $ScriptDir) {
        Write-Log "INFO" ("probe stop event set, pid_file: {0}" -f $pidFile)
    } else {
        Write-Log "INFO" ("probe stop event not found, pid_file: {0}" -f $pidFile)
    }

    $snapshot = @{}
    foreach ($w in $workers) {
        $proc = Get-Process -Id $w.ProcessId -ErrorAction SilentlyContinue
        if ($proc) { $snapshot[$w.ProcessId] = $proc.StartTime }
    }

    Start-Sleep -Seconds 1

    foreach ($procId in @($snapshot.Keys)) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc) { continue }

        $ci = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if (-not $ci -or -not $ci.ExecutablePath) { continue }
        if ((Resolve-Path $ci.ExecutablePath -ErrorAction SilentlyContinue).Path -ne $ExpectedExe) { continue }
        if ($proc.StartTime -ne $snapshot[$procId]) { continue }

        Write-Log "WARN" ("force killing stale worker without guard, pid: {0}" -f $procId)
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

& $BinaryPath daemon-start -c $ConfigPath
if ($LASTEXITCODE -eq 0) {
    Write-Log "INFO" "daemon-start success"
    if (-not $FromCron) { Register-Guard }
    exit 0
}

Write-Log "ERROR" "daemon-start failed"
exit 1
