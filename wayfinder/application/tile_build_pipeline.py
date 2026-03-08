from pathlib import Path
from typing import Optional, Dict, Any
import subprocess

from wayfinder.domain.geojson_to_osm_service import GeoJSONToOSMService
from engines.valhalla_engine.tile_builder import ValhallaTileBuilder
from wayfinder.config.paths import (
    CUSTOM_GEOJSON_PATH,
    GENERATED_OSM_PATH,
    GENERATED_PBF_PATH,
    VALHALLA_CONFIG_PATH,
    TILES_DIR,
)


class TileBuildPipeline:
    """
    Application workflow responsible for rebuilding Valhalla tiles.

    Steps:
        1. Convert GeoJSON → OSM
        2. Renumber OSM
        3. Sort OSM
        4. Convert OSM → PBF
        5. Build Valhalla tiles
    """

    def __init__(self):
        self._tile_builder = ValhallaTileBuilder(TILES_DIR)

    # -------------------------------------------------------------

    def run(
            self,
            *,
            geojson_path: Optional[Path] = None,
            force: bool = True,
    ) -> Dict[str, Any]:
        geojson_path = geojson_path or CUSTOM_GEOJSON_PATH

        if not geojson_path.exists():
            raise FileNotFoundError(f"GeoJSON not found: {geojson_path}")

        # 1️⃣ GeoJSON → OSM
        GeoJSONToOSMService.convert(
            geojson_path=geojson_path,
            osm_path=GENERATED_OSM_PATH,
        )

        renumbered_osm = GENERATED_OSM_PATH.with_name("generated_renumbered.osm")

        # 2️⃣ Renumber
        subprocess.run(
            [
                "osmium",
                "renumber",
                str(GENERATED_OSM_PATH),
                "-o",
                str(renumbered_osm),
                "--overwrite",
            ],
            check=True,
        )

        # 3️⃣ Sort directly to PBF
        subprocess.run(
            [
                "osmium",
                "sort",
                str(renumbered_osm),
                "-o",
                str(GENERATED_PBF_PATH),
                "--overwrite",
            ],
            check=True,
        )

        # 4️⃣ Build tiles
        self._tile_builder.build(
            config_path=VALHALLA_CONFIG_PATH,
            osm_path=GENERATED_PBF_PATH,
            force=force,
        )

        return {
            "status": "success",
            "geojson_used": str(geojson_path),
            "osm_generated": str(GENERATED_OSM_PATH),
            "pbf_generated": str(GENERATED_PBF_PATH),
        }