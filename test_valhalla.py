from pathlib import Path
from valhalla import Actor


CONFIG_PATH = Path(__file__).parent / "valhalla.json"


def load_actor() -> Actor:
    """
    Load Valhalla Actor using the provided config.
    This will immediately fail if the config is invalid.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing valhalla.json at {CONFIG_PATH}")

    print("Loading Valhalla Actor...")
    actor = Actor(str(CONFIG_PATH))
    print("✓ Valhalla Actor loaded successfully\n")
    return actor


def test_route(actor: Actor):
    print("=== ROUTE TEST ===")
    result = actor.route({
        "costing": "pedestrian",
        "locations": [
            {"lat": 42.5078, "lon": 1.5211},
            {"lat": 42.5063, "lon": 1.5289}
        ]
    })

    summary = result["trip"]["summary"]
    print("Route summary:", summary, "\n")


def test_isochrone(actor: Actor):
    print("=== ISOCHRONE TEST ===")
    result = actor.isochrone({
        "locations": [
            {"lat": 42.5078, "lon": 1.5211}
        ],
        "costing": "pedestrian",
        "contours": [
            {"time": 5, "color": "ff0000"}
        ],
        "polygons": True
    })

    print("Isochrone feature count:", len(result["features"]), "\n")


def test_matrix(actor: Actor):
    print("=== MATRIX TEST ===")
    result = actor.matrix({
        "costing": "pedestrian",
        "sources": [
            {"lat": 42.5078, "lon": 1.5211}
        ],
        "targets": [
            {"lat": 42.5063, "lon": 1.5289}
        ]
    })

    print("Matrix result:", result, "\n")


def test_height(actor: Actor):
    print("=== HEIGHT TEST ===")
    result = actor.height({
        "shape": [
            {"lat": 42.5078, "lon": 1.5211},
            {"lat": 42.5063, "lon": 1.5289}
        ],
        "range": True
    })

    print("Height result:", result, "\n")


def test_expansion(actor: Actor):
    print("=== EXPANSION TEST ===")
    result = actor.expansion({
        "action": "route",
        "costing": "pedestrian",
        "locations": [
            {"lat": 42.5078, "lon": 1.5211},
            {"lat": 42.5063, "lon": 1.5289}
        ],
        "expansion_properties": [
            "duration",
            "edge_id",
            "edge_status"
        ]
    })

    algo = result.get("properties", {}).get("algorithm")
    print("Expansion algorithm:", algo)
    print("Expanded edges:", len(result.get("features", [])), "\n")


def main():
    actor = load_actor()

    # Run tests one by one so failures are obvious
    test_route(actor)
    test_isochrone(actor)
    test_matrix(actor)
    test_height(actor)
    test_expansion(actor)

    print("🎉 ALL VALHALLA TESTS PASSED 🎉")


if __name__ == "__main__":
    main()
