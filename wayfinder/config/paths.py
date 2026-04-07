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

# Single-file network build (replaces chunked intermediates for bootstrap)
NETWORK_OSM_PATH = VALHALLA_DATA_DIR / "network.osm"
NETWORK_PBF_PATH = VALHALLA_DATA_DIR / "network.osm.pbf"

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
# Chunk storage
# -------------------------------------------------------------------

CHUNKS_DIR = VALHALLA_DATA_DIR / "chunks"

# Source chunks (editable)
CHUNK_GEOJSON_DIR = CHUNKS_DIR / "geojson"

# Derived chunks (temporary build artifacts)
CHUNK_PBF_DIR = CHUNKS_DIR / "pbf"
CHUNK_OSM_DIR = CHUNKS_DIR / "osm"

# -------------------------------------------------------------------
# Node registry (persistent coordinate → OSM node ID mapping)
# Used to maintain stable node IDs across CRUD updates
# -------------------------------------------------------------------

NODE_REGISTRY_PATH = VALHALLA_DATA_DIR / "node_registry.db"

# -------------------------------------------------------------------
# Elevation data directory
# Valhalla checks here for DEM tiles first; falls back to OSM `ele`
# tags on nodes if the directory is empty or has no coverage.
# -------------------------------------------------------------------

ELEVATION_DIR = VALHALLA_DATA_DIR / "elevation_data"