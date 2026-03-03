# engines/valhalla/tile_builder.py

import subprocess
import urllib.request
from pathlib import Path


class ValhallaTileBuilder:

    DEFAULT_OSM_URL = (
        "https://download.geofabrik.de/north-america/us/virginia-latest.osm.pbf"
    )

    def __init__(self, tiles_dir: Path):
        self.tiles_dir = tiles_dir

    def build(self, config_path: Path, osm_path: Path | None = None) -> None:
        if not config_path.exists():
            raise RuntimeError("valhalla.json not found — cannot build tiles")

        self._ensure_tile_dir()

        if osm_path is None:
            osm_path = self.tiles_dir.parent / "default.osm.pbf"

        self._ensure_pbf(osm_path)
        self._build_tiles(config_path, osm_path)

    # ---------------- internals ----------------

    def _run(self, cmd: list[str]):
        print(f"▶ {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    def _ensure_tile_dir(self):
        self.tiles_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Tile dir ready: {self.tiles_dir}")

    def _ensure_pbf(self, osm_path: Path):
        if osm_path.exists():
            print(f"✓ OSM PBF already exists: {osm_path}")
            return

        osm_path.parent.mkdir(parents=True, exist_ok=True)
        print("⬇ Downloading OSM PBF")
        urllib.request.urlretrieve(self.DEFAULT_OSM_URL, osm_path)
        print(f"✓ Downloaded {osm_path}")

    def _build_tiles(self, config: Path, osm_path: Path):
        if self._tiles_exist():
            print("✓ Tiles already built")
            return

        self._run([
            "valhalla_build_tiles",
            "-c", str(config),
            str(osm_path),
        ])

        if not self._tiles_exist():
            raise RuntimeError("Tile build completed but no tiles were produced")

        print("✓ Tiles built successfully")

    def _tiles_exist(self) -> bool:
        if not self.tiles_dir.exists():
            return False
        return any(self.tiles_dir.rglob("*.gph"))