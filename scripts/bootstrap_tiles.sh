#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Valhalla tiles..."

cd /app

python -u -m scripts.bootstrap_tiles

echo "Starting Valhalla service..."

exec valhalla_service /app/data/valhalla/valhalla.json 1