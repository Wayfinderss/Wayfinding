from fastapi import APIRouter
from pydantic import BaseModel
from app.pipeline.config_pipeline import ValhallaConfigPipeline
from app.jobs.job import Job

router = APIRouter()

class Input(BaseModel):
    lat: float
    lon: float
@router.post("/test_pipeline")
def test_pipeline():
    pipeline = ValhallaConfigPipeline(job=Job(metadata={}))
    result = pipeline.run_pipeline()
    return {"result": result}
