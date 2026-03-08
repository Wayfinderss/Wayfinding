from typing import Dict, Any
import subprocess

from wayfinder.application.tile_build_pipeline import TileBuildPipeline


class AdminTileController:
    """
    Admin controller responsible for rebuilding routing tiles.
    """

    def __init__(self, compose_file: str = "docker-compose.yaml"):
        self.compose_file = compose_file
        self._pipeline = TileBuildPipeline()

    # -----------------------------------------------------

    def rebuild_tiles(self) -> Dict[str, Any]:

        try:
            result = self._pipeline.run(force=True)

            return {
                "status": "success",
                "pipeline": result,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": "Tile rebuild failed",
                "details": str(e),
            }

    # -----------------------------------------------------

    def restart_valhalla(self) -> Dict[str, Any]:

        try:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    self.compose_file,
                    "restart",
                    "valhalla",
                ],
                check=True,
            )

            return {
                "status": "success",
                "message": "Valhalla service restarted",
            }

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "message": "Failed to restart Valhalla",
                "details": str(e),
            }

    # -----------------------------------------------------

    def rebuild_and_reload(self) -> Dict[str, Any]:

        build = self.rebuild_tiles()

        if build["status"] != "success":
            return build

        restart = self.restart_valhalla()

        return {
            "status": "success",
            "build": build,
            "restart": restart,
        }