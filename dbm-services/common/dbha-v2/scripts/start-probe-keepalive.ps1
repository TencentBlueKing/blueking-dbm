# dbha-probe keepalive Windows start script.
# Admin-only: stop legacy keepalive, register minutely SYSTEM task running
# ensure-keepalive --from-cron, then schtasks /Run. No interactive-session spawn.
#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PingHttpAddr
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$BinaryPath = Join-Path $ScriptDir "bin\dbha-probe.exe"
$TaskName   = "DBHA_PROBE_KEEPALIVE_GUARD"
$StopScript = Join-Path $ScriptDir "stop-probe-keepalive.ps1"
$PingHttpAddr = $PingHttpAddr.Trim()

function Write-Log {
    param([string]$Level, [string]$Message)
    Write-Host ("{0} [{1}] {2}" -f (Get-Date -Format o), $Level, $Message)
}

function Test-IsAdministrator {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    Write-Log "ERROR" "Administrator privileges required to register SYSTEM scheduled task (no interactive-user fallback)"
    exit 1
}
if (-not (Test-Path $BinaryPath)) {
    Write-Log "ERROR" "binary missing, path: $BinaryPath"
    exit 1
}
if ([string]::IsNullOrWhiteSpace($PingHttpAddr)) {
    Write-Log "ERROR" "missing required -PingHttpAddr"
    exit 1
}

if (Test-Path $StopScript) {
    Write-Log "INFO" "stopping existing keepalive"
    try {
        & $StopScript
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN" "stop-probe-keepalive.ps1 exited $LASTEXITCODE; continuing"
        }
    }
    catch {
        Write-Log "WARN" ("stop-probe-keepalive.ps1 failed: {0}; continuing" -f $_.Exception.Message)
    }
}

# schtasks /TR cannot contain bare &&/&; helper .cmd cds to InstallRoot then ensure-keepalive.
$runtimeDir = Join-Path $ScriptDir "runtime"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$helper = Join-Path $runtimeDir "run-ensure-keepalive.cmd"
@(
    "@echo off"
    "cd /d `"$ScriptDir`""
    "bin\dbha-probe.exe ensure-keepalive --ping-http-addr $PingHttpAddr --from-cron"
) | Set-Content -Path $helper -Encoding ascii

Write-Log "INFO" "registering SYSTEM scheduled task $TaskName (TR=$helper)"
$createArgs = @('/Create', '/SC', 'MINUTE', '/MO', '1', '/TN', $TaskName, '/RU', 'SYSTEM', '/F', '/TR', $helper)
& schtasks @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "schtasks /Create failed (TR=$helper)"
    exit 1
}

Write-Log "INFO" "starting keepalive via schtasks /Run (Session 0 SYSTEM)"
& schtasks @('/Run', '/TN', $TaskName) | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "schtasks /Run failed"
    exit 1
}

$ExpectedExe = (Resolve-Path $BinaryPath).Path
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    $running = @(Get-CimInstance Win32_Process -Filter "Name='dbha-probe.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            ((Resolve-Path $_.ExecutablePath -ErrorAction SilentlyContinue).Path -eq $ExpectedExe) -and
            $_.CommandLine -and ($_.CommandLine -match [regex]::Escape("--ping-http-addr")) -and
            ($_.CommandLine -match [regex]::Escape($PingHttpAddr))
        })
    if ($running.Count -gt 0) {
        $ok = $true
        break
    }
}

if (-not $ok) {
    Write-Log "ERROR" "keepalive not up after schtasks /Run"
    exit 1
}

Write-Log "INFO" "keepalive started (SYSTEM); health: curl http://$PingHttpAddr/ping"
exit 0
