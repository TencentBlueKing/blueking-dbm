# Sandbox smoke tests for dbha-probe run modes (Windows).
# Covers branch #18637: named-event stop for worker / daemon-start / keepalive,
# PS↔Go event-name parity, and optional schtasks script path.
#
# Usage (from dbha-v2 root or anywhere):
#   .\scripts\sandbox-probe-modes.ps1
#   .\scripts\sandbox-probe-modes.ps1 -SkipBuild -PingHttpAddr 127.0.0.1:18080
#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$SandboxRoot = "",
    [switch]$SkipBuild,
    [string]$PingHttpAddr = "127.0.0.1:18080"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($SandboxRoot)) {
    $SandboxRoot = Join-Path $RepoRoot "build\sandbox-probe"
}
$SandboxRoot = [System.IO.Path]::GetFullPath($SandboxRoot)
$ReportPath = Join-Path $SandboxRoot "sandbox-report.txt"
$Results = [System.Collections.Generic.List[object]]::new()
$LogLines = [System.Collections.Generic.List[string]]::new()

function Write-SandboxLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ss"), $Message
    Write-Host $line
    $LogLines.Add($line) | Out-Null
}

function Add-Result {
    param(
        [string]$Id,
        [ValidateSet("PASS", "FAIL", "SKIP")]
        [string]$Status,
        [string]$Detail
    )
    $Results.Add([pscustomobject]@{ Id = $Id; Status = $Status; Detail = $Detail }) | Out-Null
    Write-SandboxLog ("[{0}] {1}: {2}" -f $Status, $Id, $Detail)
}

function Get-SandboxExeProcesses {
    param([string]$ExePath)
    $resolved = (Resolve-Path $ExePath -ErrorAction SilentlyContinue).Path
    if (-not $resolved) { return @() }
    Get-CimInstance Win32_Process -Filter "Name='dbha-probe.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            ((Resolve-Path $_.ExecutablePath -ErrorAction SilentlyContinue).Path -eq $resolved)
        }
}

function Stop-SandboxProcesses {
    param([string]$ExePath)
    $procs = @(Get-SandboxExeProcesses -ExePath $ExePath)
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 300
}

function Remove-SandboxTasks {
    foreach ($tn in @("DBHA_PROBE_KEEPALIVE_GUARD", "DBHA_V2_PROBE_GUARD")) {
        # Task may already be gone; never treat "not found" as terminating.
        cmd /c "schtasks /Delete /TN `"$tn`" /F >NUL 2>&1" | Out-Null
    }
}

function Test-SchtaskExists {
    param([string]$TaskName)
    cmd /c "schtasks /Query /TN `"$TaskName`" >NUL 2>&1" | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Test-IsAdministrator {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-SchtaskRunAsAndTr {
    param([string]$TaskName)
    $xml = schtasks /Query /TN $TaskName /XML 2>$null | Out-String
    if ($LASTEXITCODE -ne 0) { return $null }
    $runAs = $null
    $tr = $null
    if ($xml -match '<UserId>([^<]+)</UserId>') { $runAs = $Matches[1] }
    if ($xml -match '<Command>([^<]+)</Command>') {
        $cmd = $Matches[1]
        $args = ""
        if ($xml -match '<Arguments>([^<]+)</Arguments>') { $args = $Matches[1] }
        $tr = ($cmd + " " + $args).Trim()
    }
    # Fallback: /V /FO LIST
    if (-not $tr) {
        $list = schtasks /Query /TN $TaskName /V /FO LIST 2>$null | Out-String
        foreach ($line in ($list -split "`r?`n")) {
            if ($line -match '^\s*Task To Run:\s*(.+)$') { $tr = $Matches[1].Trim() }
            if ($line -match '^\s*Run As User:\s*(.+)$') { $runAs = $Matches[1].Trim() }
        }
    }
    return [pscustomobject]@{ RunAs = $runAs; Tr = $tr }
}

function Initialize-Sandbox {
    Write-SandboxLog "initializing sandbox at $SandboxRoot"
    if (Test-Path $SandboxRoot) {
        $exe = Join-Path $SandboxRoot "bin\dbha-probe.exe"
        if (Test-Path $exe) { Stop-SandboxProcesses -ExePath $exe }
        Remove-SandboxTasks
        Remove-Item -Recurse -Force $SandboxRoot
    }

    $dirs = @(
        (Join-Path $SandboxRoot "bin"),
        (Join-Path $SandboxRoot "etc"),
        (Join-Path $SandboxRoot "pids"),
        (Join-Path $SandboxRoot "logs"),
        (Join-Path $SandboxRoot "runtime"),
        (Join-Path $SandboxRoot "lib")
    )
    foreach ($d in $dirs) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }

    $yaml = @"
name: sandbox-probe
version: test
serviceID: "sandbox"
pidFile: "./pids/probe.pid"
log:
  path: "./logs/probe.log"
  level: info
  fileCount: 3
  fileSize: 10
"@
    Set-Content -Path (Join-Path $SandboxRoot "etc\probe.yaml") -Value $yaml -Encoding utf8

    $copyMap = @{
        (Join-Path $RepoRoot "scripts\start-probe.ps1")              = (Join-Path $SandboxRoot "start-probe.ps1")
        (Join-Path $RepoRoot "scripts\stop-probe.ps1")               = (Join-Path $SandboxRoot "stop-probe.ps1")
        (Join-Path $RepoRoot "scripts\start-probe-keepalive.ps1")    = (Join-Path $SandboxRoot "start-probe-keepalive.ps1")
        (Join-Path $RepoRoot "scripts\stop-probe-keepalive.ps1")     = (Join-Path $SandboxRoot "stop-probe-keepalive.ps1")
        (Join-Path $RepoRoot "scripts\lib\probe-event-utils.ps1")    = (Join-Path $SandboxRoot "lib\probe-event-utils.ps1")
    }
    foreach ($src in $copyMap.Keys) {
        if (-not (Test-Path $src)) { throw "missing source file: $src" }
        Copy-Item -Force $src $copyMap[$src]
    }
}

function Ensure-Binary {
    $dest = Join-Path $SandboxRoot "bin\dbha-probe.exe"
    $built = Join-Path $RepoRoot "build\dbha-probe.exe"

    if (-not $SkipBuild) {
        Write-SandboxLog "building Windows probe binary"
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")
        Push-Location $RepoRoot
        try {
            $env:CGO_ENABLED = "0"
            $env:GOOS = "windows"
            $env:GOARCH = "amd64"
            New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "build") | Out-Null
            & go build -o $built (Join-Path $RepoRoot "cmd\probe")
            if ($LASTEXITCODE -ne 0) { throw "go build probe failed" }
        }
        finally {
            Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
            Remove-Item Env:GOOS -ErrorAction SilentlyContinue
            Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
            Pop-Location
        }
    }

    if (-not (Test-Path $built)) {
        throw "binary not found at $built; build first or omit -SkipBuild"
    }
    Copy-Item -Force $built $dest
    Write-SandboxLog "binary ready: $dest"
    return $dest
}

function Test-SchtasksWritable {
    $tn = "DBHA_SANDBOX_PROBE_PERM_CHECK"
    cmd /c "schtasks /Create /SC ONCE /ST 23:59 /TN `"$tn`" /TR `"cmd /c exit 0`" /F >NUL 2>&1" | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    cmd /c "schtasks /Delete /TN `"$tn`" /F >NUL 2>&1" | Out-Null
    return $ok
}

function Wait-Condition {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSec = 15,
        [string]$What = "condition"
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) { return $true }
        Start-Sleep -Milliseconds 250
    }
    throw "timeout waiting for $What (${TimeoutSec}s)"
}

function Invoke-CaseE1 {
    . (Join-Path $SandboxRoot "lib\probe-event-utils.ps1")
    $got = Get-KeepaliveStopEventName -Addr "127.0.0.1:8080"
    $want = 'Global\dbha-probe-56852a5456d1b09e-stop'
    if ($got -ne $want) {
        Add-Result -Id "E1" -Status "FAIL" -Detail "event name mismatch: got=$got want=$want"
        return
    }
    Add-Result -Id "E1" -Status "PASS" -Detail "PS Get-KeepaliveStopEventName matches Go golden"
}

function Invoke-CaseK1 {
    param(
        [string]$ExePath,
        [bool]$SchtasksOk
    )
    . (Join-Path $SandboxRoot "lib\probe-event-utils.ps1")
    $startScript = Join-Path $SandboxRoot "start-probe-keepalive.ps1"
    $stopScript = Join-Path $SandboxRoot "stop-probe-keepalive.ps1"
    $pidFile = Join-Path $SandboxRoot "runtime\probe-keepalive.pid"
    $usedScriptPath = $false
    $schtasksNote = ""

    Stop-SandboxProcesses -ExePath $ExePath
    Remove-Item -Force -ErrorAction SilentlyContinue $pidFile, (Join-Path $SandboxRoot "runtime\probe-keepalive.addr")

    if ($SchtasksOk) {
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $startScript -PingHttpAddr $PingHttpAddr
            if ($LASTEXITCODE -ne 0) { throw "start-probe-keepalive.ps1 exit $LASTEXITCODE" }
            $usedScriptPath = $true
            $schtasksNote = "; schtasks register via start script OK"
        }
        catch {
            $schtasksNote = "; schtasks/script start failed ($($_.Exception.Message)), fell back to CLI"
            $usedScriptPath = $false
        }
    }
    else {
        $schtasksNote = "; schtasks not writable, using CLI path (schtasks SKIP)"
    }

    if (-not $usedScriptPath) {
        $proc = Start-Process -FilePath $ExePath `
            -ArgumentList @("--ping-http-addr", $PingHttpAddr) `
            -WorkingDirectory $SandboxRoot `
            -WindowStyle Hidden -PassThru
        Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
        Set-Content -Path (Join-Path $SandboxRoot "runtime\probe-keepalive.addr") -Value $PingHttpAddr -Encoding ascii
        Start-Sleep -Milliseconds 500
        if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
            Add-Result -Id "K1" -Status "FAIL" -Detail "CLI keepalive failed to stay up"
            return
        }
    }

    try {
        $null = Wait-Condition -What "ping ready" -TimeoutSec 10 -Condition {
            try {
                $resp = Invoke-WebRequest -Uri ("http://{0}/ping" -f $PingHttpAddr) -UseBasicParsing -TimeoutSec 2
                return ($resp.StatusCode -eq 200 -and $resp.Content -match "pong")
            }
            catch { return $false }
        }
        $pingBody = (Invoke-WebRequest -Uri ("http://{0}/ping" -f $PingHttpAddr) -UseBasicParsing -TimeoutSec 2).Content

        if ($usedScriptPath) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript
            if ($LASTEXITCODE -ne 0) { throw "stop-probe-keepalive.ps1 exit $LASTEXITCODE" }
        }
        else {
            if (-not (Set-KeepaliveStopEvent -Addr $PingHttpAddr)) {
                throw "Set-KeepaliveStopEvent failed (event not found)"
            }
            $null = Wait-Condition -What "keepalive exit" -TimeoutSec 10 -Condition {
                @(Get-SandboxExeProcesses -ExePath $ExePath | Where-Object {
                        $_.CommandLine -and ($_.CommandLine -match [regex]::Escape("--ping-http-addr"))
                    }).Count -eq 0
            }
            Remove-Item -Force -ErrorAction SilentlyContinue $pidFile, (Join-Path $SandboxRoot "runtime\probe-keepalive.addr")
        }

        Start-Sleep -Milliseconds 500
        $left = @(Get-SandboxExeProcesses -ExePath $ExePath | Where-Object {
                $_.CommandLine -and ($_.CommandLine -match [regex]::Escape("--ping-http-addr"))
            })
        if ($left.Count -gt 0) {
            Add-Result -Id "K1" -Status "FAIL" -Detail "keepalive process still running after stop"
            return
        }
        if (Test-Path $pidFile) {
            Add-Result -Id "K1" -Status "FAIL" -Detail "probe-keepalive.pid still present"
            return
        }

        $taskLeft = Test-SchtaskExists -TaskName "DBHA_PROBE_KEEPALIVE_GUARD"

        $detail = "pingOK body=$pingBody$schtasksNote"
        if ($usedScriptPath -and $taskLeft) {
            Add-Result -Id "K1" -Status "FAIL" -Detail "keepalive guard task still present; $detail"
            return
        }
        if (-not $usedScriptPath) {
            Add-Result -Id "K1" -Status "PASS" -Detail "$detail | named-event stop OK (schtasks path SKIP)"
        }
        else {
            Add-Result -Id "K1" -Status "PASS" -Detail "$detail | script start/stop + task cleanup OK"
        }
    }
    catch {
        Add-Result -Id "K1" -Status "FAIL" -Detail $_.Exception.Message
        Stop-SandboxProcesses -ExePath $ExePath
    }
}

function Invoke-CaseS1 {
    param(
        [string]$ExePath,
        [bool]$SchtasksOk
    )
    # SYSTEM ensure cold-start + interactive Global stop (requires Admin).
    if (-not $SchtasksOk) {
        Add-Result -Id "S1" -Status "SKIP" -Detail "schtasks not writable"
        return
    }
    if (-not (Test-IsAdministrator)) {
        Add-Result -Id "S1" -Status "SKIP" -Detail "Administrator required for /RU SYSTEM start-probe.ps1"
        return
    }

    $startScript = Join-Path $SandboxRoot "start-probe.ps1"
    $stopScript = Join-Path $SandboxRoot "stop-probe.ps1"
    $pidFile = Join-Path $SandboxRoot "pids\probe.pid"
    Stop-SandboxProcesses -ExePath $ExePath
    Remove-SandboxTasks
    Remove-Item -Force -ErrorAction SilentlyContinue $pidFile

    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $startScript
        if ($LASTEXITCODE -ne 0) { throw "start-probe.ps1 exit $LASTEXITCODE" }

        $meta = Get-SchtaskRunAsAndTr -TaskName "DBHA_V2_PROBE_GUARD"
        if (-not $meta) { throw "DBHA_V2_PROBE_GUARD task missing after start" }
        if ($meta.Tr -notmatch 'ensure') { throw "task TR missing ensure (helper/cmd): $($meta.Tr)" }
        # schtasks XML may show "SYSTEM" or the well-known SID S-1-5-18.
        if ($meta.RunAs -notmatch '(?i)SYSTEM|S-1-5-18') {
            throw "task RunAs not SYSTEM: $($meta.RunAs)"
        }

        $null = Wait-Condition -What "SYSTEM guard" -TimeoutSec 20 -Condition {
            @(Get-SandboxExeProcesses -ExePath $ExePath | Where-Object {
                    $_.CommandLine -and ($_.CommandLine -match "daemon-start") -and
                    ($_.CommandLine -notmatch "--ping-http-addr")
                }).Count -ge 1
        }

        # Interactive stop must open Global\ event (not force-kill only).
        & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript
        if ($LASTEXITCODE -ne 0) { throw "stop-probe.ps1 exit $LASTEXITCODE" }

        $null = Wait-Condition -What "probe stopped" -TimeoutSec 20 -Condition {
            (@(Get-SandboxExeProcesses -ExePath $ExePath).Count -eq 0) -and (-not (Test-Path $pidFile))
        }

        Add-Result -Id "S1" -Status "PASS" -Detail ("SYSTEM TR contains ensure; RunAs={0}; interactive stop OK" -f $meta.RunAs)
    }
    catch {
        Add-Result -Id "S1" -Status "FAIL" -Detail $_.Exception.Message
        Stop-SandboxProcesses -ExePath $ExePath
        Remove-SandboxTasks
    }
}

function Invoke-CaseW1 {
    param([string]$ExePath)
    $cfg = "etc\probe.yaml"
    $pidFile = Join-Path $SandboxRoot "pids\probe.pid"
    Stop-SandboxProcesses -ExePath $ExePath
    Remove-Item -Force -ErrorAction SilentlyContinue $pidFile

    Push-Location $SandboxRoot
    try {
        & $ExePath start -c $cfg
        if ($LASTEXITCODE -ne 0) { throw "start failed exit=$LASTEXITCODE" }

        $null = Wait-Condition -What "worker pid file" -TimeoutSec 10 -Condition { Test-Path $pidFile }

        $health = & $ExePath health -c $cfg 2>&1 | Out-String
        if ($health -notmatch "running") {
            throw "health not running: $health"
        }

        & $ExePath stop -c $cfg
        if ($LASTEXITCODE -ne 0) { throw "stop failed exit=$LASTEXITCODE" }

        $null = Wait-Condition -What "worker gone" -TimeoutSec 15 -Condition {
            (@(Get-SandboxExeProcesses -ExePath $ExePath).Count -eq 0) -and (-not (Test-Path $pidFile))
        }

        Add-Result -Id "W1" -Status "PASS" -Detail "start/health/stop OK; pid cleared; named-event stop path"
    }
    catch {
        Add-Result -Id "W1" -Status "FAIL" -Detail $_.Exception.Message
        Stop-SandboxProcesses -ExePath $ExePath
        Remove-Item -Force -ErrorAction SilentlyContinue $pidFile
    }
    finally {
        Pop-Location
    }
}

function Invoke-CaseD1 {
    param([string]$ExePath)
    $cfg = "etc\probe.yaml"
    $pidFile = Join-Path $SandboxRoot "pids\probe.pid"
    Stop-SandboxProcesses -ExePath $ExePath
    Remove-Item -Force -ErrorAction SilentlyContinue $pidFile

    Push-Location $SandboxRoot
    try {
        & $ExePath daemon-start -c $cfg
        if ($LASTEXITCODE -ne 0) { throw "daemon-start failed exit=$LASTEXITCODE" }

        $null = Wait-Condition -What "daemon pid file" -TimeoutSec 10 -Condition { Test-Path $pidFile }

        $guards = @(Get-SandboxExeProcesses -ExePath $ExePath | Where-Object {
                $_.CommandLine -and ($_.CommandLine -match "daemon-start")
            })
        if ($guards.Count -lt 1) {
            throw "no guard process with daemon-start in cmdline"
        }

        # Allow worker child to appear under guard.
        Start-Sleep -Seconds 1
        $before = @(Get-SandboxExeProcesses -ExePath $ExePath)
        if ($before.Count -lt 1) {
            throw "no probe processes after daemon-start"
        }

        & $ExePath stop -c $cfg
        if ($LASTEXITCODE -ne 0) { throw "stop failed exit=$LASTEXITCODE" }

        $null = Wait-Condition -What "daemon fully stopped" -TimeoutSec 20 -Condition {
            (@(Get-SandboxExeProcesses -ExePath $ExePath).Count -eq 0) -and (-not (Test-Path $pidFile))
        }

        # Guard must not have relaunched a worker after stop.
        Start-Sleep -Seconds 2
        $after = @(Get-SandboxExeProcesses -ExePath $ExePath)
        if ($after.Count -gt 0) {
            throw ("residual processes after stop: " + (($after | ForEach-Object { $_.ProcessId }) -join ","))
        }
        if (Test-Path $pidFile) {
            throw "pid file still present after daemon stop"
        }

        Add-Result -Id "D1" -Status "PASS" -Detail ("daemon-start guard seen (n={0}), stop cleared guard+worker+pid" -f $guards.Count)
    }
    catch {
        Add-Result -Id "D1" -Status "FAIL" -Detail $_.Exception.Message
        Stop-SandboxProcesses -ExePath $ExePath
        Remove-Item -Force -ErrorAction SilentlyContinue $pidFile
    }
    finally {
        Pop-Location
    }
}

function Write-ReportFile {
    param(
        [string]$ExePath,
        [bool]$SchtasksOk,
        [string]$GoVersion,
        [string]$Branch,
        [string]$Commit
    )
    $pass = @($Results | Where-Object Status -eq "PASS").Count
    $fail = @($Results | Where-Object Status -eq "FAIL").Count
    $skip = @($Results | Where-Object Status -eq "SKIP").Count
    $lines = @()
    $lines += "dbha-probe sandbox mode test report"
    $lines += ("generated: {0}" -f (Get-Date -Format o))
    $lines += ("branch: {0}" -f $Branch)
    $lines += ("commit: {0}" -f $Commit)
    $lines += ("go: {0}" -f $GoVersion)
    $lines += ("sandbox: {0}" -f $SandboxRoot)
    $lines += ("binary: {0}" -f $ExePath)
    $lines += ("pingAddr: {0}" -f $PingHttpAddr)
    $lines += ("schtasksWritable: {0}" -f $SchtasksOk)
    $lines += ("summary: PASS={0} FAIL={1} SKIP={2}" -f $pass, $fail, $skip)
    $lines += ""
    $lines += "cases:"
    foreach ($r in $Results) {
        $lines += ("  {0,-4} {1,-4} {2}" -f $r.Id, $r.Status, $r.Detail)
    }
    $lines += ""
    $lines += "log:"
    $lines += $LogLines
    Set-Content -Path $ReportPath -Value ($lines -join "`n") -Encoding utf8
    Write-SandboxLog "wrote $ReportPath"
}

# ---- main ----
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
    [System.Environment]::GetEnvironmentVariable("Path", "User")

$branch = (git -C $RepoRoot rev-parse --abbrev-ref HEAD 2>$null)
$commit = (git -C $RepoRoot rev-parse --short HEAD 2>$null)
$goVer = (& go version 2>$null)

Initialize-Sandbox
$exe = Ensure-Binary
$schtasksOk = $false
try { $schtasksOk = Test-SchtasksWritable } catch { $schtasksOk = $false }
Write-SandboxLog ("schtasks writable: {0}" -f $schtasksOk)

Invoke-CaseE1
Invoke-CaseK1 -ExePath $exe -SchtasksOk $schtasksOk
Invoke-CaseS1 -ExePath $exe -SchtasksOk $schtasksOk
Invoke-CaseW1 -ExePath $exe
Invoke-CaseD1 -ExePath $exe

# Final cleanup
Stop-SandboxProcesses -ExePath $exe
Remove-SandboxTasks

Write-ReportFile -ExePath $exe -SchtasksOk $schtasksOk -GoVersion $goVer -Branch $branch -Commit $commit

Write-Host ""
Write-Host "===== SUMMARY ====="
foreach ($r in $Results) {
    Write-Host ("{0,-4} {1,-4} {2}" -f $r.Id, $r.Status, $r.Detail)
}
$failCount = @($Results | Where-Object Status -eq "FAIL").Count
if ($failCount -gt 0) {
    Write-Host "OVERALL: FAIL"
    exit 1
}
Write-Host "OVERALL: PASS"
exit 0
