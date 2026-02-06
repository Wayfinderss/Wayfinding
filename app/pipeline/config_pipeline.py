from app.jobs.job import Job, JobStatus
from app.services.register import VALHALLA_SERVICE_REGISTRY
from app.core.paths import DATA_DIR
from pathlib import Path

class ValhallaConfigPipeline:
    def __init__(self, job: Job):
        self.job = job

    def run_pipeline(self):
        if self.job.get_status() != JobStatus.CREATED:
            raise ValueError("Cannot run pipeline on a job that is not in CREATED state")
        if Path(DATA_DIR / "valhalla.json").exists():
            return
        config_state = VALHALLA_SERVICE_REGISTRY["config_builder"].run()
        normalizer = VALHALLA_SERVICE_REGISTRY["config_normalizer"].run(state=config_state)
        VALHALLA_SERVICE_REGISTRY["config_writer"].run(state=normalizer, output_path=DATA_DIR / "config.json")
        VALHALLA_SERVICE_REGISTRY["tile_builder"].run(config_path=DATA_DIR / "config.json", osm_path=DATA_DIR / "custom_files" / "andorra-latest.osm.pbf")
        results = VALHALLA_SERVICE_REGISTRY["valhalla_test"].run(config_path=DATA_DIR / "config.json")
        return results
