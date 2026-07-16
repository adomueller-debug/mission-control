#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="/Users/adrianmuller/AI-Platform"
DOCKER="/opt/homebrew/bin/docker"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if ! "$DOCKER" info >/dev/null 2>&1; then
  /usr/bin/open -gja Docker
fi

for _ in {1..60}; do
  if "$DOCKER" info >/dev/null 2>&1; then
    cd "$PROJECT_ROOT"
    exec "$DOCKER" compose up -d --no-deps n8n
  fi
  sleep 2
done

echo "Docker wurde innerhalb von 120 Sekunden nicht erreichbar." >&2
exit 1
