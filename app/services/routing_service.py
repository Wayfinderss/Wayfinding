from typing import Any, Dict
import re

from engines.valhalla_engine.adapter import ValhallaAdapter


class ValhallaRouteService:
    """
    High-level route service responsible for business-level
    route validation and error interpretation.
    """

    def __init__(self, adapter: ValhallaAdapter):
        self._adapter = adapter

    def request_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        costing: str = "pedestrian",
    ) -> Dict[str, Any]:

        payload = {
            "locations": [
                {"lat": origin_lat, "lon": origin_lng},
                {"lat": dest_lat, "lon": dest_lng},
            ],
            "costing": costing,
        }

        try:
            result = self._adapter.route(payload)

        except RuntimeError as e:
            error_msg = str(e)
            error_code = self._parse_error_code(error_msg)
            return {
                "success": False,
                "error_code": error_code,
                "error_message": error_msg,
            }

        except Exception as e:
            return {
                "success": False,
                "error_code": -3,
                "error_message": f"Unexpected error: {str(e)}",
            }

        # Normal successful response
        trip = result.get("trip", result)

        summary = trip.get("summary", {})
        route_length = summary.get("length", 0)
        route_time = summary.get("time", 0)

        if route_length == 0 or route_time == 0:
            return {
                "success": False,
                "error_code": 443,
                "error_message": "Degenerate route: zero length or time (no real walkable path found)",
            }

        return {
            "success": True,
            "trip": trip,
        }

    @staticmethod
    def _parse_error_code(error_msg: str) -> int:
        """
        Extract Valhalla error codes from error message.
        Common codes:
            170 - no road near destination
            171 - no road near origin
            442 - no path found
        """

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