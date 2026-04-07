#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Valhalla tiles..."

cd /app

if [ "${REBUILD_TILES:-false}" = "true" ]; then
  python -u -m scripts.bootstrap_tiles --rebuild
else
  python -u -m scripts.bootstrap_tiles
fi

# Download elevation tiles if not already present.
# Uses valhalla_build_elevation which fetches SRTM data for the bounding
# box defined by min_x/min_y/max_x/max_y env vars in docker-compose.yaml.
ELEVATION_DIR="/app/data/valhalla/elevation_data"
if [ ! -d "$ELEVATION_DIR" ] || [ -z "$(ls -A "$ELEVATION_DIR" 2>/dev/null)" ]; then
  echo "Downloading elevation tiles..."
  mkdir -p "$ELEVATION_DIR"
  valhalla_build_elevation \
    --from-tiles \
    --decompress \
    -c /app/data/valhalla/valhalla.json \
    -v
  echo "Elevation tiles downloaded → $ELEVATION_DIR"
else
  echo "Elevation tiles already exist, skipping download"
fi

echo "Starting Valhalla service..."

exec valhalla_service /app/data/valhalla/valhalla.json 1