from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent

BASE_JOBS_DIR = APP_ROOT / "jobs"

DATA_DIR = APP_ROOT / "data"
TILES_DIR = DATA_DIR / "tiles"
VALHALLA_DATA = DATA_DIR / "valhalla"

TRANSIT_DIR = APP_ROOT / "transit"
TRANSIT_FEEDS_DIR = APP_ROOT / "transit_feeds"
ELEVATION_DIR = APP_ROOT / "elevation"