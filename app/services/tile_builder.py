import subprocess
import urllib.request
from pathlib import Path

from app.services.base import TestService
from app.services.register import register
from app.core.paths import (
    TILES_DIR
)

@register("tile_builder")
class ValhallaTileBuilder(TestService):
    service_name = "tile_builder"

    osm_path_URL = "https://download.geofabrik.de/north-america/us/virginia-latest.osm.pbf"

    def run(self, config_path: Path, osm_path: Path) -> None:

        if not config_path.exists():
            raise RuntimeError("valhalla.json not found — config pipeline must run first")

        self._ensure_tile_dir()
        self._ensure_pbf(osm_path)
        self._build_tiles(config_path, osm_path)

    # ---------------- internals ----------------

    def _run(self, cmd: list[str]):
        print(f"▶ {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    def _ensure_tile_dir(self):
        TILES_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✓ Tile dir ready: {TILES_DIR}")

    def _ensure_pbf(self, osm_path: Path):
        if osm_path.exists():
            print(f"✓ OSM PBF already exists: {osm_path}")
            return

        osm_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"⬇ Downloading OSM PBF")
        urllib.request.urlretrieve(self.osm_path_URL, osm_path)
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
        if not TILES_DIR.exists():
            return False
        return any(TILES_DIR.rglob("*.gph"))
