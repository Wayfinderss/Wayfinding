#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Valhalla tiles..."

cd /app

ELEVATION_DIR="/app/data/valhalla/elevation_data"
TILES_DIR="/app/data/valhalla/tiles"
DATA_DIR="/app/data/valhalla"

# REBUILD_ALL: wipe the entire data directory and start from scratch
if [ "${REBUILD_ALL:-false}" = "true" ]; then
  echo "REBUILD_ALL requested — wiping entire data directory..."
  rm -rf "$DATA_DIR"
  mkdir -p "$DATA_DIR"
fi

# On a forced rebuild, wipe elevation too so it gets re-derived from new tiles
if [ "${REBUILD_TILES:-false}" = "true" ] && [ -d "$ELEVATION_DIR" ]; then
  echo "Clearing elevation data for fresh rebuild..."
  rm -rf "$ELEVATION_DIR"
fi

# Step 1: Build tiles (first pass — elevation not yet present)
if [ "${REBUILD_ALL:-false}" = "true" ] || [ "${REBUILD_TILES:-false}" = "true" ]; then
  python -u -m scripts.bootstrap_tiles --rebuild
else
  python -u -m scripts.bootstrap_tiles
fi

# Step 2: Flatten elevation dir if it exists (may have been downloaded but not
# yet flattened from a previous interrupted run)
if [ -d "$ELEVATION_DIR" ]; then
  python -u -m scripts.flatten_elevation
fi

# Step 3: Download elevation tiles if not already present in the flat dir.
# Tiles are now built so --from-tiles can derive exact coverage.
if [ -z "$(find "$ELEVATION_DIR" -maxdepth 1 -name "*.hgt" 2>/dev/null | head -1)" ]; then
  echo "Downloading elevation tiles..."
  mkdir -p "$ELEVATION_DIR"
  valhalla_build_elevation \
    --from-tiles \
    --decompress \
    -o "$ELEVATION_DIR" \
    -c /app/data/valhalla/valhalla.json \
    -vv
  echo "Elevation tiles downloaded → $ELEVATION_DIR"

  # Step 4: Flatten elevation subdirectories into parent
  python -u -m scripts.flatten_elevation

  # Step 5: Wipe tiles and rebuild with elevation now in place
  echo "Rebuilding tiles with elevation..."
  rm -rf "$TILES_DIR"
  python -u -m scripts.bootstrap_tiles
else
  echo "Elevation tiles already present, skipping download"
fi

echo "Starting Valhalla service..."
exec valhalla_service /app/data/valhalla/valhalla.json 1