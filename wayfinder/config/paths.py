from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# -------------------------------------------------------------------
# Valhalla data directory
# -------------------------------------------------------------------

VALHALLA_DATA_DIR = BASE_DIR / "data" / "valhalla"

# -------------------------------------------------------------------
# Source datasets
# -------------------------------------------------------------------

CUSTOM_GEOJSON_PATH = VALHALLA_DATA_DIR / "custom_sidewalks.geojson"

# -------------------------------------------------------------------
# Generated intermediate files
# -------------------------------------------------------------------

GENERATED_OSM_PATH = VALHALLA_DATA_DIR / "generated_sidewalks.osm"

GENERATED_PBF_PATH = VALHALLA_DATA_DIR / "generated_sidewalks.osm.pbf"
GENERATED_OPL_PATH = VALHALLA_DATA_DIR / "generated_sidewalks.osm.opl"

# -------------------------------------------------------------------
# Valhalla configuration
# -------------------------------------------------------------------

VALHALLA_CONFIG_PATH = VALHALLA_DATA_DIR / "valhalla.json"

# -------------------------------------------------------------------
# Valhalla tile storage
# -------------------------------------------------------------------

VALHALLA_TILES_DIR = VALHALLA_DATA_DIR / "tiles"
TILES_DIR = VALHALLA_TILES_DIR

# -------------------------------------------------------------------
# Chunk storage (GeoJSON + PBF per geohash bucket)
# -------------------------------------------------------------------

CHUNKS_DIR = VALHALLA_DATA_DIR / "chunks"