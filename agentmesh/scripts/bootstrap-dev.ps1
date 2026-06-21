# AgentMesh bootstrap for Cursor multi-terminal development
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageDir = Split-Path -Parent $ScriptDir
Set-Location $PackageDir

Write-Host "Bootstrapping AgentMesh..." -ForegroundColor Cyan
python -m agentmesh.cli bootstrap
exit $LASTEXITCODE
