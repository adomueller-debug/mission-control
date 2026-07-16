#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="/Users/adrianmuller/AI-Platform"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$PROJECT_ROOT"
exec "$PROJECT_ROOT/.venv/bin/uvicorn" backend.app.main:app \
  --host 127.0.0.1 \
  --port 8000
