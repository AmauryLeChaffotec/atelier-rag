$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Ouvrez Docker Desktop puis relancez ce script.' }
ollama pull qwen3-embedding:0.6b
if ($LASTEXITCODE -ne 0) { throw 'Installez ou démarrez Ollama, puis relancez ce script.' }
ollama pull gemma4:e4b
if ($LASTEXITCODE -ne 0) { throw 'Le téléchargement de Gemma a échoué.' }
docker compose up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw 'Le démarrage a échoué. Consultez docker compose logs.' }
Write-Host 'Atelier est prêt : http://localhost:3000'
