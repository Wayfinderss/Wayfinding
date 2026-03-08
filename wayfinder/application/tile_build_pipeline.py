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
    Workflow responsible for rebuilding Valhalla tiles.

    Steps:
        1. GeoJSON → OSM XML
        2. OSM XML → PBF (osmium)
        3. Build Valhalla tiles
    """

    def __init__(self):
        self._tile_builder = ValhallaTileBuilder(TILES_DIR)

    def run(
        self,
        *,
        geojson_path: Optional[Path] = None,
        force: bool = True,
    ) -> Dict[str, Any]:

        geojson_path = geojson_path or CUSTOM_GEOJSON_PATH

        if not geojson_path.exists():
            raise FileNotFoundError(f"GeoJSON not found: {geojson_path}")

        GENERATED_OSM_PATH.parent.mkdir(parents=True, exist_ok=True)

        print("Step 1: GeoJSON → OSM")

        GeoJSONToOSMService.convert(
            geojson_path=geojson_path,
            osm_path=GENERATED_OSM_PATH,
        )

        print("Step 2: OSM → PBF")

        subprocess.run(
            [
                "osmium",
                "sort",
                str(GENERATED_OSM_PATH),
                "-o",
                str(GENERATED_PBF_PATH),
                "--overwrite",
            ],
            check=True,
        )

        print("Step 3: Build Valhalla tiles")

        self._tile_builder.build(
            config_path=VALHALLA_CONFIG_PATH,
            osm_path=GENERATED_PBF_PATH,
        )

        return {
            "status": "success",
            "geojson_used": str(geojson_path),
            "osm_generated": str(GENERATED_OSM_PATH),
            "pbf_generated": str(GENERATED_PBF_PATH),
        }