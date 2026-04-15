#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Valhalla tiles..."

export PATH="/usr/local/bin:$PATH"

cd /app

ELEVATION_DIR="/app/data/valhalla/elevation_data"
TILES_DIR="/app/data/valhalla/tiles"
DATA_DIR="/app/data/valhalla"

if [ "${REBUILD_ALL:-false}" = "true" ]; then
  echo "REBUILD_ALL requested — wiping entire data directory..."
  rm -rf "$DATA_DIR"
  mkdir -p "$DATA_DIR"
fi

if [ "${REBUILD_TILES:-false}" = "true" ] && [ -d "$ELEVATION_DIR" ]; then
  echo "Clearing elevation data for fresh rebuild..."
  rm -rf "$ELEVATION_DIR"
fi

if [ "${REBUILD_ALL:-false}" = "true" ] || [ "${REBUILD_TILES:-false}" = "true" ]; then
  python -u -m scripts.bootstrap_tiles --rebuild
else
  python -u -m scripts.bootstrap_tiles
fi

if [ -d "$ELEVATION_DIR" ]; then
  python -u -m scripts.flatten_elevation
fi

if [ -z "$(find "$ELEVATION_DIR" -maxdepth 1 -name "*.hgt" 2>/dev/null | head -1)" ]; then
  echo "Downloading elevation tiles..."
  mkdir -p "$ELEVATION_DIR"
  /usr/local/bin/valhalla_build_elevation \
    --from-tiles \
    --decompress \
    -o "$ELEVATION_DIR" \
    -c /app/data/valhalla/valhalla.json \
    -vv
  echo "Elevation tiles downloaded → $ELEVATION_DIR"
  python -u -m scripts.flatten_elevation
  echo "Rebuilding tiles with elevation..."
  rm -rf "$TILES_DIR"
  python -u -m scripts.bootstrap_tiles
else
  echo "Elevation tiles already present, skipping download"
fi

# rebuild_server.py is PID 1 — it starts and manages valhalla_service
# as a child subprocess, restarting it after each tile swap.
echo "Starting rebuild server (manages valhalla_service)..."
exec python3 /app/engines/valhalla_engine/rebuild_server.py