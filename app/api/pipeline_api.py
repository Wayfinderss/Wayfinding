from pathlib import Path
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.pipeline.config_pipeline import ValhallaConfigPipeline
from app.jobs.job import Job


router = APIRouter(prefix="/valhalla", tags=["valhalla"])


class ValhallaPipelineInput(BaseModel):
    pbf_file: str = Field(default="andorra-latest.osm.pbf")
    lat: float
    lon: float
    tests: List[str] = Field(
        default_factory=lambda: [
            "route",
            "isochrone",
            "matrix",
            "height",
            "expansion",
        ]
    )


@router.post("/test_pipeline")
def test_pipeline(pipeline_input: ValhallaPipelineInput):
    job = Job(metadata={"source": "valhalla_test_api"})

    pipeline = ValhallaConfigPipeline(
        job=job,
        pbf_file=pipeline_input.pbf_file,
        lat=pipeline_input.lat,
        lon=pipeline_input.lon,
        tests=pipeline_input.tests,
    )

    result = pipeline.run_pipeline()
    return result
