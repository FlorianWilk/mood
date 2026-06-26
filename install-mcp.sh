#!/usr/bin/env bash
# Registriert die mood-MCP-Bridge in Claude Code (Tool: feel).
# Danach zeigt deine KI ihre Stimmung auf dem laufenden mood-Display (./run.sh).
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"
PORT="${MOOD_PORT:-8765}"

command -v claude >/dev/null || { echo "FEHLER: 'claude' (Claude Code CLI) nicht gefunden."; exit 1; }
command -v uv     >/dev/null || { echo "FEHLER: 'uv' nicht gefunden – siehe https://docs.astral.sh/uv/"; exit 1; }

# venv beim ersten Mal einrichten (für den Python-Interpreter-Pfad)
[ -d .venv ] || uv sync

# idempotent: vorhandene Registrierung ersetzen
claude mcp remove mood >/dev/null 2>&1 || true
claude mcp add mood --scope user -- \
  "$DIR/.venv/bin/python" "$DIR/mood.py" -m --port "$PORT"

echo "✓ mood-Bridge registriert (Port $PORT)."
echo "  1) Display starten:  ./run.sh"
echo "  2) Claude Code neu starten, dann mit /mcp prüfen."
