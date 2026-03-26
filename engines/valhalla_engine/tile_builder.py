import subprocess
import urllib.request
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


MERGE_BATCH_SIZE = 64   # osmium merge args per batch
MERGE_WORKERS   = 8     # parallel batch merges


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
        append: bool = False,
    ) -> None:
        """
        Build Valhalla tiles from a single PBF.

        Args:
            config_path:   Path to valhalla.json
            osm_path:      Path to OSM PBF
            auto_download: Download default dataset if osm_path is missing
            force:         Clear existing tiles before building
            append:        Add tiles without clearing existing tiles (for incremental updates)
        """
        config_path = Path(config_path)
        osm_path    = Path(osm_path)

        if not config_path.exists():
            raise RuntimeError("valhalla.json not found — cannot build tiles")

        if not osm_path.exists():
            if not auto_download:
                raise FileNotFoundError(
                    f"OSM PBF not found at {osm_path} "
                    "(set auto_download=True to fetch default dataset)"
                )
            self._download_default_pbf(osm_path)

        if not append:
            if self._tiles_exist():
                if not force:
                    print("✓ Tiles already exist — skipping build")
                    return
                print("♻ Clearing existing tiles (force rebuild)")
                self._clear_tiles()

        self._ensure_tile_dir()
        self._run(["valhalla_build_tiles", "-c", str(config_path), str(osm_path)])

        if not self._tiles_exist():
            raise RuntimeError("Tile build completed but no tiles were produced")

        print("✓ Tiles built successfully")

    def build_many(
        self,
        *,
        config_path: Path,
        osm_paths: list[Path],
        force: bool = False,
    ) -> None:
        """
        Build Valhalla tiles from many PBFs.

        Merges in parallel batches to stay under OS argument limits, then
        builds tiles from the single merged PBF.

        Args:
            config_path: Path to valhalla.json
            osm_paths:   List of chunk PBF paths
            force:       Clear existing tiles before building
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise RuntimeError("valhalla.json not found — cannot build tiles")

        missing = [p for p in osm_paths if not Path(p).exists()]
        if missing:
            raise FileNotFoundError(f"Missing PBFs: {missing}")

        if self._tiles_exist():
            if not force:
                print("✓ Tiles already exist — skipping build")
                return
            print("♻ Clearing existing tiles (force rebuild)")
            self._clear_tiles()

        merge_dir = self.tiles_dir.parent / "merge_tmp"
        merge_dir.mkdir(parents=True, exist_ok=True)

        try:
            merged_pbf = self._merge_all(osm_paths, merge_dir)

            self._ensure_tile_dir()
            self._run(["valhalla_build_tiles", "-c", str(config_path), str(merged_pbf)])

            if not self._tiles_exist():
                raise RuntimeError("Tile build completed but no tiles were produced")

            print(f"✓ Tiles built successfully from {len(osm_paths)} chunks")

        finally:
            shutil.rmtree(merge_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Merge helpers
    # ------------------------------------------------------------------

    def _merge_all(self, osm_paths: list[Path], merge_dir: Path) -> Path:
        """
        Recursively merge PBFs in parallel batches until one file remains.
        Each round merges up to MERGE_BATCH_SIZE files per worker.
        """
        current = list(osm_paths)
        round_n = 0

        while len(current) > 1:
            batches = [
                current[i : i + MERGE_BATCH_SIZE]
                for i in range(0, len(current), MERGE_BATCH_SIZE)
            ]

            print(f"  Merge round {round_n}: {len(current)} files → {len(batches)} batches")

            next_round: list[Path] = []

            with ThreadPoolExecutor(max_workers=MERGE_WORKERS) as ex:
                futures = {
                    ex.submit(
                        self._merge_batch,
                        batch,
                        merge_dir / f"r{round_n}_b{i}.pbf",
                    ): i
                    for i, batch in enumerate(batches)
                }
                for future in as_completed(futures):
                    next_round.append(future.result())

            current = next_round
            round_n += 1

        return current[0]

    def _merge_batch(self, paths: list[Path], out: Path) -> Path:
        """Merge a single batch of PBFs into one output file."""
        if len(paths) == 1:
            return paths[0]
        self._run([
            "osmium", "merge",
            *[str(p) for p in paths],
            "-o", str(out),
            "--overwrite",
        ])
        return out

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