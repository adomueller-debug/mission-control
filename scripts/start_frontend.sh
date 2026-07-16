#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="/Users/adrianmuller/AI-Platform"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$PROJECT_ROOT/frontend"
exec /opt/homebrew/bin/npm run dev -- --host 127.0.0.1 --port 5173
