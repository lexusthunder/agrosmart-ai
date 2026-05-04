#!/bin/bash
# Entrypoint pentru HF Space: seed DB la startup (ephemeral filesystem) apoi porneste API.
set -e

echo "==> Seed DB pentru containerul curent..."
python -m scripts.seed || echo "(seed esuat, continui)"

echo "==> Pornesc uvicorn pe :${PORT:-7860}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}"
