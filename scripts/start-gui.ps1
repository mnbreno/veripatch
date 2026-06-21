<#
.SYNOPSIS
    Starts the VeriPatch backend and GUI.

.DESCRIPTION
    Launches a persistent TCP backend (headless) and the wxLua GUI.
    The backend runs without a console; the GUI window is shown normally.
    Set VERIPATCH_PYTHON to override Python.
#>

$ErrorActionPreference = "Stop"

$LaunchLog = Join-Path $env:TEMP "veripatch-launch.log"

function Write-LaunchLog {
    param([string]$Message)
    Add-Content -Path $LaunchLog -Value ("[{0}] {1}" -f (Get-Date -Format "s"), $Message)
}

try {
    $ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $ProjectRoot = (Resolve-Path (Join-Path $ScriptPath "..")).Path
    $BackendDir = Join-Path $ProjectRoot "backend"
    $GuiDir = Join-Path $ProjectRoot "gui"
    $StartBackendScript = Join-Path $ScriptPath "start-backend.ps1"

    $PythonExe = $env:VERIPATCH_PYTHON
    if (-not $PythonExe) {
        $PythonCmd = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($PythonCmd) {
            $PythonExe = $PythonCmd.Source
        } else {
            $Fallback = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
            if (Test-Path $Fallback) {
                $PythonExe = $Fallback
            } else {
                throw "Python not found. Set VERIPATCH_PYTHON or install Python 3.11+."
            }
        }
    }

    $LuaExe = $env:VERIPATCH_LUA
    if (-not $LuaExe) {
        $BundledDir = Join-Path $ProjectRoot "tools\wxlua542\bin\64bit"
        $BundledWxLua = Join-Path $BundledDir "wxLua.exe"
        $BundledLua = Join-Path $BundledDir "lua.exe"
        if (Test-Path $BundledWxLua) {
            $LuaExe = $BundledWxLua
        } elseif (Test-Path $BundledLua) {
            $LuaExe = $BundledLua
        } else {
            $LuaCmd = Get-Command wxLua.exe -ErrorAction SilentlyContinue
            if ($LuaCmd) {
                $LuaExe = $LuaCmd.Source
            } else {
                $LuaCmd = Get-Command lua.exe -ErrorAction SilentlyContinue
                if ($LuaCmd) {
                    $LuaExe = $LuaCmd.Source
                } else {
                    throw "Lua/wxLua not found. Install wxLua or set VERIPATCH_LUA."
                }
            }
        }
    }

    $LuaBin = Split-Path -Parent $LuaExe
    if ($LuaBin -match "wxlua542\\bin\\64bit$") {
        $env:PATH = "$LuaBin;$env:PATH"
    }
    $LuarocksShare = Join-Path $env:APPDATA "luarocks\share\lua\5.4"
    if (Test-Path $LuarocksShare) {
        $env:LUA_PATH = "$LuarocksShare\?.lua;$LuarocksShare\?\init.lua;$env:LUA_PATH"
    }

    $Port = $env:VERIPATCH_IPC_PORT
    if (-not $Port) {
        $Port = "8765"
    }

    if (-not $env:VERIPATCH_SKIP_BACKEND) {
        if ($env:VERIPATCH_KEEP_BACKEND -ne "1") {
            Start-Process `
                -FilePath "powershell.exe" `
                -ArgumentList @(
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-WindowStyle", "Hidden",
                    "-File", $StartBackendScript,
                    "-Port", $Port,
                    "-ProjectRoot", $ProjectRoot,
                    "-PythonExe", $PythonExe,
                    "-Restart"
                ) `
                -WindowStyle Hidden | Out-Null
            Start-Sleep -Seconds 1
        } else {
            $BackendRunning = $false
            try {
                $BackendRunning = (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded
            } catch {
                $BackendRunning = $false
            }

            if (-not $BackendRunning) {
                & $StartBackendScript -Port $Port -ProjectRoot $ProjectRoot -PythonExe $PythonExe
                Start-Sleep -Seconds 1
            }
        }
    }

    $env:VERIPATCH_PYTHON = $PythonExe
    $env:VERIPATCH_IPC_PORT = $Port
    $env:VERIPATCH_BACKEND_MANAGED = "1"
    Write-LaunchLog "Starting GUI: $LuaExe in $GuiDir"

    $GuiProc = Start-Process `
        -FilePath $LuaExe `
        -ArgumentList @("main.lua") `
        -WorkingDirectory $GuiDir `
        -PassThru

    Start-Sleep -Milliseconds 800
    if ($GuiProc.HasExited) {
        throw "GUI exited immediately with code $($GuiProc.ExitCode). See wxLua output above or $LaunchLog"
    }

    Write-LaunchLog "GUI started (pid $($GuiProc.Id))"
} catch {
    Write-LaunchLog $_.Exception.Message
    exit 1
}
