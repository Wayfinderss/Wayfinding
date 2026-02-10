from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.controllers.valhalla_controller import ValhallaPipelineController
from app.jobs.job_handler import JobManager


router = APIRouter(prefix="/valhalla", tags=["valhalla"])


class ValhallaPipelineInput(BaseModel):
    pbf_file: str = Field(default="andorra-latest.osm.pbf")
    lat: float
    lon: float

    tests: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "route": {},
            "isochrone": {},
            "matrix": {},
            "height": {},
            "expansion": {},
        }
    )


# Instantiate once (app-level singleton)
job_manager = JobManager()
controller = ValhallaPipelineController(job_manager)


@router.post("/test_pipeline")
def test_pipeline(pipeline_input: ValhallaPipelineInput):
    return controller.run_pipeline(
        pbf_file=pipeline_input.pbf_file,
        lat=pipeline_input.lat,
        lon=pipeline_input.lon,
        tests=pipeline_input.tests,
        metadata={"source": "valhalla_test_api"},
    )
