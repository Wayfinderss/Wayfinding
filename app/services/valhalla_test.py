from typing import Dict, Any, Callable, List
from pathlib import Path

from valhalla import Actor

from app.services.base import TestService
from app.services.register import register


@register("valhalla_test")
class ValhallaTestService(TestService):
    service_name = "valhalla_test"

    def run(
        self,
        config_path: Path,
        tests: List[str],
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        actor = self._load_actor(config_path)

        # store coordinates for internal use
        self.lat = lat
        self.lon = lon

        test_registry: Dict[str, Callable[[Actor], Dict[str, Any]]] = {
            "route": self._test_route,
            "isochrone": self._test_isochrone,
            "matrix": self._test_matrix,
            "height": self._test_height,
            "expansion": self._test_expansion,
        }

        results: Dict[str, Any] = {}

        for test_name in tests:
            if test_name not in test_registry:
                results[test_name] = {
                    "status": "skipped",
                    "reason": "unknown test",
                }
                continue

            try:
                results[test_name] = test_registry[test_name](actor)
            except Exception as e:
                results[test_name] = {
                    "status": "error",
                    "error": str(e),
                }

        return {
            "status": "ok",
            "lat": self.lat,
            "lon": self.lon,
            "tests": results,
        }

    # ---------------- internals ----------------

    def _load_actor(self, config_path: Path) -> Actor:
        if not config_path.exists():
            raise FileNotFoundError(f"Missing valhalla.json at {config_path}")

        return Actor(str(config_path))

    # ---------------- tests ----------------

    def _test_route(self, actor: Actor) -> Dict[str, Any]:
        result = actor.route({
            "costing": "pedestrian",
            "locations": [
                {"lat": self.lat, "lon": self.lon},
                {"lat": self.lat + 0.001, "lon": self.lon + 0.001},
            ],
        })

        return {
            "status": "ok",
            "summary": result.get("trip"),
        }

    def _test_isochrone(self, actor: Actor) -> Dict[str, Any]:
        result = actor.isochrone({
            "locations": [
                {"lat": self.lat, "lon": self.lon}
            ],
            "costing": "pedestrian",
            "contours": [{"time": 5, "color": "ff0000"}],
            "polygons": True,
        })

        return {
            "status": "ok",
            "features": len(result.get("features", [])),
        }

    def _test_matrix(self, actor: Actor) -> Dict[str, Any]:
        result = actor.matrix({
            "costing": "pedestrian",
            "sources": [
                {"lat": self.lat, "lon": self.lon}
            ],
            "targets": [
                {"lat": self.lat + 0.001, "lon": self.lon + 0.001}
            ],
        })

        return {
            "status": "ok",
            "result": result,
        }

    def _test_height(self, actor: Actor) -> Dict[str, Any]:
        result = actor.height({
            "shape": [
                {"lat": self.lat, "lon": self.lon},
                {"lat": self.lat + 0.001, "lon": self.lon + 0.001},
            ],
            "range": True,
        })

        return {
            "status": "ok",
            "result": result,
        }

    def _test_expansion(self, actor: Actor) -> Dict[str, Any]:
        result = actor.expansion({
            "action": "route",
            "costing": "pedestrian",
            "locations": [
                {"lat": self.lat, "lon": self.lon},
                {"lat": self.lat + 0.001, "lon": self.lon + 0.001},
            ],
            "expansion_properties": [
                "duration",
                "edge_id",
                "edge_status",
            ],
        })

        return {
            "status": "ok",
            "algorithm": result.get("properties", {}).get("algorithm"),
            "edges": len(result.get("features", [])),
        }
