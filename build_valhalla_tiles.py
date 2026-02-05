import subprocess
import sys
from pathlib import Path
import urllib.request

# ---------------- CONFIG ----------------

VALHALLA_JSON = Path("valhalla.json")

# Where tiles should live (must match mjolnir.tile_dir)
TILE_DIR = Path.home() / "valhalla_data"

# OSM source
OSM_PBF_URL = "https://download.geofabrik.de/north-america/us/virginia-latest.osm.pbf"
OSM_PBF = Path("custom_files/region.osm.pbf")

# ---------------------------------------


def run(cmd: list[str]):
    """Run a subprocess with logging and hard failure."""
    print(f"▶ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def ensure_tile_dir():
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Tile dir: {TILE_DIR}")


def download_pbf():
    if OSM_PBF.exists():
        print(f"✓ OSM PBF already exists: {OSM_PBF}")
        return

    print(f"⬇ Downloading OSM PBF from {OSM_PBF_URL}")
    urllib.request.urlretrieve(OSM_PBF_URL, OSM_PBF)
    print(f"✓ Downloaded {OSM_PBF}")


def build_tiles():
    run([
        "valhalla_build_tiles",
        "-c", str(VALHALLA_JSON),
        str(OSM_PBF),
    ])


def verify_tiles():
    tiles_path = TILE_DIR / "tiles"
    if not tiles_path.exists():
        raise RuntimeError("❌ Tile build failed: tiles/ directory not found")

    tile_count = sum(1 for _ in tiles_path.rglob("*"))
    if tile_count == 0:
        raise RuntimeError("❌ Tile build failed: tiles directory is empty")

    print(f"✓ Tiles built successfully ({tile_count} files)")


def main():
    if not VALHALLA_JSON.exists():
        print("❌ valhalla.json not found")
        sys.exit(1)

    ensure_tile_dir()
    download_pbf()
    build_tiles()
    verify_tiles()

    print("\n🎉 Valhalla tiles are ready")


if __name__ == "__main__":
    main()
