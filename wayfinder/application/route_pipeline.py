from typing import Any, Dict

from wayfinder.domain.routing_service import ValhallaRouteService


class RoutePipeline:
    """
    Pure routing execution layer.
    No side effects.
    """

    def __init__(self, route_service: ValhallaRouteService):
        self._route_service = route_service

    def execute(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        costing: str = "pedestrian",
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        return self._route_service.request_route(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            costing=costing,
            options=options,
        )