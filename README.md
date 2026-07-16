# Mission Control

Mission Control ist eine lokale, autonome AI-Agentenplattform. Der erste Referenz-Workflow analysiert Softwareaufgaben, erzeugt Änderungen mit Ollama, validiert das Projekt und kann einen GitHub-Pull-Request mit Auto-Merge veröffentlichen.

## Voraussetzungen

- Python 3.12 und Node.js
- Ollama mit dem schnellen lokalen Standardmodell `qwen2.5:7b`
- Für Publishing: Git und ein `GITHUB_TOKEN` mit Repository- und Pull-Request-Rechten

## Start

```bash
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

## Automatischer Start unter macOS

Die versionierten LaunchAgent-Dateien unter `config/launchd` starten Backend und
Dashboard nach der Anmeldung und halten beide Prozesse aktiv. Der n8n-Agent
startet bei Bedarf Docker Desktop und anschließend den lokalen n8n-Container.
Ollama wird über den vorhandenen Homebrew-Service gestartet; ein zweiter
Ollama-Agent ist daher nicht erforderlich.

```bash
mkdir -p data/logs ~/Library/LaunchAgents
cp config/launchd/com.missioncontrol.backend.plist ~/Library/LaunchAgents/
cp config/launchd/com.missioncontrol.frontend.plist ~/Library/LaunchAgents/
cp config/launchd/com.missioncontrol.n8n.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.missioncontrol.backend.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.missioncontrol.frontend.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.missioncontrol.n8n.plist
```

Das Dashboard läuft unter `http://127.0.0.1:5173`, die API-Dokumentation unter `http://127.0.0.1:8000/docs`.

## Run-API

- `POST /api/v1/runs` startet einen autonomen Run.
- `GET /api/v1/runs/{id}` liefert Zustand und Ergebnis.
- `POST /api/v1/runs/{id}/cancel` aktiviert den Kill-Switch.
- `POST /api/v1/runs/{id}/resume` setzt einen fehlgeschlagenen oder abgebrochenen Run fort.
- `GET /api/v1/runs/{id}/events` und `WS /api/v1/ws/runs/{id}` liefern die Timeline.
- `GET /api/v1/runs/{id}/report` exportiert einen Markdown-Bericht.
- `GET /api/v1/health` prüft Datenbank, Git und Ollama.

Die aktuelle Mission-Control-Version wird zentral definiert und vom Health-Endpunkt sowie im Dashboard angezeigt.

Standardlimits sind 20 Minuten, 50 Tool-Aufrufe und drei Reparaturzyklen. Dateioperationen bleiben auf den ausgewählten Workspace begrenzt. Secrets werden in Events redigiert.

## Qualitätsprüfungen

```bash
.venv/bin/pytest -q
.venv/bin/ruff check backend
.venv/bin/mypy backend/app --explicit-package-bases
cd frontend && npm run lint && npm run build
```
