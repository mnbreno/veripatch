<#
.SYNOPSIS
    Creates a desktop shortcut for the VeriPatch GUI.

.DESCRIPTION
    This script creates a .lnk file on the user's desktop that launches the VeriPatch GUI.
    It automatically determines the path to main.lua and attempts to find a Lua executable.
    If VERIPATCH_PYTHON environment variable is set, it will be used as the Python executable
    for the backend.

.NOTES
    Requires PowerShell 5.1 or later.
#>

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Join-Path $ScriptPath ".."
$GuiPath = Join-Path $ProjectRoot "gui\main.lua"
$BackendPath = Join-Path $ProjectRoot "backend"

$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "VeriPatch.lnk"
$WshShell = New-Object -ComObject WScript.Shell

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

# Attempt to find lua.exe
$LuaExe = Get-Command lua.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $LuaExe) {
    Write-Error "Lua executable (lua.exe) not found in PATH. Please install Lua and wxLua."
    exit 1
}

# Set the target path for the shortcut
$Shortcut.TargetPath = $LuaExe
$Shortcut.Arguments = "`"$GuiPath`""

# Set working directory to the GUI folder
$Shortcut.WorkingDirectory = (Split-Path $GuiPath)

# Set icon path (optional)
# You might want to create a proper icon file in the future
# $Shortcut.IconLocation = "path	o\your\icon.ico"

# Save the shortcut
$Shortcut.Save()

Write-Host "VeriPatch shortcut created at $ShortcutPath"

# Optional: Set VERIPATCH_PYTHON environment variable if it's not set
# This ensures the correct Python is used by the backend
if (-not $env:VERIPATCH_PYTHON) {
    # Attempt to find python.exe
    $PythonExe = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    if ($PythonExe) {
        Write-Host "Setting VERIPATCH_PYTHON environment variable to $PythonExe"
        $env:VERIPATCH_PYTHON = $PythonExe
        # For persistent setting, you might use:
        # [System.Environment]::SetEnvironmentVariable("VERIPATCH_PYTHON", $PythonExe, "User")
    } else {
        Write-Warning "Python executable (python.exe) not found in PATH. Please ensure Python is installed and configured for the VeriPatch backend."
    }
}
