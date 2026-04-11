from typing import Any, Dict
import re

from engines.valhalla_engine.adapter import ValhallaAdapter


class ValhallaRouteService:
    """
    High-level route service responsible for:
    - Business-level route validation
    - Error interpretation
    """

    _ERROR_CODE_UNEXPECTED: int = -3
    _ERROR_CODE_DEGENERATE_ROUTE: int = 443
    _DEGENERATE_ROUTE_MESSAGE: str = (
        "Degenerate route: zero length or time (no real walkable path found)"
    )

    def __init__(self, adapter: ValhallaAdapter):
        self._adapter = adapter

    # ------------------------------------------------------------------
    # ROUTING
    # ------------------------------------------------------------------

    def request_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        costing: str = "pedestrian",
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        payload = self._build_route_payload(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            costing=costing,
            options=options,
        )

        try:
            adapter_result = self._adapter.route(payload)
        except RuntimeError as e:
            error_message = str(e)
            return self._error_result(
                error_code=self._parse_error_code(error_message),
                error_message=error_message,
            )
        except Exception as e:
            return self._error_result(
                error_code=self._ERROR_CODE_UNEXPECTED,
                error_message=f"Unexpected error: {str(e)}",
            )

        trip = self._extract_trip(adapter_result)

        if self._is_degenerate_trip(trip):
            return self._error_result(
                error_code=self._ERROR_CODE_DEGENERATE_ROUTE,
                error_message=self._DEGENERATE_ROUTE_MESSAGE,
            )

        return {"success": True, "trip": trip}

    def _build_route_payload(
        self,
        *,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        costing: str,
        options: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "locations": [
                {"lat": origin_lat, "lon": origin_lng},
                {"lat": dest_lat, "lon": dest_lng},
            ],
            "costing": costing,
        }

        if options:
            if "directions_options" in options:
                payload["directions_options"] = options["directions_options"]
            if "shape_format" in options:
                payload["shape_format"] = options["shape_format"]
            if "elevation_interval" in options:
                payload["elevation_interval"] = options["elevation_interval"]
            if "costing_options" in options:
                payload["costing_options"] = options["costing_options"]
            if "exclude_locations" in options:
                payload["exclude_locations"] = options["exclude_locations"]

        return payload

    def _extract_trip(self, adapter_result: Dict[str, Any]) -> Dict[str, Any]:
        trip = adapter_result.get("trip", adapter_result)
        return trip if isinstance(trip, dict) else {}

    def _is_degenerate_trip(self, trip: Dict[str, Any]) -> bool:
        summary = trip.get("summary", {})
        if not isinstance(summary, dict):
            return True

        route_length = summary.get("length") or 0
        route_time = summary.get("time") or 0
        return route_length == 0 or route_time == 0

    def _error_result(self, *, error_code: int, error_message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
        }

    # ------------------------------------------------------------------
    # ERROR PARSING
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_error_code(error_msg: str) -> int:
        match = re.search(r'"error_code"\s*:\s*(\d+)', error_msg)
        if match:
            return int(match.group(1))

        lower = error_msg.lower()

        if "no path" in lower or "no route" in lower:
            return 442

        if "no suitable" in lower and "origin" in lower:
            return 171

        if "no suitable" in lower and "destination" in lower:
            return 170

        return -1