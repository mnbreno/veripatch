<#
.SYNOPSIS
    Starts the VeriPatch backend without a console window.
#>

param(
    [int]$Port = 8765,
    [string]$ProjectRoot = "",
    [string]$PythonExe = "",
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

function Stop-VeriPatchBackend {
    param([int]$ListenPort)
    try {
        $connections = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            if ($conn.OwningProcess) {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        # Ignore lookup failures when nothing is listening.
    }
}

if (-not $ProjectRoot) {
    $ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $ProjectRoot = (Resolve-Path (Join-Path $ScriptPath "..")).Path
}

$BackendDir = Join-Path $ProjectRoot "backend"

if (-not $PythonExe) {
    $PythonExe = $env:VERIPATCH_PYTHON
}
if (-not $PythonExe) {
    $PythonCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    } else {
        $Fallback = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
        if (Test-Path $Fallback) {
            $PythonExe = $Fallback
        }
    }
}

if (-not $PythonExe) {
    Write-Error "Python not found. Set VERIPATCH_PYTHON or install Python 3.11+."
    exit 1
}

if ($Restart -or $env:VERIPATCH_RESTART_BACKEND -eq "1") {
    Stop-VeriPatchBackend -ListenPort $Port
    Start-Sleep -Milliseconds 500
}

$PythonDir = Split-Path -Parent $PythonExe
$PythonwExe = Join-Path $PythonDir "pythonw.exe"
if (Test-Path $PythonwExe) {
    $PythonExe = $PythonwExe
}

Start-Process `
    -FilePath $PythonExe `
    -ArgumentList @("-m", "veripatch", "--port", $Port, "--write-port-file") `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden | Out-Null
