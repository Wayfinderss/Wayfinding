from typing import Any, Dict, Optional

from wayfinder.application.route_pipeline import RoutePipeline
from wayfinder.application.invalid_route_pipeline import InvalidRoutePipeline
from wayfinder.domain.routing_service import ValhallaRouteService
from engines.valhalla_engine.adapter import ValhallaAdapter


VALHALLA_FAILURE_REASONS = {
    170: "no_road_near_destination",
    171: "no_road_near_origin",
    442: "no_path_found",
    443: "degenerate_route",
}


class RouteController:
    def __init__(
        self,
        valhalla_url: str,
        db_backend: str = "postgres",
        db_connection_string: str = "dbname=walkway_demand",
    ):
        adapter = ValhallaAdapter(base_url=valhalla_url)
        route_service = ValhallaRouteService(adapter)

        self.pipeline = RoutePipeline(route_service)
        self.invalid_route_pipeline = InvalidRoutePipeline(
            backend=db_backend,
            connection_string=db_connection_string,
            geohash_precision=9,
            auto_create_schema=False,
        )

    def get_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        costing: str = "pedestrian",
        options: Dict[str, Any] | None = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = self.pipeline.execute(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            costing=costing,
            options=options,
        )

        if result.get("success"):
            return {
                "status": "ok",
                "trip": result["trip"],
            }

        error_code = result.get("error_code")
        error_message = result.get("error_message", "unknown")

        failure_reason = VALHALLA_FAILURE_REASONS.get(
            error_code,
            f"valhalla_{error_code}",
        )

        if error_code is not None and error_code >= 0:
            attempt = self.invalid_route_pipeline.log_failed_route(
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                dest_lat=dest_lat,
                dest_lng=dest_lng,
                user_id=user_id,
                failure_reason=failure_reason,
            )
            logged_attempt_id = attempt.id
        else:
            logged_attempt_id = None

        return {
            "status": "no_route",
            "error_code": error_code,
            "error_message": error_message,
            "failure_reason": failure_reason,
            "logged_attempt_id": logged_attempt_id,
        }