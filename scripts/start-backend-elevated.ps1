<#
.SYNOPSIS
    Starts the VeriPatch backend with administrator rights (UAC prompt).
#>
param(
    [int]$Port = 8765,
    [string]$ProjectRoot = "",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $ProjectRoot = (Resolve-Path (Join-Path $ScriptPath "..")).Path
}

$BackendScript = Join-Path $ProjectRoot "scripts\start-backend.ps1"
if (-not (Test-Path $BackendScript)) {
    Write-Error "Backend launcher not found: $BackendScript"
    exit 1
}

$argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-WindowStyle", "Hidden",
    "-File", $BackendScript,
    "-Port", $Port,
    "-ProjectRoot", $ProjectRoot,
    "-Restart"
)
if ($PythonExe) {
    $argList += @("-PythonExe", $PythonExe)
}

Start-Process `
    -FilePath "powershell.exe" `
    -Verb RunAs `
    -ArgumentList $argList `
    -WindowStyle Hidden | Out-Null
