from fastapi import APIRouter, Query

from app.pipelines.invalid_route_pipeline import InvalidRoutePipeline

router = APIRouter(prefix="/demand", tags=["demand"])

pipeline = InvalidRoutePipeline(
    backend="postgres",
    connection_string="dbname=walkway_demand",
    auto_create_schema=False,
    geohash_precision=9,
)


@router.get("/hotspots")
def get_hotspots(
    min_attempts: int = Query(default=3, description="Minimum failed attempts to qualify"),
    limit: int = Query(default=50, description="Max results to return"),
):
    hotspots = pipeline.get_demand_hotspots(min_attempts=min_attempts, limit=limit)
    return [
        {
            "geohash": hs.geohash,
            "point_type": hs.point_type,
            "center_lat": hs.center_lat,
            "center_lng": hs.center_lng,
            "attempt_count": hs.attempt_count,
            "unique_users": hs.unique_users,
            "first_seen": hs.first_seen,
            "last_seen": hs.last_seen,
            "failure_reasons": hs.sample_reasons,
        }
        for hs in hotspots
    ]


@router.get("/route_pairs")
def get_route_pairs(
    min_attempts: int = Query(default=2, description="Minimum failed attempts to qualify"),
    limit: int = Query(default=20, description="Max results to return"),
):
    return pipeline.get_top_route_pairs(min_attempts=min_attempts, limit=limit)


@router.get("/near")
def get_attempts_near(
    lat: float = Query(..., description="Latitude to search around"),
    lng: float = Query(..., description="Longitude to search around"),
):
    return pipeline.get_attempts_near(lat, lng)