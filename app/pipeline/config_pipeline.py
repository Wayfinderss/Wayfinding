from typing import Dict, Any
import os

from app.jobs.job import Job, JobStatus
from app.services.register import VALHALLA_SERVICE_REGISTRY
from app.core.paths import DATA_DIR


class ValhallaConfigPipeline:
    def __init__(
        self,
        job: Job,
        pbf_file: str,
        lat: float,
        lon: float,
        tests: Dict[str, Dict[str, Any]],
    ):
        self.job = job
        self.osm_path = DATA_DIR / "custom_files" / pbf_file
        self.lat = lat
        self.lon = lon
        self.tests = tests

    def run_pipeline(self):
        if self.job.get_status() != JobStatus.RUNNING:
            raise ValueError(
                "Cannot run pipeline on a job that is not in RUNNING state"
            )

        config_path = DATA_DIR / "config.json"

        # ---------------- config generation ----------------
        if config_path.exists():
            os.remove(config_path)

        config_state = VALHALLA_SERVICE_REGISTRY["config_builder"].run()

        normalized_state = VALHALLA_SERVICE_REGISTRY[
            "config_normalizer"
        ].run(state=config_state)

        VALHALLA_SERVICE_REGISTRY["config_writer"].run(
            state=normalized_state,
            output_path=config_path,
        )

        # ---------------- tile building ----------------
        VALHALLA_SERVICE_REGISTRY["tile_builder"].run(
            config_path=config_path,
            osm_path=self.osm_path,
        )

        # ---------------- validation tests ----------------
        results = VALHALLA_SERVICE_REGISTRY["valhalla_test"].run(
            config_path=config_path,
            tests=self.tests,     # dict[str, dict]
            lat=self.lat,
            lon=self.lon,
        )

        return {
            "job_id": self.job.get_id(),
            "status": "ok",
            "inputs": {
                "osm_path": str(self.osm_path),
                "origin": {
                    "lat": self.lat,
                    "lon": self.lon,
                },
                "tests": self.tests,
            },
            "results": results,
        }
