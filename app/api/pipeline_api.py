from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core.paths import DATA_DIR
from app.controllers.valhalla_controller import ValhallaPipelineController
from app.jobs.job_handler import JobManager
from app.api.blocked_streets_api import store as blocked_streets_store

router = APIRouter(prefix="/valhalla", tags=["valhalla"])

# Original pipeline endpoint (if needed)
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

# New directions endpoint
class DirectionsRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    costing: str = "pedestrian"

@router.post("/directions")
def get_directions(request: DirectionsRequest):
    config_path = DATA_DIR / "config.json"
    
    if not config_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Valhalla config not found. Run pipeline first."
        )
    
    # Import lazily so the API can start even if valhalla bindings
    # aren't available yet; we surface a clean 503 for callers instead.
    try:
        from app.services.valhalla_test import ValhallaTestService
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=503,
            detail=f"Valhalla service unavailable: {e}",
        )

    valhalla_service = ValhallaTestService()
    
    result = valhalla_service.run(
        config_path=config_path,
        tests={
            "route": {
                "target": {
                    "lat": request.destination_lat,
                    "lon": request.destination_lon,
                },
                "costing": request.costing,
            }
        },
        lat=request.origin_lat,
        lon=request.origin_lon,
    )

    route_data = result.get("tests", {}).get("route", {})
    active_blocked = blocked_streets_store.list_all(active_only=True)
    active_blocked_streets: List[Dict[str, Any]] = [
        {"id": b.id, "name": b.name} for b in active_blocked
    ]
    return {
        **route_data,
        "active_blocked_streets": active_blocked_streets,
    }