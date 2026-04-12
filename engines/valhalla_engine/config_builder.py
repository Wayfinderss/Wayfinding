from pathlib import Path
import subprocess
import json

from wayfinder.config.paths import ELEVATION_DIR, TILES_DIR, VALHALLA_DATA_DIR


class ValhallaConfigBuilder:

    def __init__(self, tiles_dir: Path):
        self.tiles_dir = tiles_dir

    def build_config(self) -> dict:
        result = subprocess.run(
            ["valhalla_build_config"],
            capture_output=True,
            text=True,
            check=True,
        )

        config = json.loads(result.stdout)

        # Tile storage
        config["mjolnir"]["tile_dir"] = str(self.tiles_dir)
        config["mjolnir"].pop("tile_extract", None)
        config["mjolnir"].pop("traffic_extract", None)
        config["mjolnir"]["elevation"] = str(ELEVATION_DIR)

        # Elevation — valhalla_build_elevation downloads tiles here,
        # and valhalla_build_tiles reads them from the same path.
        config.setdefault("additional_data", {})
        config["additional_data"]["elevation"] = str(ELEVATION_DIR)

        # Loki service defaults
        config.setdefault("loki", {})
        config["loki"].setdefault("service_defaults", {})
        defaults = config["loki"]["service_defaults"]
        defaults.setdefault("mvt_min_zoom_road_class", [0] * 8)
        defaults.setdefault("mvt_cache_min_zoom", 0)
        defaults.setdefault("mvt_cache_max_zoom", 16)
        defaults.setdefault("minimum_reachability", 3)

        return config

    def write(self, config_path: Path) -> Path:
        config = self.build_config()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        ELEVATION_DIR.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return config_path