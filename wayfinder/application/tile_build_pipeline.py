import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional

from wayfinder.domain.geojson_to_osm_service import GeoJSONToOSMService
from engines.valhalla_engine.tile_builder import ValhallaTileBuilder
from wayfinder.config.paths import (
    CHUNKS_DIR,
    CHUNK_GEOJSON_DIR,
    CHUNK_OSM_DIR,
    CHUNK_PBF_DIR,
    CUSTOM_GEOJSON_PATH,
    GENERATED_OSM_PATH,
    GENERATED_PBF_PATH,
    VALHALLA_CONFIG_PATH,
    TILES_DIR,
)


CONVERSION_WORKERS = 8  # parallel GeoJSON → OSM → PBF conversions

# OSM tooling expects IDs to fit in signed 64-bit integers.
# When we build multiple chunk PBFs and later merge them, we must avoid
# node/way ID collisions across chunks, but we also must not generate
# out-of-range IDs (which breaks `osmium sort`).
# We achieve this by allocating deterministic, per-chunk ID ranges using
# a fixed stride based on the chunk's index within the current build.
NODE_ID_STRIDE = 1_000_000_000
WAY_ID_STRIDE = 1_000_000_000


class TileBuildPipeline:
    """
    Workflow responsible for rebuilding Valhalla tiles.

    Accepts either a pre-chunked dict of GeoJSON features (keyed by geohash)
    or a fallback file path for unchunked builds.

    Chunks are persisted to CHUNKS_DIR as GeoJSON + PBF pairs, keyed by
    geohash. A rebuild only reprocesses the geohashes passed in, leaving
    all other chunks untouched.
    """

    def __init__(self):
        self._tile_builder = ValhallaTileBuilder(TILES_DIR)

    @staticmethod
    def _id_bases_from_index(chunk_index: int) -> tuple[int, int]:
        """
        Create deterministic, per-build base offsets for node/way IDs.

        This avoids ID collisions when multiple chunk PBFs are merged, while
        also keeping IDs within signed 64-bit range for OSM tooling.
        """
        node_id_base = chunk_index * NODE_ID_STRIDE
        way_id_base = chunk_index * WAY_ID_STRIDE
        return node_id_base, way_id_base

    def write_chunks(self, chunks: Dict[str, list]) -> None:
        """Write all chunks to CHUNKS_DIR without building tiles."""
        CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
        for chunk_index, geohash in enumerate(sorted(chunks.keys())):
            features = chunks[geohash]
            self._write_chunk(geohash, features, chunk_index=chunk_index)
            print(f"  [{geohash}] {len(features)} features written")

    def run(
        self,
        *,
        chunks: Optional[Dict[str, list]] = None,
        geojson_path: Optional[Path] = None,
        force: bool = True,
    ) -> Dict[str, Any]:

        if chunks is not None:
            return self._run_chunked(chunks, force=force)

        return self._run_single(geojson_path or CUSTOM_GEOJSON_PATH)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_chunked(self, chunks: Dict[str, list], *, force: bool) -> Dict[str, Any]:
        CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
        pbf_paths = []

        geohashes = sorted(chunks.keys())
        with ThreadPoolExecutor(max_workers=CONVERSION_WORKERS) as ex:
            futures = {
                ex.submit(
                    self._write_chunk,
                    geohash,
                    chunks[geohash],
                    chunk_index=chunk_index,
                    force=force,
                ): geohash
                for chunk_index, geohash in enumerate(geohashes)
            }
            for future in as_completed(futures):
                geohash = futures[future]
                pbf_path = future.result()
                pbf_paths.append(pbf_path)
                print(f"  [{geohash}] converted → {pbf_path}")

        print(f"Building tiles from {len(pbf_paths)} chunks")
        self._tile_builder.build_many(config_path=VALHALLA_CONFIG_PATH, osm_paths=pbf_paths, remove_merge=False)

        return {
            "status": "success",
            "chunks_processed": len(pbf_paths),
        }

    def _write_chunk(self, geohash: str, features: list, *, chunk_index: int = 0, force: bool = True) -> Path:
        prefix = geohash[:5]

        geojson_dir = CHUNK_GEOJSON_DIR / prefix
        osm_dir = CHUNK_OSM_DIR / prefix
        pbf_dir = CHUNK_PBF_DIR / prefix

        geojson_dir.mkdir(parents=True, exist_ok=True)
        osm_dir.mkdir(parents=True, exist_ok=True)
        pbf_dir.mkdir(parents=True, exist_ok=True)

        geojson_path = geojson_dir / f"{geohash}.geojson"
        osm_path = osm_dir / f"{geohash}.osm"
        pbf_path = pbf_dir / f"{geohash}.pbf"

        # In incremental mode, avoid re-converting chunks that are already present.
        if pbf_path.exists() and not force:
            print(f"  [{geohash}] cached chunk → {pbf_path}")
            return pbf_path

        geojson_path.write_text(
            json.dumps({"type": "FeatureCollection", "features": features}),
            encoding="utf-8",
        )

        print(f"  [{geohash}] Step 1: GeoJSON → OSM")
        node_id_base, way_id_base = self._id_bases_from_index(chunk_index)
        GeoJSONToOSMService.convert(
            geojson_path=geojson_path,
            osm_path=osm_path,
            node_id_base=node_id_base,
            way_id_base=way_id_base,
        )

        print(f"  [{geohash}] Step 2: OSM → PBF")
        subprocess.run(
            [
                "osmium", "sort",
                str(osm_path),
                "-o", str(pbf_path),
                "--output-format", "pbf",
                "--overwrite",
            ],
            check=True,
        )

        KEEP_INTERMEDIATE_OSM = True
        if not KEEP_INTERMEDIATE_OSM:
            osm_path.unlink(missing_ok=True)

        return pbf_path

    def _process_chunk(self, geohash: str, features: list) -> Dict[str, Any]:
        """Single-chunk build used for incremental updates (e.g. REST API)."""
        pbf_path = self._write_chunk(geohash, features)
        print(f"  [{geohash}] Step 3: Build Valhalla tiles")
        self._tile_builder.build(config_path=VALHALLA_CONFIG_PATH, osm_path=pbf_path, append=True)
        return {
            "geohash": geohash,
            "features": len(features),
            "pbf_generated": str(pbf_path),
        }

    def _run_single(self, geojson_path: Path) -> Dict[str, Any]:
        if not geojson_path.exists():
            raise FileNotFoundError(f"GeoJSON not found: {geojson_path}")

        GENERATED_OSM_PATH.parent.mkdir(parents=True, exist_ok=True)

        print("Step 1: GeoJSON → OSM")
        GeoJSONToOSMService.convert(geojson_path=geojson_path, osm_path=GENERATED_OSM_PATH)

        print("Step 2: OSM → PBF")
        subprocess.run(
            ["osmium", "sort", str(GENERATED_OSM_PATH), "-o", str(GENERATED_PBF_PATH), "--overwrite"],
            check=True,
        )

        print("Step 3: Build Valhalla tiles")
        self._tile_builder.build(config_path=VALHALLA_CONFIG_PATH, osm_path=GENERATED_PBF_PATH)

        return {
            "status": "success",
            "geojson_used": str(geojson_path),
            "osm_generated": str(GENERATED_OSM_PATH),
            "pbf_generated": str(GENERATED_PBF_PATH),
        }