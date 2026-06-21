<#
.SYNOPSIS
    Creates a desktop shortcut for the VeriPatch GUI.

.DESCRIPTION
    Creates VeriPatch.lnk on the desktop. The shortcut launches start-gui-hidden.vbs,
    which starts the backend headlessly and opens the VeriPatch GUI window.
#>

$ErrorActionPreference = "Stop"

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = (Resolve-Path (Join-Path $ScriptPath "..")).Path
$GuiDir = Join-Path $ProjectRoot "gui"
$LauncherVbs = Join-Path $ScriptPath "start-gui-hidden.vbs"
$IconPath = Join-Path $GuiDir "assets\veripatch.ico"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "VeriPatch.lnk"

$PythonExe = $env:VERIPATCH_PYTHON
if (-not $PythonExe) {
    $PythonCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    } else {
        $Fallback = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
        if (Test-Path $Fallback) {
            $PythonExe = $Fallback
        }
    }
}

if (-not (Test-Path $LauncherVbs)) {
    Write-Error "Launcher script not found: $LauncherVbs"
    exit 1
}

if (-not (Test-Path $IconPath)) {
    $BuildIcon = Join-Path $ScriptPath "build-icon.py"
    if ((Test-Path $BuildIcon) -and $PythonExe) {
        Write-Host "Building icon at $IconPath ..."
        & $PythonExe $BuildIcon
    }
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = (Get-Command wscript.exe).Source
$Shortcut.Arguments = "`"$LauncherVbs`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "VeriPatch - Official Source Updates"

if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}

$Shortcut.Save()

Write-Host "VeriPatch shortcut created at $ShortcutPath"
Write-Host "Shortcut launches via: $LauncherVbs"
