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
    [string]$WxLuaDir = "",
    [switch]$PortableZipOnly
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$GuiDir = Join-Path $ProjectRoot "gui"
$PackagingDir = Join-Path $ProjectRoot "packaging\windows"
$ArtifactsDir = Join-Path $ProjectRoot "artifacts"
$StagingDir = Join-Path $PackagingDir "staging"
$UseSfxFallback = $false

if (-not $Version) {
    $pyproject = Get-Content (Join-Path $BackendDir "pyproject.toml") -Raw
    if ($pyproject -match 'version\s*=\s*"([^"]+)"') {
        $Version = $Matches[1]
    } else {
        throw "Could not read version from backend/pyproject.toml"
    }
}

Write-Host "Building VeriPatch $Version Windows installer..." -ForegroundColor Cyan

if (-not $PortableZipOnly) {
    $Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if (-not $Iscc) {
        $IsccCandidates = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
        )
        foreach ($candidate in $IsccCandidates) {
            if (Test-Path $candidate) {
                $Iscc = @{ Source = $candidate }
                break
            }
        }
    }
    $UseSfxFallback = -not $Iscc
    if ($UseSfxFallback) {
        Write-Warning "Inno Setup 6 not found; building self-extracting installer (7-Zip SFX) instead."
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
& $PythonExe -m pip install --no-warn-script-location --upgrade pip setuptools wheel | Out-Null
& $PythonExe -m pip install --no-warn-script-location "$BackendDir" | Out-Null

# Application files
$AppDir = Join-Path $StagingDir "app"
New-Item -ItemType Directory -Path $AppDir | Out-Null
Copy-Item -Recurse -Force $GuiDir (Join-Path $AppDir "gui")
Copy-Item -Recurse -Force (Join-Path $BackendDir "veripatch") (Join-Path $AppDir "backend\veripatch")
Copy-Item -Force (Join-Path $BackendDir "pyproject.toml") (Join-Path $AppDir "backend\pyproject.toml")

$ScriptsDest = Join-Path $AppDir "scripts"
New-Item -ItemType Directory -Path $ScriptsDest | Out-Null
foreach ($name in @("start-gui.ps1", "start-backend.ps1", "start-backend-hidden.vbs", "start-gui-hidden.vbs", "create-shortcut.ps1")) {
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

if ($PortableZipOnly) {
    $PortableZip = Join-Path $ArtifactsDir "VeriPatch-$Version-Windows-Portable.zip"
    if (Test-Path $PortableZip) {
        Remove-Item -Force $PortableZip
    }
    Compress-Archive -Path (Join-Path $StagingDir "*") -DestinationPath $PortableZip
    Write-Host "Built portable ZIP $PortableZip" -ForegroundColor Green
    return
}

$OutputExe = Join-Path $ArtifactsDir "VeriPatch-$Version-Setup.exe"
if (Test-Path $OutputExe) {
    Remove-Item -Force $OutputExe
}

if ($UseSfxFallback) {
    $SevenZipVersion = "2409"
    $ExtraZip = "7z$SevenZipVersion-extra.7z"
    $ExtraUrl = "https://www.7-zip.org/a/$ExtraZip"
    $ExtraCache = Join-Path $EmbedCache $ExtraZip
    if (-not (Test-Path $ExtraCache)) {
        Write-Host "Downloading 7-Zip extra tools..."
        Invoke-WebRequest -Uri $ExtraUrl -OutFile $ExtraCache
    }
    $SevenZipDir = Join-Path $PackagingDir "cache\7zip-extra"
    if (-not (Test-Path (Join-Path $SevenZipDir "7z.exe"))) {
        if (Test-Path $SevenZipDir) {
            Remove-Item -Recurse -Force $SevenZipDir
        }
        New-Item -ItemType Directory -Path $SevenZipDir -Force | Out-Null
        $SevenZipExe = Join-Path $EmbedCache "7zr.exe"
        if (-not (Test-Path $SevenZipExe)) {
            Invoke-WebRequest -Uri "https://www.7-zip.org/a/7zr.exe" -OutFile $SevenZipExe
        }
        & $SevenZipExe x $ExtraCache "-o$SevenZipDir" -y | Out-Null
    }
    $SevenZ = Join-Path $SevenZipDir "7z.exe"
    $SfxModule = Join-Path $SevenZipDir "7zSD.sfx"
    if (-not (Test-Path $SevenZ) -or -not (Test-Path $SfxModule)) {
        throw "7-Zip SFX tools missing after extract; expected $SevenZ and $SfxModule"
    }

    @"
`$ErrorActionPreference = 'Stop'
`$InstallDir = Join-Path `$env:LOCALAPPDATA 'VeriPatch'
`$SourceDir = `$PSScriptRoot
if (Test-Path `$InstallDir) {
    Remove-Item -Recurse -Force `$InstallDir
}
New-Item -ItemType Directory -Path `$InstallDir -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path `$SourceDir '*') `$InstallDir
`$Launcher = Join-Path `$InstallDir 'VeriPatch.ps1'
`$Wsh = New-Object -ComObject WScript.Shell
`$Shortcut = `$Wsh.CreateShortcut((Join-Path `$env:USERPROFILE 'Desktop\VeriPatch.lnk'))
`$Shortcut.TargetPath = 'powershell.exe'
`$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"`$Launcher`""
`$Shortcut.WorkingDirectory = `$InstallDir
`$Shortcut.Save()
Write-Host "VeriPatch $Version installed to `$InstallDir"
"@ | Set-Content -Path (Join-Path $StagingDir "install.ps1") -Encoding UTF8

    $Archive7z = Join-Path $ArtifactsDir "VeriPatch-$Version-staging.7z"
    if (Test-Path $Archive7z) {
        Remove-Item -Force $Archive7z
    }
    & $SevenZ a -t7z -mx=9 $Archive7z (Join-Path $StagingDir "*") | Out-Null

    $SfxConfig = Join-Path $PackagingDir "sfx-config.txt"
    @"
;!@Install@!UTF-8!
Title="VeriPatch $Version Setup"
BeginPrompt="Install VeriPatch $Version to %LOCALAPPDATA%\VeriPatch?"
RunProgram="powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1"
;!@InstallEnd@!
"@ | Set-Content -Path $SfxConfig -Encoding UTF8

    $SfxParts = @($SfxModule, $SfxConfig, $Archive7z)
    $Fs = [System.IO.File]::Open($OutputExe, [System.IO.FileMode]::Create)
    try {
        foreach ($part in $SfxParts) {
            $bytes = [System.IO.File]::ReadAllBytes($part)
            $Fs.Write($bytes, 0, $bytes.Length)
        }
    } finally {
        $Fs.Close()
    }
    Remove-Item -Force $Archive7z
    Write-Host "Built SFX installer $OutputExe" -ForegroundColor Green
    return
}

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
