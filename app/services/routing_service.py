"""
Valhalla route service — uses Valhalla's Python bindings (Actor)
to request pedestrian routes, matching how your existing test
pipeline works.
"""

from typing import Any, Dict
from pathlib import Path

from valhalla import Actor

class ValhallaRouteService:
    def __init__(self, config_path: Path):
        if not config_path.exists():
            raise FileNotFoundError(
                f"Valhalla config not found at {config_path}. "
                "Run /valhalla/test_pipeline first to generate it."
            )
        self.actor = Actor(str(config_path))

    def request_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        costing: str = "pedestrian",
    ) -> Dict[str, Any]:
        try:
            result = self.actor.route({
                "locations": [
                    {"lat": origin_lat, "lon": origin_lng},
                    {"lat": dest_lat, "lon": dest_lng},
                ],
                "costing": costing,
            })

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

        if isinstance(result, dict) and "trip" in result:
            trip = result["trip"]
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

        # Some versions return the trip at the top level
        return {
            "success": True,
            "trip": result,
        }

    @staticmethod
    def _parse_error_code(error_msg: str) -> int:
        """
        Try to extract a Valhalla error code from the exception message.
        Common codes: 170 (no road near dest), 171 (no road near origin),
        442 (no path found).
        """
        import re
        match = re.search(r'"error_code"\s*:\s*(\d+)', error_msg)
        if match:
            return int(match.group(1))

        # Check for known phrases
        lower = error_msg.lower()
        if "no path" in lower or "no route" in lower:
            return 442
        if "no suitable" in lower and "origin" in lower:
            return 171
        if "no suitable" in lower and "destination" in lower:
            return 170

        return -1