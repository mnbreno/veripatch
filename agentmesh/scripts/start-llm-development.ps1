# Start all 5 AgentMesh dev agents backed by a local LM Studio server.
param(
    [string]$BaseUrl = "http://10.5.0.2:1234/v1",
    [string]$Model = "qwen/qwen3.5-9b",
    [string]$ApiKey = "lm-studio"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageDir = Split-Path -Parent $ScriptDir
Set-Location $PackageDir

$env:AGENTMESH_BRAIN = "llm"
$env:AGENTMESH_LLM_PROVIDER = "openai"
$env:AGENTMESH_LLM_BASE_URL = $BaseUrl
$env:AGENTMESH_LLM_MODEL = $Model
$env:AGENTMESH_LLM_API_KEY = $ApiKey
$env:AGENTMESH_LLM_TIMEOUT = "300"

Write-Host "AgentMesh LLM development" -ForegroundColor Cyan
Write-Host "  Base URL: $BaseUrl"
Write-Host "  Model:    $Model"
Write-Host ""

Write-Host "Checking LM Studio..." -ForegroundColor Yellow
$modelsUrl = $BaseUrl -replace "/v1$", "/v1/models"
try {
    $models = Invoke-RestMethod -Uri $modelsUrl -TimeoutSec 10
    $ids = $models.data | ForEach-Object { $_.id }
    if ($Model -notin $ids) {
        Write-Warning "Model '$Model' not listed. Available: $($ids -join ', ')"
    } else {
        Write-Host "Model '$Model' is available." -ForegroundColor Green
    }
} catch {
    Write-Error "Cannot reach LM Studio at $modelsUrl. Start the server and load the model first."
}

python -m agentmesh.cli bootstrap --no-install | Out-Null

$started = 0
foreach ($i in 1..5) {
    Write-Host "Starting agent $i/5..." -ForegroundColor Cyan
    $cmd = @(
        "set AGENTMESH_BRAIN=llm",
        "set AGENTMESH_LLM_PROVIDER=openai",
        "set AGENTMESH_LLM_BASE_URL=$BaseUrl",
        "set AGENTMESH_LLM_MODEL=$Model",
        "set AGENTMESH_LLM_API_KEY=$ApiKey",
        "set AGENTMESH_LLM_TIMEOUT=300",
        "python -m agentmesh.cli start development --here"
    ) -join " && "
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList @("/c", $cmd) `
        -WorkingDirectory $PackageDir `
        -WindowStyle Minimized | Out-Null
    Start-Sleep -Seconds 2
    $started++
}

Start-Sleep -Seconds 2
python -m agentmesh.cli status
Write-Host ""
Write-Host "Started $started agent processes using local LLM." -ForegroundColor Green
Write-Host "Run a workflow against these agents:"
Write-Host "  agentmesh orchestrate design-review-doc --file-bus"
