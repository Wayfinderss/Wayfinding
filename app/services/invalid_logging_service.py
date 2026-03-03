"""
Invalid route logger — thin wrapper around the demand pipeline
for use inside the FastAPI application.

Initializes the pipeline once and exposes a simple .log() method
that the route controller calls on every failed route attempt.
"""

from typing import Optional

from app.pipelines.invalid_route_pipeline import InvalidRoutePipeline, FailedRouteAttempt

class InvalidRouteLogger:
    def __init__(
        self,
        backend: str = "postgres",
        connection_string: str = "dbname=walkway_demand",
        geohash_precision: int = 8,
    ):
        self.pipeline = InvalidRoutePipeline(
            backend=backend,
            connection_string=connection_string,
            geohash_precision=geohash_precision,
            auto_create_schema=False,  # schema is created separately
        )

    def log(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        user_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> FailedRouteAttempt:
        """Log a single failed route attempt. Returns the logged record."""
        return self.pipeline.log_failed_route(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            user_id=user_id,
            failure_reason=failure_reason,
        )