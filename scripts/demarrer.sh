#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then cp .env.example .env; fi
ollama pull qwen3-embedding:0.6b
ollama pull gemma4:e4b
docker compose up -d --build --wait
echo 'Atelier est prêt : http://localhost:3000'
