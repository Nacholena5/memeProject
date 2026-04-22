param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "No se encontró .venv. Crealo e instalá dependencias primero."
}

if (-not (Test-Path ".env.local") -and (Test-Path ".env.local.example")) {
    Copy-Item ".env.local.example" ".env.local"
    Write-Output "Se creó .env.local desde .env.local.example"
}

$env:DATABASE_URL = "sqlite:///./meme_research.db"
$python = ".venv\Scripts\python.exe"

Start-Process -FilePath $python -ArgumentList "scripts/ops.py","scenario","full" -NoNewWindow -Wait | Out-Null

if (-not $NoBrowser) {
    Start-Process "http://$Host`:$Port"
}

& $python scripts/ops.py serve-sqlite --host $Host --port $Port
