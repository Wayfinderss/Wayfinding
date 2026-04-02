#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Valhalla tiles..."

cd /app

if [ "${REBUILD_TILES:-false}" = "true" ]; then
  python -u -m scripts.bootstrap_tiles --rebuild
else
  python -u -m scripts.bootstrap_tiles
fi

echo "Starting Valhalla service..."

exec valhalla_service /app/data/valhalla/valhalla.json 1