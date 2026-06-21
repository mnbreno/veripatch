#Requires -Version 5.1
<#
.SYNOPSIS
    Builds a VeriPatch Windows installer using Inno Setup.

.DESCRIPTION
    Stages backend (embedded Python), GUI, and launcher scripts, then compiles
    VeriPatch-{version}-Setup.exe with Inno Setup 6 (iscc.exe).

.PARAMETER Version
    Override version (default: read from backend/pyproject.toml).

.PARAMETER WxLuaDir
    Optional path to wxLua bundle (e.g. tools/wxlua542) copied into the installer.
#>
param(
    [string]$Version = "",
    [string]$WxLuaDir = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$GuiDir = Join-Path $ProjectRoot "gui"
$PackagingDir = Join-Path $ProjectRoot "packaging\windows"
$ArtifactsDir = Join-Path $ProjectRoot "artifacts"
$StagingDir = Join-Path $PackagingDir "staging"

if (-not $Version) {
    $Version = & python -c "import pathlib,re; t=pathlib.Path(r'$BackendDir/pyproject.toml').read_text(); m=re.search(r'version\s*=\s*\"([^\"]+)\"', t); print(m.group(1))"
}

Write-Host "Building VeriPatch $Version Windows installer..." -ForegroundColor Cyan

$Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $Iscc) {
    $DefaultIscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $DefaultIscc) {
        $Iscc = @{ Source = $DefaultIscc }
    } else {
        Write-Error "Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php and add iscc.exe to PATH."
    }
}

if (Test-Path $StagingDir) {
    Remove-Item -Recurse -Force $StagingDir
}
New-Item -ItemType Directory -Path $StagingDir | Out-Null
New-Item -ItemType Directory -Path $ArtifactsDir -Force | Out-Null

# Embedded Python 3.12 amd64
$PythonVersion = "3.12.7"
$EmbedZip = "python-$PythonVersion-embed-amd64.zip"
$EmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/$EmbedZip"
$EmbedCache = Join-Path $PackagingDir "cache"
New-Item -ItemType Directory -Path $EmbedCache -Force | Out-Null
$EmbedPath = Join-Path $EmbedCache $EmbedZip

if (-not (Test-Path $EmbedPath)) {
    Write-Host "Downloading embedded Python $PythonVersion..."
    Invoke-WebRequest -Uri $EmbedUrl -OutFile $EmbedPath
}

$PythonDir = Join-Path $StagingDir "python"
Expand-Archive -Path $EmbedPath -DestinationPath $PythonDir -Force

# Enable pip in embeddable distro
$PthFile = Get-ChildItem "$PythonDir\python*._pth" | Select-Object -First 1
if ($PthFile) {
    $pth = Get-Content $PthFile.FullName
    $pth = $pth | ForEach-Object { if ($_ -eq "#import site") { "import site" } else { $_ } }
    Set-Content -Path $PthFile.FullName -Value $pth
}

$GetPip = Join-Path $EmbedCache "get-pip.py"
if (-not (Test-Path $GetPip)) {
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip
}

$PythonExe = Join-Path $PythonDir "python.exe"
& $PythonExe $GetPip --no-warn-script-location | Out-Null
& $PythonExe -m pip install --no-warn-script-location "$BackendDir" | Out-Null

# Application files
$AppDir = Join-Path $StagingDir "app"
New-Item -ItemType Directory -Path $AppDir | Out-Null
Copy-Item -Recurse -Force $GuiDir (Join-Path $AppDir "gui")
Copy-Item -Recurse -Force (Join-Path $BackendDir "veripatch") (Join-Path $AppDir "backend\veripatch")
Copy-Item -Force (Join-Path $BackendDir "pyproject.toml") (Join-Path $AppDir "backend\pyproject.toml")

$ScriptsDest = Join-Path $AppDir "scripts"
New-Item -ItemType Directory -Path $ScriptsDest | Out-Null
foreach ($name in @("start-gui.ps1", "start-backend.ps1", "start-gui-hidden.vbs", "create-shortcut.ps1")) {
    Copy-Item -Force (Join-Path $ScriptDir $name) (Join-Path $ScriptsDest $name)
}

if ($WxLuaDir -and (Test-Path $WxLuaDir)) {
    Copy-Item -Recurse -Force $WxLuaDir (Join-Path $AppDir "tools\wxlua542")
}

# Launcher wrapper for installed layout
@'
$InstallRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$env:VERIPATCH_PYTHON = Join-Path $InstallRoot "python\pythonw.exe"
$env:VERIPATCH_LUA = Join-Path $InstallRoot "app\tools\wxlua542\bin\64bit\wxLua.exe"
& (Join-Path $InstallRoot "app\scripts\start-gui.ps1")
'@ | Set-Content -Path (Join-Path $StagingDir "VeriPatch.ps1") -Encoding UTF8

Write-Host "Compiling installer..."
& $Iscc.Source `
    "/DAppVersion=$Version" `
    "/DStagingDir=$StagingDir" `
    (Join-Path $PackagingDir "VeriPatch.iss")

$OutputExe = Join-Path $ArtifactsDir "VeriPatch-$Version-Setup.exe"
if (-not (Test-Path $OutputExe)) {
    Write-Error "Installer build failed; expected $OutputExe"
}
Write-Host "Built $OutputExe" -ForegroundColor Green
