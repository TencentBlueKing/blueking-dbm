# Shared Windows named-event helpers for dbha-probe scripts.
# Event names must stay byte-for-byte in sync with pkg/process/eventname.go (DeriveEventName).
#Requires -Version 5.1

function Get-DeriveEventName {
    param(
        [string]$Key,
        [string]$Suffix
    )
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Key)
        $hex = ($sha1.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join ''
    } finally {
        $sha1.Dispose()
    }
    return "Local\dbha-probe-" + $hex.Substring(0, 16) + $Suffix
}

function Get-EventKeyFromPidFile {
    param(
        [string]$PidFile,
        [string]$BaseDir
    )
    if ([string]::IsNullOrWhiteSpace($PidFile)) {
        return ""
    }
    if (-not [System.IO.Path]::IsPathRooted($PidFile)) {
        $PidFile = Join-Path $BaseDir $PidFile
    }
    return [System.IO.Path]::GetFullPath($PidFile)
}

function Get-ProbeStopEventNameFromPidFile {
    param(
        [string]$PidFile,
        [string]$BaseDir
    )
    $key = Get-EventKeyFromPidFile -PidFile $PidFile -BaseDir $BaseDir
    return Get-DeriveEventName -Key $key -Suffix "-stop"
}

function Set-NamedStopEvent {
    param([string]$EventName)
    try {
        $evt = [System.Threading.EventWaitHandle]::OpenExisting($EventName)
        [void]$evt.Set()
        $evt.Dispose()
        return $true
    } catch [System.Threading.WaitHandleCannotBeOpenedException] {
        return $false
    }
}

function Set-ProbeStopEventByPidFile {
    param(
        [string]$PidFile,
        [string]$BaseDir
    )
    $name = Get-ProbeStopEventNameFromPidFile -PidFile $PidFile -BaseDir $BaseDir
    return Set-NamedStopEvent -EventName $name
}

function Get-KeepaliveStopEventName {
    param([string]$Addr)
    return Get-DeriveEventName -Key $Addr -Suffix "-stop"
}

function Set-KeepaliveStopEvent {
    param([string]$Addr)
    $name = Get-KeepaliveStopEventName -Addr $Addr
    return Set-NamedStopEvent -EventName $name
}

function Get-PidFileFromProbeConfig {
    param(
        [string]$ConfigPath,
        [string]$BaseDir
    )
    if (-not (Test-Path $ConfigPath)) {
        return Join-Path $BaseDir "pids\probe.pid"
    }
    $content = Get-Content -Path $ConfigPath -Raw
    if ($content -match '(?m)^pidFile:\s*"?([^"\r\n#]+)"?') {
        $raw = $Matches[1].Trim()
        if ([System.IO.Path]::IsPathRooted($raw)) {
            return $raw
        }
        return Join-Path $BaseDir ($raw -replace '/', '\')
    }
    return Join-Path $BaseDir "pids\probe.pid"
}
