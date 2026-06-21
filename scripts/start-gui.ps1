<#
.SYNOPSIS
    Starts the VeriPatch backend and GUI.

.DESCRIPTION
    Launches a persistent TCP backend (optional) and the wxLua GUI.
    Set VERIPATCH_PYTHON to override the Python executable.
    Set VERIPATCH_IPC_PORT to connect the GUI to an existing backend.
#>

$ErrorActionPreference = "Stop"

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = (Resolve-Path (Join-Path $ScriptPath "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$GuiDir = Join-Path $ProjectRoot "gui"

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
            Write-Error "Python not found. Set VERIPATCH_PYTHON or install Python 3.11+."
            exit 1
        }
    }
}

$LuaExe = $env:VERIPATCH_LUA
if (-not $LuaExe) {
    $BundledLua = Join-Path $ProjectRoot "tools\wxlua542\bin\64bit\lua.exe"
    if (Test-Path $BundledLua) {
        $LuaExe = $BundledLua
    } else {
        $LuaCmd = Get-Command lua.exe -ErrorAction SilentlyContinue
        if ($LuaCmd) {
            $LuaExe = $LuaCmd.Source
        } else {
            Write-Error "Lua not found. Install Lua 5.4 + wxLua or set VERIPATCH_LUA."
            exit 1
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

$PortFile = Join-Path $BackendDir ".veripatch\ipc.port"
$BackendProc = $null

if (-not $env:VERIPATCH_SKIP_BACKEND) {
    $BackendRunning = $false
    try {
        $BackendRunning = (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded
    } catch {
        $BackendRunning = $false
    }

    if (-not $BackendRunning) {
        Write-Host "Starting VeriPatch backend on 127.0.0.1:$Port ..."
        $BackendProc = Start-Process `
            -FilePath $PythonExe `
            -ArgumentList @("-m", "veripatch", "--port", $Port, "--write-port-file") `
            -WorkingDirectory $BackendDir `
            -PassThru `
            -WindowStyle Hidden
        Start-Sleep -Seconds 1
    } else {
        Write-Host "VeriPatch backend already running on 127.0.0.1:$Port"
    }
}

Write-Host "Launching VeriPatch GUI ..."
$env:VERIPATCH_PYTHON = $PythonExe
$env:VERIPATCH_IPC_PORT = $Port
$GuiProc = Start-Process `
    -FilePath $LuaExe `
    -ArgumentList @("main.lua") `
    -WorkingDirectory $GuiDir `
    -PassThru

if ($GuiProc.ExitCode -and $GuiProc.ExitCode -ne 0) {
    if ($BackendProc) {
        Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
    }
    exit $GuiProc.ExitCode
}

Write-Host "VeriPatch GUI started (PID $($GuiProc.Id))."
if ($BackendProc) {
    Write-Host "Backend PID $($BackendProc.Id) listening on port $Port."
}
