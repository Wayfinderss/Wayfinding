import subprocess
import urllib.request
import shutil
from pathlib import Path


class ValhallaTileBuilder:
    """
    Engine-level component responsible for building Valhalla tiles.

    This class does NOT know anything about the Wayfinder application
    structure. It only operates on:
        - config path
        - OSM PBF
        - tile directory
    """

    DEFAULT_OSM_URL = (
        "https://download.geofabrik.de/north-america/us/virginia-latest.osm.pbf"
    )

    def __init__(self, tiles_dir: Path):
        self.tiles_dir = Path(tiles_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        *,
        config_path: Path,
        osm_path: Path,
        auto_download: bool = False,
        force: bool = False,
    ) -> None:
        """
        Build Valhalla tiles.

        Args:
            config_path: Path to valhalla.json
            osm_path: Path to OSM PBF
            auto_download: Download default dataset if missing
            force: Force rebuild even if tiles already exist
        """

        config_path = Path(config_path)
        osm_path = Path(osm_path)

        if not config_path.exists():
            raise RuntimeError("valhalla.json not found — cannot build tiles")

        if not osm_path.exists():
            if not auto_download:
                raise FileNotFoundError(
                    f"OSM PBF not found at {osm_path} "
                    "(set auto_download=True to fetch default dataset)"
                )
            self._download_default_pbf(osm_path)

        if self._tiles_exist():
            if not force:
                print("✓ Tiles already exist — skipping build")
                return
            print("♻ Clearing existing tiles (force rebuild)")
            self._clear_tiles()

        self._ensure_tile_dir()

        self._run([
            "valhalla_build_tiles",
            "-c",
            str(config_path),
            str(osm_path),
        ])

        if not self._tiles_exist():
            raise RuntimeError("Tile build completed but no tiles were produced")

        print("✓ Tiles built successfully")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(self, cmd: list[str]):
        print(f"▶ {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    def _ensure_tile_dir(self):
        self.tiles_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Tile directory ready: {self.tiles_dir}")

    def _clear_tiles(self):
        if self.tiles_dir.exists():
            shutil.rmtree(self.tiles_dir)

    def _download_default_pbf(self, osm_path: Path):
        osm_path.parent.mkdir(parents=True, exist_ok=True)
        print("⬇ Downloading default OSM dataset")
        urllib.request.urlretrieve(self.DEFAULT_OSM_URL, osm_path)
        print(f"✓ Downloaded dataset to {osm_path}")

    def _tiles_exist(self) -> bool:
        return self.tiles_dir.exists() and any(self.tiles_dir.rglob("*.gph"))