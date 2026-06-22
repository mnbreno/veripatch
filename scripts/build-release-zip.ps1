#Requires -Version 5.1
<#
.SYNOPSIS
    Creates a VeriPatch source release ZIP for GitHub Releases.
#>
param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$ArtifactsDir = Join-Path $ProjectRoot "artifacts"
$StageRoot = Join-Path $ProjectRoot "packaging\release-zip"

if (-not $Version) {
    $Version = & python -c "import pathlib,re; t=pathlib.Path(r'$BackendDir/pyproject.toml').read_text(); m=re.search(r'version\s*=\s*\"([^\"]+)\"', t); print(m.group(1))"
}

$BundleDir = Join-Path $StageRoot "VeriPatch-$Version"
if (Test-Path $StageRoot) {
    Remove-Item -Recurse -Force $StageRoot
}
New-Item -ItemType Directory -Path $BundleDir -Force | Out-Null
New-Item -ItemType Directory -Path $ArtifactsDir -Force | Out-Null

foreach ($item in @("backend", "gui", "scripts", "docs", "tests")) {
    $source = Join-Path $ProjectRoot $item
    if (Test-Path $source) {
        Copy-Item -Recurse -Force $source (Join-Path $BundleDir $item)
    }
}
foreach ($file in @("README.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md")) {
    $source = Join-Path $ProjectRoot $file
    if (Test-Path $source) {
        Copy-Item -Force $source (Join-Path $BundleDir $file)
    }
}

$ZipPath = Join-Path $ArtifactsDir "VeriPatch-$Version.zip"
if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}
Compress-Archive -Path (Join-Path $BundleDir "*") -DestinationPath $ZipPath
Remove-Item -Recurse -Force $StageRoot

Write-Host "Built $ZipPath" -ForegroundColor Green
