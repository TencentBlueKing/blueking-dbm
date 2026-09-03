# MIT License
#
# Copyright (c) 2023 腾讯蓝鲸
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Windows PowerShell build script equivalent to Makefile.
# Usage:
#   .\build.ps1
#   .\build.ps1 probe
#   .\build.ps1 package-probe-windows
#   .\build.ps1 -GoOS windows all
#   .\build.ps1 help

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Target = "all",

    [ValidateSet("linux", "windows", "darwin")]
    [string]$GoOS = "linux",

    [string]$Version
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RootDir = $PSScriptRoot
Set-Location $RootDir

# base (aligned with Makefile)
$Project = "dbha-v2"
$Protoc = "protoc"
$ProtoDir = "pkg/proto/idl"
$GenDir = "pkg/proto"
$BuildDir = "build"
$Module = "dbm-services/common/dbha-v2/pkg"
$BinPrefix = "dbha-"

$ServerBins = @("dbha-admin", "dbha-analysis", "dbha-receiver")
$ProbeBins = @("dbha-probe")
$ProbeWindowsBin = "dbha-probe.exe"
$ServerToolkits = @("dbha-cluster", "dbha-bwmgr")
$ServerToolkitConfigs = @("cluster.yaml", "bwmgr.yaml")
$ServerTemplates = @("admin.yaml", "analysis.yaml", "receiver.yaml")
$ServerSnippets = @(
    "receiver_source_probe.yaml",
    "receiver_source_kafka.yaml",
    "receiver_sink_mysql.yaml"
)
$ProbeTemplates = @("probe.yaml")
$ProbeSnippets = @("probe_mysql_shard.yaml", "probe_redis_shard.yaml")
$GuardUtilsLib = "scripts/lib/guard-utils.sh"
$ServerScripts = @(
    "scripts/setup.sh",
    "scripts/start-server.sh",
    "scripts/stop-server.sh",
    "scripts/deploy.sh",
    "scripts/render_configs.py"
)
$ProbeScripts = @(
    "scripts/start-probe.sh",
    "scripts/stop-probe.sh",
    "scripts/start-probe-keepalive.sh",
    "scripts/stop-probe-keepalive.sh",
    "scripts/deploy.sh",
    "scripts/render_configs.py"
)
$ProbeWindowsScripts = @(
    "scripts/start-probe.ps1",
    "scripts/stop-probe.ps1",
    "scripts/start-probe-keepalive.ps1",
    "scripts/stop-probe-keepalive.ps1",
    "scripts/render_configs.py"
)
$ProbeWindowsLibs = @(
    "scripts/lib/probe-event-utils.ps1"
)

function Get-GitOutput {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
    $out = & git @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($out | Out-String))) {
        return "unknown"
    }
    return ($out | Select-Object -First 1).ToString().Trim()
}

function Initialize-VersionInfo {
    # Match GNU date +%Y-%m-%dT%T%z (offset without colon)
    $offset = [System.TimeZoneInfo]::Local.GetUtcOffset((Get-Date))
    $sign = if ($offset -ge [TimeSpan]::Zero) { "+" } else { "-" }
    $script:BuildTime = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss") + `
        ("{0}{1:00}{2:00}" -f $sign, [Math]::Abs($offset.Hours), [Math]::Abs($offset.Minutes))

    $script:GitTag = Get-GitOutput describe --tags --always
    $script:GitHash = Get-GitOutput rev-parse --short HEAD
    if ([string]::IsNullOrWhiteSpace($Version)) {
        $dateSuffix = Get-Date -Format "yy.MM.dd"
        $script:Version = "$($script:GitTag)-$dateSuffix"
    }
    else {
        $script:Version = $Version
    }

    $script:BuildFlag = "-X '$Module/version.buildTime=$($script:BuildTime)' " +
    "-X '$Module/version.gitTag=$($script:GitTag)' " +
    "-X '$Module/version.gitHash=$($script:GitHash)' " +
    "-X '$Module/version.version=$($script:Version)'"

    $script:ServerPkgDir = Join-Path $BuildDir "$Project-server"
    $script:ServerPkgName = "$($script:Version)-server.tar.gz"
    $script:ProbePkgDir = Join-Path $BuildDir "$Project-probe"
    $script:ProbePkgName = "$($script:Version)-probe.tar.gz"
    $script:ProbeWindowsPkgDir = Join-Path $BuildDir "$Project-probe-windows"
    $script:ProbeWindowsPkgName = "$($script:Version)-probe-windows.zip"
}

function Assert-Command {
    param(
        [string]$Name,
        [string]$Hint
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "required command '$Name' not found. $Hint"
    }
}

function Ensure-BuildDir {
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
}

function Get-BinSuffix {
    param([string]$OS)
    if ($OS -eq "windows") { return ".exe" }
    return ""
}

function Invoke-GoBuild {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OutputName,

        [Parameter(Mandatory = $true)]
        [string]$Source,

        [string]$OS = $GoOS
    )
    Ensure-BuildDir
    $suffix = Get-BinSuffix -OS $OS
    $outPath = Join-Path $BuildDir ($OutputName + $suffix)

    $env:CGO_ENABLED = "0"
    $env:GOOS = $OS
    $env:GOARCH = "amd64"
    try {
        & go build `
            -ldflags $script:BuildFlag `
            "-gcflags=all=-trimpath=$RootDir" `
            "-asmflags=all=-trimpath=$RootDir" `
            -o $outPath `
            $Source
        if ($LASTEXITCODE -ne 0) {
            throw "go build failed for $Source -> $outPath"
        }
    }
    finally {
        Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
        Remove-Item Env:GOOS -ErrorAction SilentlyContinue
        Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
    }
    Write-Host "built $outPath"
}

function Invoke-ServiceBuild {
    param(
        [string]$Service,
        [switch]$SkipProto
    )
    if (-not $SkipProto) {
        Ensure-ProtoReady
    }
    Invoke-GoBuild -OutputName ($BinPrefix + $Service) -Source "cmd/$Service/main.go"
}

function Test-ProtoToolsAvailable {
    return (Get-Command $Protoc -ErrorAction SilentlyContinue) -and `
        (Get-Command "goimports" -ErrorAction SilentlyContinue)
}

function Invoke-ProtocGenerate {
    New-Item -ItemType Directory -Force -Path $GenDir | Out-Null
    $protoFiles = Get-ChildItem -Path $ProtoDir -Filter "*.proto" -File -ErrorAction SilentlyContinue
    if (-not $protoFiles) {
        throw "no .proto files found under $ProtoDir"
    }

    foreach ($pf in $protoFiles) {
        & $Protoc `
            --go_out=$GenDir --go_opt=paths=source_relative `
            --go-grpc_out=$GenDir --go-grpc_opt=paths=source_relative `
            -I$ProtoDir `
            $pf.FullName
        if ($LASTEXITCODE -ne 0) {
            throw "protoc failed for $($pf.Name)"
        }
    }

    $genGo = @(Get-ChildItem -Path $GenDir -Filter "*.go" -File -ErrorAction SilentlyContinue)
    if ($genGo.Count -gt 0) {
        & goimports -w ($genGo.FullName)
        if ($LASTEXITCODE -ne 0) {
            throw "goimports failed on $GenDir"
        }
    }
}

function Invoke-TargetProto {
    Assert-Command -Name $Protoc -Hint "Install protobuf compiler and ensure it is on PATH."
    Assert-Command -Name "goimports" -Hint "Install with: go install golang.org/x/tools/cmd/goimports@latest"
    Invoke-ProtocGenerate
}

# Like Make's proto prerequisite: regenerate when tools exist; otherwise reuse committed generated code.
function Ensure-ProtoReady {
    if (Test-ProtoToolsAvailable) {
        Invoke-ProtocGenerate
        return
    }
    $genGo = @(Get-ChildItem -Path $GenDir -Filter "*.go" -File -ErrorAction SilentlyContinue)
    if ($genGo.Count -eq 0) {
        throw "protobuf tools missing and no generated Go files under $GenDir. Install protoc/goimports, or run: .\build.ps1 proto"
    }
    Write-Warning "protoc/goimports not found; reusing existing generated files in $GenDir"
}

function Invoke-TargetAdmin { param([switch]$SkipProto) Invoke-ServiceBuild -Service "admin" -SkipProto:$SkipProto }
function Invoke-TargetAnalysis { param([switch]$SkipProto) Invoke-ServiceBuild -Service "analysis" -SkipProto:$SkipProto }
function Invoke-TargetReceiver { param([switch]$SkipProto) Invoke-ServiceBuild -Service "receiver" -SkipProto:$SkipProto }
function Invoke-TargetProbe { param([switch]$SkipProto) Invoke-ServiceBuild -Service "probe" -SkipProto:$SkipProto }

function Invoke-TargetProbeWindows {
    param([switch]$SkipProto)
    if (-not $SkipProto) {
        Ensure-ProtoReady
    }
    Ensure-BuildDir
    $outPath = Join-Path $BuildDir $ProbeWindowsBin
    $env:CGO_ENABLED = "0"
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"
    try {
        & go build `
            -ldflags $script:BuildFlag `
            "-gcflags=all=-trimpath=$RootDir" `
            "-asmflags=all=-trimpath=$RootDir" `
            -o $outPath `
            "cmd/probe/main.go"
        if ($LASTEXITCODE -ne 0) {
            throw "go build failed for probe-windows"
        }
    }
    finally {
        Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
        Remove-Item Env:GOOS -ErrorAction SilentlyContinue
        Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
    }
    Write-Host "built $outPath"
}

function Invoke-TargetCheckWindows {
    $env:CGO_ENABLED = "0"
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"
    try {
        & go build ./...
        if ($LASTEXITCODE -ne 0) {
            throw "check-windows failed: go build ./..."
        }
    }
    finally {
        Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
        Remove-Item Env:GOOS -ErrorAction SilentlyContinue
        Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
    }
    Write-Host "check-windows OK"
}

function Invoke-TargetDoc {
    Ensure-BuildDir
    Assert-Command -Name "go" -Hint "Install Go and ensure it is on PATH."
    $env:GOBIN = (Join-Path $RootDir $BuildDir)
    try {
        & go install github.com/swaggo/swag/v2/cmd/swag@latest
        if ($LASTEXITCODE -ne 0) {
            throw "go install swag failed"
        }
    }
    finally {
        Remove-Item Env:GOBIN -ErrorAction SilentlyContinue
    }

    $swag = Join-Path $BuildDir "swag.exe"
    if (-not (Test-Path $swag)) {
        $swag = Join-Path $BuildDir "swag"
    }
    if (-not (Test-Path $swag)) {
        throw "swag binary not found under $BuildDir after install"
    }

    & $swag fmt
    if ($LASTEXITCODE -ne 0) { throw "swag fmt failed" }
    & $swag init -g cmd/admin/main.go --parseDependency --parseDepth 3
    if ($LASTEXITCODE -ne 0) { throw "swag init failed" }
}

function Invoke-TargetCluster {
    Invoke-GoBuild -OutputName ($BinPrefix + "cluster") -Source "./tools/cmd/cluster"
}

function Invoke-TargetBwmgr {
    Invoke-GoBuild -OutputName ($BinPrefix + "bwmgr") -Source "./tools/cmd/bwmgr"
}

function Invoke-TargetToolkits {
    Invoke-TargetCluster
    Invoke-TargetBwmgr
}

function Invoke-TargetAll {
    Ensure-ProtoReady
    Invoke-TargetAdmin -SkipProto
    Invoke-TargetAnalysis -SkipProto
    Invoke-TargetReceiver -SkipProto
    Invoke-TargetProbe -SkipProto
    Invoke-TargetToolkits
}

function Invoke-TargetFormat {
    Assert-Command -Name "goimports" -Hint "Install with: go install golang.org/x/tools/cmd/goimports@latest"
    & goimports -w .
    if ($LASTEXITCODE -ne 0) { throw "goimports failed" }

    Get-ChildItem -Path $RootDir -Filter "go.mod" -Recurse -File | ForEach-Object {
        Push-Location $_.DirectoryName
        try {
            & go mod tidy
            if ($LASTEXITCODE -ne 0) {
                throw "go mod tidy failed in $($_.DirectoryName)"
            }
        }
        finally {
            Pop-Location
        }
    }
}

function Invoke-TargetTest {
    & go test -v -race -cover ./...
    if ($LASTEXITCODE -ne 0) { throw "go test failed" }
}

function Copy-ItemsTo {
    param(
        [string[]]$Sources,
        [string]$Destination
    )
    foreach ($src in $Sources) {
        if (-not (Test-Path $src)) {
            throw "missing required file: $src"
        }
        Copy-Item -Path $src -Destination $Destination -Force
    }
}

function New-TarGzPackage {
    param(
        [string]$ArchiveName,
        [string]$FolderName
    )
    Assert-Command -Name "tar" -Hint "tar is required (available on modern Windows)."
    $archivePath = Join-Path $BuildDir $ArchiveName
    if (Test-Path $archivePath) {
        Remove-Item -Force $archivePath
    }
    Push-Location $BuildDir
    try {
        & tar -czf $ArchiveName $FolderName
        if ($LASTEXITCODE -ne 0) {
            throw "tar failed creating $ArchiveName"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-TargetPackageServer {
    Ensure-ProtoReady
    Invoke-TargetAdmin -SkipProto
    Invoke-TargetAnalysis -SkipProto
    Invoke-TargetReceiver -SkipProto
    Invoke-TargetToolkits

    Write-Host "Packaging $($script:ServerPkgName)..."
    if (Test-Path $script:ServerPkgDir) {
        Remove-Item -Recurse -Force $script:ServerPkgDir
    }

    $suffix = Get-BinSuffix -OS $GoOS
    $dirs = @(
        (Join-Path $script:ServerPkgDir "bin"),
        (Join-Path $script:ServerPkgDir "etc"),
        (Join-Path $script:ServerPkgDir "logs"),
        (Join-Path $script:ServerPkgDir "pids"),
        (Join-Path $script:ServerPkgDir "toolkits"),
        (Join-Path $script:ServerPkgDir "lib"),
        (Join-Path $script:ServerPkgDir "etc\templates\snippets")
    )
    foreach ($d in $dirs) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }

    foreach ($bin in $ServerBins) {
        $src = Join-Path $BuildDir ($bin + $suffix)
        if (-not (Test-Path $src)) {
            throw "missing binary: $src"
        }
        Copy-Item $src (Join-Path $script:ServerPkgDir "bin") -Force
    }
    foreach ($bin in $ServerToolkits) {
        $src = Join-Path $BuildDir ($bin + $suffix)
        if (-not (Test-Path $src)) {
            throw "missing toolkit binary: $src"
        }
        Copy-Item $src (Join-Path $script:ServerPkgDir "toolkits") -Force
    }

    Copy-ItemsTo -Sources $ServerScripts -Destination $script:ServerPkgDir
    Copy-Item $GuardUtilsLib (Join-Path $script:ServerPkgDir "lib") -Force

    foreach ($t in $ServerTemplates) {
        Copy-Item (Join-Path "etc\templates" $t) (Join-Path $script:ServerPkgDir "etc\templates") -Force
    }
    foreach ($s in $ServerSnippets) {
        Copy-Item (Join-Path "etc\templates\snippets" $s) (Join-Path $script:ServerPkgDir "etc\templates\snippets") -Force
    }
    Copy-Item "etc\dbha-v2.server.rc.example" (Join-Path $script:ServerPkgDir "etc") -Force
    foreach ($c in $ServerToolkitConfigs) {
        Copy-Item (Join-Path "etc" $c) (Join-Path $script:ServerPkgDir "etc") -Force
    }

    $setupPath = Join-Path $script:ServerPkgDir "setup.sh"
    $setupContent = (Get-Content -Path $setupPath -Raw) -replace "__VERSION__", $script:Version
    Set-Content -Path $setupPath -Value $setupContent -NoNewline

    New-TarGzPackage -ArchiveName $script:ServerPkgName -FolderName "$Project-server"
    Remove-Item -Recurse -Force $script:ServerPkgDir
    Write-Host "Package created: $(Join-Path $BuildDir $script:ServerPkgName)"
}

function Invoke-TargetPackageProbe {
    Ensure-ProtoReady
    Invoke-TargetProbe -SkipProto

    Write-Host "Packaging $($script:ProbePkgName)..."
    if (Test-Path $script:ProbePkgDir) {
        Remove-Item -Recurse -Force $script:ProbePkgDir
    }

    $suffix = Get-BinSuffix -OS $GoOS
    $dirs = @(
        (Join-Path $script:ProbePkgDir "bin"),
        (Join-Path $script:ProbePkgDir "etc"),
        (Join-Path $script:ProbePkgDir "logs"),
        (Join-Path $script:ProbePkgDir "pids"),
        (Join-Path $script:ProbePkgDir "lib"),
        (Join-Path $script:ProbePkgDir "etc\templates\snippets")
    )
    foreach ($d in $dirs) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }

    foreach ($bin in $ProbeBins) {
        $src = Join-Path $BuildDir ($bin + $suffix)
        if (-not (Test-Path $src)) {
            throw "missing binary: $src"
        }
        Copy-Item $src (Join-Path $script:ProbePkgDir "bin") -Force
    }

    Copy-ItemsTo -Sources $ProbeScripts -Destination $script:ProbePkgDir
    Copy-Item $GuardUtilsLib (Join-Path $script:ProbePkgDir "lib") -Force

    foreach ($t in $ProbeTemplates) {
        Copy-Item (Join-Path "etc\templates" $t) (Join-Path $script:ProbePkgDir "etc\templates") -Force
    }
    foreach ($s in $ProbeSnippets) {
        Copy-Item (Join-Path "etc\templates\snippets" $s) (Join-Path $script:ProbePkgDir "etc\templates\snippets") -Force
    }
    Copy-Item "etc\dbha-v2.probe.rc.example" (Join-Path $script:ProbePkgDir "etc") -Force

    New-TarGzPackage -ArchiveName $script:ProbePkgName -FolderName "$Project-probe"
    Remove-Item -Recurse -Force $script:ProbePkgDir
    Write-Host "Package created: $(Join-Path $BuildDir $script:ProbePkgName)"
}

function Invoke-TargetPackageProbeWindows {
    Ensure-ProtoReady
    Invoke-TargetProbeWindows -SkipProto

    Write-Host "Packaging $($script:ProbeWindowsPkgName)..."
    if (Test-Path $script:ProbeWindowsPkgDir) {
        Remove-Item -Recurse -Force $script:ProbeWindowsPkgDir
    }

    $dirs = @(
        (Join-Path $script:ProbeWindowsPkgDir "bin"),
        (Join-Path $script:ProbeWindowsPkgDir "etc"),
        (Join-Path $script:ProbeWindowsPkgDir "logs"),
        (Join-Path $script:ProbeWindowsPkgDir "pids"),
        (Join-Path $script:ProbeWindowsPkgDir "lib"),
        (Join-Path $script:ProbeWindowsPkgDir "etc\templates\snippets")
    )
    foreach ($d in $dirs) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }

    $probeExe = Join-Path $BuildDir $ProbeWindowsBin
    if (-not (Test-Path $probeExe)) {
        throw "missing binary: $probeExe"
    }
    Copy-Item $probeExe (Join-Path $script:ProbeWindowsPkgDir "bin") -Force
    Copy-ItemsTo -Sources $ProbeWindowsScripts -Destination $script:ProbeWindowsPkgDir
    Copy-ItemsTo -Sources $ProbeWindowsLibs -Destination (Join-Path $script:ProbeWindowsPkgDir "lib")

    foreach ($t in $ProbeTemplates) {
        Copy-Item (Join-Path "etc\templates" $t) (Join-Path $script:ProbeWindowsPkgDir "etc\templates") -Force
    }
    foreach ($s in $ProbeSnippets) {
        Copy-Item (Join-Path "etc\templates\snippets" $s) (Join-Path $script:ProbeWindowsPkgDir "etc\templates\snippets") -Force
    }
    Copy-Item "etc\dbha-v2.probe.rc.example" (Join-Path $script:ProbeWindowsPkgDir "etc") -Force

    $zipPath = Join-Path $BuildDir $script:ProbeWindowsPkgName
    if (Test-Path $zipPath) {
        Remove-Item -Force $zipPath
    }
    # Compress-Archive from inside build/ so the archive root is dbha-v2-probe-windows/
    $folderToZip = $script:ProbeWindowsPkgDir
    Compress-Archive -Path $folderToZip -DestinationPath $zipPath -Force

    Remove-Item -Recurse -Force $script:ProbeWindowsPkgDir
    Write-Host "Package created: $zipPath"
}

function Invoke-TargetPackage {
    Invoke-TargetPackageServer
    Invoke-TargetPackageProbe
    Invoke-TargetPackageProbeWindows
}

function Invoke-TargetClean {
    Get-ChildItem -Path $GenDir -Filter "*.go" -File -ErrorAction SilentlyContinue |
        Remove-Item -Force
    if (Test-Path $BuildDir) {
        Get-ChildItem -Path $BuildDir -Force -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }
    Write-Host "cleaned $GenDir/*.go and $BuildDir/*"
}

function Invoke-TargetHelp {
    @"
Usage: .\build.ps1 [target] [-GoOS linux|windows|darwin] [-Version <ver>]

Targets:
  all        - Build all services and toolkits (default)
  proto      - Generate protobuf files
  admin      - Build admin service
  analysis   - Build analysis service
  receiver   - Build receiver service
  probe      - Build probe service
  probe-windows  - Build Windows probe binary (dbha-probe.exe)
  check-windows  - Cross-compile the whole module for Windows (build gate)
  toolkits   - Build toolkit binaries (cluster, bwmgr)
  cluster    - Build cluster toolkit (dbha-cluster)
  bwmgr      - Build black-white list manager (dbha-bwmgr)
  package    - Build and create both server and probe release packages
  package-server - Create server release package (services + toolkits + etc templates)
  package-probe  - Create probe release package ($($script:Version)-probe.tar.gz)
  package-probe-windows - Create Windows probe release package ($($script:Version)-probe-windows.zip)
  format     - Format code and tidy modules
  test       - Run tests
  clean      - Clean build artifacts
  help       - Show this help message
"@ | Write-Host
}

# --- main ---
Assert-Command -Name "go" -Hint "Install Go and ensure it is on PATH."
Initialize-VersionInfo

switch ($Target.ToLowerInvariant()) {
    "all" { Invoke-TargetAll }
    "proto" { Invoke-TargetProto }
    "admin" { Invoke-TargetAdmin }
    "analysis" { Invoke-TargetAnalysis }
    "receiver" { Invoke-TargetReceiver }
    "probe" { Invoke-TargetProbe }
    "probe-windows" { Invoke-TargetProbeWindows }
    "check-windows" { Invoke-TargetCheckWindows }
    "doc" { Invoke-TargetDoc }
    "toolkits" { Invoke-TargetToolkits }
    "cluster" { Invoke-TargetCluster }
    "bwmgr" { Invoke-TargetBwmgr }
    "format" { Invoke-TargetFormat }
    "test" { Invoke-TargetTest }
    "package" { Invoke-TargetPackage }
    "package-server" { Invoke-TargetPackageServer }
    "package-probe" { Invoke-TargetPackageProbe }
    "package-probe-windows" { Invoke-TargetPackageProbeWindows }
    "clean" { Invoke-TargetClean }
    "help" { Invoke-TargetHelp }
    default {
        throw "unknown target '$Target'. Run: .\build.ps1 help"
    }
}
