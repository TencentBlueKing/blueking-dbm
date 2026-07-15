# dbha-probe Windows start script.
# Admin-only: stop legacy user-session processes, register a minutely SYSTEM
# Scheduled Task that runs `dbha-probe ensure --from-cron`, then schtasks /Run.
# Cold start does NOT daemon-start in the interactive session (avoids dual instances).
#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$BinaryPath = Join-Path $ScriptDir "bin\dbha-probe.exe"
$ConfigPath = Join-Path $ScriptDir "etc\probe.yaml"
$TaskName   = "DBHA_V2_PROBE_GUARD"
$StopScript = Join-Path $ScriptDir "stop-probe.ps1"

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
if (-not (Test-Path $ConfigPath)) {
    Write-Log "ERROR" "config missing, path: $ConfigPath"
    exit 1
}

# Upgrade / re-start: stop legacy Local\ / user-session processes and delete old task.
if (Test-Path $StopScript) {
    Write-Log "INFO" "stopping existing probe (graceful Global event + force-kill fallback)"
    try {
        & $StopScript
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN" "stop-probe.ps1 exited $LASTEXITCODE; continuing with task registration"
        }
    }
    catch {
        Write-Log "WARN" ("stop-probe.ps1 failed: {0}; continuing with task registration" -f $_.Exception.Message)
    }
}

# schtasks /TR cannot contain bare &&/& (splitter). Emit a tiny .cmd that cds to
# InstallRoot then runs ensure (same semantics as: cmd /c "cd /d root && ensure").
$runtimeDir = Join-Path $ScriptDir "runtime"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$helper = Join-Path $runtimeDir "run-ensure-probe.cmd"
@(
    "@echo off"
    "cd /d `"$ScriptDir`""
    "bin\dbha-probe.exe ensure -c etc\probe.yaml --from-cron"
) | Set-Content -Path $helper -Encoding ascii

Write-Log "INFO" "registering SYSTEM scheduled task $TaskName (TR=$helper)"
$createArgs = @('/Create', '/SC', 'MINUTE', '/MO', '1', '/TN', $TaskName, '/RU', 'SYSTEM', '/F', '/TR', $helper)
& schtasks @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "schtasks /Create failed (TR=$helper)"
    exit 1
}

Write-Log "INFO" "starting probe via schtasks /Run (Session 0 SYSTEM)"
& schtasks @('/Run', '/TN', $TaskName) | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "schtasks /Run failed"
    exit 1
}

$ExpectedExe = (Resolve-Path $BinaryPath).Path
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    $guards = @(Get-CimInstance Win32_Process -Filter "Name='dbha-probe.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            ((Resolve-Path $_.ExecutablePath -ErrorAction SilentlyContinue).Path -eq $ExpectedExe) -and
            $_.CommandLine -and ($_.CommandLine -match "daemon-start") -and
            ($_.CommandLine -notmatch "--ping-http-addr")
        })
    if ($guards.Count -gt 0) {
        $ok = $true
        break
    }
}

if (-not $ok) {
    Write-Log "ERROR" "probe guard not up after schtasks /Run; check InstallRoot pids/logs and task history"
    exit 1
}

Write-Log "INFO" "daemon-start (SYSTEM) success; health: bin\dbha-probe.exe health -c etc\probe.yaml"
exit 0
