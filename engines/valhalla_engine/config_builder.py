from pathlib import Path
import subprocess
import json


class ValhallaConfigBuilder:
    """
    Responsible for generating a valid Valhalla config using
    the installed Valhalla binary.
    """

    def __init__(self, tiles_dir: Path):
        self.tiles_dir = tiles_dir

    def build_config(self) -> dict:
        """
        Calls valhalla_build_config and returns the parsed JSON.
        """

        result = subprocess.run(
            ["valhalla_build_config"],
            capture_output=True,
            text=True,
            check=True,
        )

        config = json.loads(result.stdout)

        # override tile directory
        config["mjolnir"]["tile_dir"] = str(self.tiles_dir)

        return config

    def write(self, config_path: Path) -> Path:
        """
        Generates the config and writes it to disk.
        """

        config = self.build_config()

        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        return config_path