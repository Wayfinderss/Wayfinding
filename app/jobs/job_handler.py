from typing import Dict, Optional
from app.jobs.job import Job, JobStatus


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create_job(self, metadata: Optional[Dict] = None) -> Job:
        job = Job(metadata=metadata)
        self._jobs[job.get_id()] = job
        return job

    def get_job(self, job_id: str) -> Job:
        return self._jobs[job_id]

    def update_job_status(self, job_id: str, new_status: JobStatus) -> None:
        job = self.get_job(job_id)

        allowed = {
            JobStatus.CREATED: {JobStatus.QUEUED, JobStatus.CANCELLED},
            JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
            JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
            JobStatus.FAILED: set(),
            JobStatus.COMPLETED: set(),
        }[job.status]

        if new_status not in allowed:
            raise ValueError(
                f"Invalid job state transition: {job.status} → {new_status}"
            )

        job.status = new_status

    def delete_job(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise ValueError(f"Job with ID {job_id} does not exist")

        del self._jobs[job_id]