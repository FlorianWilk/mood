#!/usr/bin/env bash
# mood — startet das Stimmungs-Display deiner KI (Listener) mit den Standard-Settings.
# Andere brauchen nur:  ./run.sh   (Voraussetzung: uv + NVIDIA-GPU)
#
# Eigene Argumente werden durchgereicht, z.B.:  ./run.sh --color cyan
set -euo pipefail
cd "$(dirname "$0")"

# venv beim ersten Mal einrichten
if [ ! -d .venv ]; then
  echo "Richte Umgebung ein (uv sync) …"
  uv sync
fi

exec uv run mood.py "$@"
