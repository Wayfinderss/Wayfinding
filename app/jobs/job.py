import uuid
from enum import Enum
from datetime import datetime
from pathlib import Path
import shutil

from app.core.paths import BASE_JOBS_DIR


class JobStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job:
    """
    Represents a single execution job.

    Responsibilities:
    - Own a unique job ID
    - Track lifecycle status
    - Own a job-specific artifact directory
    """

    def __init__(self, metadata: dict) -> None:
        self.job_id: str = str(uuid.uuid4())
        self.metadata: dict = metadata

        # Lifecycle
        self.status: JobStatus = JobStatus.CREATED
        self.created_at: datetime = datetime.now()
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None

        # Job-owned directory
        self.job_dir: Path = BASE_JOBS_DIR / self.job_id
        self.job_dir.mkdir(parents=True, exist_ok=True)

    # ==========================
    # Accessors
    # ==========================

    def get_id(self) -> str:
        return self.job_id

    def get_status(self) -> JobStatus:
        return self.status

    def get_dir(self) -> Path:
        return self.job_dir

    # ==========================
    # Lifecycle helpers (optional but useful)
    # ==========================

    def mark_running(self):
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self):
        self.status = JobStatus.COMPLETED
        self.finished_at = datetime.now()

    def mark_failed(self):
        self.status = JobStatus.FAILED
        self.finished_at = datetime.now()

    def mark_cancelled(self):
        self.status = JobStatus.CANCELLED
        self.finished_at = datetime.now()

    def cleanup(self):
        shutil.rmtree(self.job_dir, ignore_errors=True)