# dbha-probe keepalive Windows start script (equivalent of start-probe-keepalive.sh).
# Starts the keepalive ping server in the background, records its pid/addr, and
# registers a periodic Scheduled Task that re-runs this script with -FromCron to
# auto-restart it (equivalent to the Linux crontab guard).
#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PingHttpAddr,
    [switch]$FromCron
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

. (Join-Path $ScriptDir "lib\probe-event-utils.ps1")

$BinaryPath = Join-Path $ScriptDir "bin\dbha-probe.exe"
$RuntimeDir = Join-Path $ScriptDir "runtime"
$PidFile    = Join-Path $RuntimeDir "probe-keepalive.pid"
$AddrFile   = Join-Path $RuntimeDir "probe-keepalive.addr"
$TaskName   = "DBHA_PROBE_KEEPALIVE_GUARD"

$PingHttpAddr = $PingHttpAddr.Trim()

function Write-Log {
    param([string]$Level, [string]$Message)
    Write-Host ("{0} [{1}] {2}" -f (Get-Date -Format o), $Level, $Message)
}

if (-not (Test-Path $BinaryPath)) {
    Write-Log "ERROR" "binary missing, path: $BinaryPath"
    exit 1
}
if ([string]::IsNullOrWhiteSpace($PingHttpAddr)) {
    Write-Log "ERROR" "missing required -PingHttpAddr"
    exit 1
}

$ExpectedExe = (Resolve-Path $BinaryPath).Path
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

# Find running keepalive processes for this addr (our binary + matching --ping-http-addr).
function Get-KeepaliveProcesses {
    Get-CimInstance Win32_Process -Filter "Name='dbha-probe.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            ((Resolve-Path $_.ExecutablePath -ErrorAction SilentlyContinue).Path -eq $ExpectedExe) -and
            $_.CommandLine -and ($_.CommandLine -match [regex]::Escape("--ping-http-addr")) -and
            ($_.CommandLine -match [regex]::Escape($PingHttpAddr))
        }
}

function Register-Guard {
    $action = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$ScriptDir\start-probe-keepalive.ps1`" -PingHttpAddr `"$PingHttpAddr`" -FromCron"
    schtasks /Create /SC MINUTE /MO 1 /TN $TaskName /TR $action /F | Out-Null
}

$running = @(Get-KeepaliveProcesses)
if ($running.Count -gt 0) {
    if ($FromCron) {
        Write-Log "INFO" "keepalive already running, skip restart in cron"
        exit 0
    }
    Write-Log "INFO" "existing keepalive detected, stopping before restart"
    if (Set-KeepaliveStopEvent -Addr $PingHttpAddr) {
        Write-Log "INFO" ("keepalive stop event set, addr: {0}" -f $PingHttpAddr)
    } else {
        Write-Log "INFO" ("keepalive stop event not found, addr: {0}" -f $PingHttpAddr)
    }

    $snapshot = @{}
    foreach ($p in $running) {
        $proc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
        if ($proc) { $snapshot[$p.ProcessId] = $proc.StartTime }
    }

    Start-Sleep -Seconds 1

    foreach ($procId in @($snapshot.Keys)) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc) { continue }

        $ci = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if (-not $ci -or -not $ci.ExecutablePath) { continue }
        if ((Resolve-Path $ci.ExecutablePath -ErrorAction SilentlyContinue).Path -ne $ExpectedExe) { continue }
        if ($proc.StartTime -ne $snapshot[$procId]) { continue }

        Write-Log "WARN" ("force killing surviving keepalive before restart, pid: {0}" -f $procId)
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

Write-Log "INFO" "starting dbha-probe keepalive in background, ping_http_addr: $PingHttpAddr"
$proc = Start-Process -FilePath $BinaryPath `
    -ArgumentList @("--ping-http-addr", $PingHttpAddr) `
    -WindowStyle Hidden -PassThru

Set-Content -Path $PidFile -Value $proc.Id -Encoding ascii
Set-Content -Path $AddrFile -Value $PingHttpAddr -Encoding ascii

Start-Sleep -Milliseconds 500
if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR" "keepalive startup check failed, pid: $($proc.Id)"
    Remove-Item -Force -ErrorAction SilentlyContinue $PidFile, $AddrFile
    exit 1
}

if (-not $FromCron) { Register-Guard }

Write-Log "INFO" "dbha-probe keepalive started, pid: $($proc.Id)"
Write-Log "INFO" "health check: curl http://$PingHttpAddr/ping"
