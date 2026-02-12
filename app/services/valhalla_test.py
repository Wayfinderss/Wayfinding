from typing import Dict, Any, Callable
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
        tests: Dict[str, Dict[str, Any]],
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        actor = self._load_actor(config_path)

        self.origin = {"lat": lat, "lon": lon}
        self.default_target = {
            "lat": lat + 0.001,
            "lon": lon + 0.001,
        }

        test_registry: Dict[str, Callable[[Actor, Dict[str, Any]], Dict[str, Any]]] = {
            "route": self._test_route,
            "isochrone": self._test_isochrone,
            "matrix": self._test_matrix,
            "height": self._test_height,
            "expansion": self._test_expansion,
        }

        results: Dict[str, Any] = {}

        for test_name, test_args in tests.items():
            if test_name not in test_registry:
                results[test_name] = {
                    "status": "skipped",
                    "reason": "unknown test",
                }
                continue

            try:
                results[test_name] = test_registry[test_name](actor, test_args)
            except Exception as e:
                results[test_name] = {
                    "status": "error",
                    "error": str(e),
                }

        return {
            "status": "ok",
            "origin": self.origin,
            "tests": results,
        }

    # ---------------- internals ----------------

    def _load_actor(self, config_path: Path) -> Actor:
        if not config_path.exists():
            raise FileNotFoundError(f"Missing valhalla.json at {config_path}")
        return Actor(str(config_path))

    def _resolve_target(self, args: Dict[str, Any]) -> Dict[str, float]:
        return args.get("target", self.default_target)

    # ---------------- tests ----------------

    def _test_route(self, actor: Actor, args: Dict[str, Any]) -> Dict[str, Any]:
        target = self._resolve_target(args)
        print(f"Testing route from {self.origin} to {target}")
        result = actor.route({
            "costing": args.get("costing", "pedestrian"),
            "locations": [
                self.origin,
                target,
            ],
        })

        return {
            "status": "ok",
            "origin": self.origin,
            "target": target,
            "summary": result.get("trip"),
        }

    def _test_isochrone(self, actor: Actor, args: Dict[str, Any]) -> Dict[str, Any]:
        result = actor.isochrone({
            "locations": [self.origin],
            "costing": args.get("costing", "pedestrian"),
            "contours": [{
                "time": args.get("time", 5),
                "color": args.get("color", "ff0000"),
            }],
            "polygons": args.get("polygons", True),
        })

        return {
            "status": "ok",
            "features": len(result.get("features", [])),
        }

    def _test_matrix(self, actor: Actor, args: Dict[str, Any]) -> Dict[str, Any]:
        target = self._resolve_target(args)

        result = actor.matrix({
            "costing": args.get("costing", "pedestrian"),
            "sources": [self.origin],
            "targets": [target],
        })

        return {
            "status": "ok",
            "origin": self.origin,
            "target": target,
            "result": result,
        }

    def _test_height(self, actor: Actor, args: Dict[str, Any]) -> Dict[str, Any]:
        target = self._resolve_target(args)

        result = actor.height({
            "shape": [
                self.origin,
                target,
            ],
            "range": args.get("range", True),
        })

        return {
            "status": "ok",
            "origin": self.origin,
            "target": target,
            "result": result,
        }

    def _test_expansion(self, actor: Actor, args: Dict[str, Any]) -> Dict[str, Any]:
        target = self._resolve_target(args)

        result = actor.expansion({
            "action": "route",
            "costing": args.get("costing", "pedestrian"),
            "locations": [
                self.origin,
                target,
            ],
            "expansion_properties": args.get(
                "properties",
                ["duration", "edge_id", "edge_status"],
            ),
        })

        return {
            "status": "ok",
            "origin": self.origin,
            "target": target,
            "algorithm": result.get("properties", {}).get("algorithm"),
            "edges": len(result.get("features", [])),
        }

