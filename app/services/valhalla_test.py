from typing import Dict, Any
from pathlib import Path
from valhalla import Actor

from app.services.base import TestService
from app.services.register import register

@register("valhalla_test")
class ValhallaTestService(TestService):
    service_name = "valhalla_test"

    def run(self, config_path: Path) -> Dict[str, Any]:
        actor = self._load_actor(config_path=config_path)

        results = {
            "route": self._test_route(actor),
            "isochrone": self._test_isochrone(actor),
            "matrix": self._test_matrix(actor),
            "height": self._test_height(actor),
            "expansion": self._test_expansion(actor),
        }

        return {
            "status": "ok",
            "tests": results,
        }

    # ---------------- internals ----------------

    def _load_actor(self, config_path: Path) -> Actor:
        if not config_path.exists():
            raise FileNotFoundError(f"Missing valhalla.json at {config_path}")

        print("Loading Valhalla Actor...")
        actor = Actor(str(config_path))
        print("✓ Valhalla Actor loaded successfully")

        return actor

    def _test_route(self, actor: Actor) -> Dict[str, Any]:
        result = actor.route({
            "costing": "pedestrian",
            "locations": [
                {"lat": 42.5078, "lon": 1.5211},
                {"lat": 42.5063, "lon": 1.5289},
            ],
        })

        return {
            "status": "ok",
            "summary": result.get("trip"),
        }

    def _test_isochrone(self, actor: Actor) -> Dict[str, Any]:
        result = actor.isochrone({
            "locations": [{"lat": 42.5078, "lon": 1.5211}],
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
            "sources": [{"lat": 42.5078, "lon": 1.5211}],
            "targets": [{"lat": 42.5063, "lon": 1.5289}],
        })

        return {
            "status": "ok",
            "result": result,
        }

    def _test_height(self, actor: Actor) -> Dict[str, Any]:
        result = actor.height({
            "shape": [
                {"lat": 42.5078, "lon": 1.5211},
                {"lat": 42.5063, "lon": 1.5289},
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
                {"lat": 42.5078, "lon": 1.5211},
                {"lat": 42.5063, "lon": 1.5289},
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
