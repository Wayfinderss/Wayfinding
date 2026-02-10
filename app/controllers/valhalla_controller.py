from typing import Dict, Any

from app.core.paths import DATA_DIR
from app.jobs.job import JobStatus
from app.jobs.job_handler import JobManager
from app.pipeline.config_pipeline import ValhallaConfigPipeline
import shutil


class ValhallaPipelineController:
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    def run_pipeline(
        self,
        *,
        pbf_file: str,
        lat: float,
        lon: float,
        tests: Dict[str, Dict[str, Any]],
        metadata: Dict[str, Any] | None = None,
        delete_job_on_finish: bool = True,
    ) -> Dict[str, Any]:

        job = self.job_manager.create_job(metadata=metadata or {})
        job_id = job.get_id()

        try:
            self.job_manager.update_job_status(job_id, JobStatus.QUEUED)
            self.job_manager.update_job_status(job_id, JobStatus.RUNNING)

            shutil.rmtree(DATA_DIR / "tiles", ignore_errors=True)

            pipeline = ValhallaConfigPipeline(
                job=job,
                pbf_file=pbf_file,
                lat=lat,
                lon=lon,
                tests=tests,
            )

            result = pipeline.run_pipeline()

            self.job_manager.update_job_status(job_id, JobStatus.COMPLETED)

            return {
                "job_id": job_id,
                "status": JobStatus.COMPLETED,
                "result": result,
            }

        except Exception as e:
            self.job_manager.update_job_status(job_id, JobStatus.FAILED)

            return {
                "job_id": job_id,
                "status": JobStatus.FAILED,
                "error": str(e),
            }

        finally:
            if delete_job_on_finish:
                job.cleanup()