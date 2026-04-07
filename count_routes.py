"""
Count routable way/feature counts across GeoJSON, OSM XML, and PBF files.

Usage:
    python count_routes.py path/to/file.geojson
    python count_routes.py path/to/file.osm
    python count_routes.py path/to/file.osm.pbf
    python count_routes.py path/to/dir/   # scans all supported files in dir
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Highway values Valhalla considers routable for pedestrians
PEDESTRIAN_HIGHWAY_TAGS = {
    "footway", "path", "pedestrian", "steps", "sidewalk",
    "living_street", "residential", "service", "track",
    "unclassified", "tertiary", "secondary", "primary",
    "trunk", "motorway",  # included but usually blocked by access
}


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------

def count_geojson(path: Path) -> dict:
    with open(path) as f:
        data = json.load(f)

    features = data.get("features", [])
    total = len(features)
    pedestrian = 0
    with_incline = 0

    for feat in features:
        props = feat.get("properties") or {}
        hw = props.get("highway", "")
        if hw in PEDESTRIAN_HIGHWAY_TAGS:
            pedestrian += 1
        if "incline" in props:
            with_incline += 1

    return {
        "format": "GeoJSON",
        "total_features": total,
        "pedestrian_routable": pedestrian,
        "with_incline_tag": with_incline,
    }


# ---------------------------------------------------------------------------
# OSM XML
# ---------------------------------------------------------------------------

def count_osm_xml(path: Path) -> dict:
    total_ways = 0
    pedestrian = 0
    with_incline = 0
    nodes = 0
    relations = 0

    # Iterparse to avoid loading the whole file into memory
    for event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == "node":
            nodes += 1
            elem.clear()
        elif elem.tag == "relation":
            relations += 1
            elem.clear()
        elif elem.tag == "way":
            total_ways += 1
            tags = {t.get("k"): t.get("v") for t in elem.findall("tag")}
            if tags.get("highway") in PEDESTRIAN_HIGHWAY_TAGS:
                pedestrian += 1
            if "incline" in tags:
                with_incline += 1
            elem.clear()

    return {
        "format": "OSM XML",
        "nodes": nodes,
        "relations": relations,
        "total_ways": total_ways,
        "pedestrian_routable": pedestrian,
        "with_incline_tag": with_incline,
    }


# ---------------------------------------------------------------------------
# PBF  (requires osmium — pip install osmium)
# ---------------------------------------------------------------------------

def count_pbf(path: Path) -> dict:
    try:
        import osmium
    except ImportError:
        return {"error": "osmium not installed — run: pip install osmium"}

    class WayHandler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = 0
            self.total_ways = 0
            self.pedestrian = 0
            self.with_incline = 0
            self.relations = 0

        def node(self, n):
            self.nodes += 1

        def relation(self, r):
            self.relations += 1

        def way(self, w):
            self.total_ways += 1
            tags = {t.k: t.v for t in w.tags}
            if tags.get("highway") in PEDESTRIAN_HIGHWAY_TAGS:
                self.pedestrian += 1
            if "incline" in tags:
                self.with_incline += 1

    h = WayHandler()
    h.apply_file(str(path))

    return {
        "format": "PBF",
        "nodes": h.nodes,
        "relations": h.relations,
        "total_ways": h.total_ways,
        "pedestrian_routable": h.pedestrian,
        "with_incline_tag": h.with_incline,
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

HANDLERS = {
    ".geojson": count_geojson,
    ".json":    count_geojson,
    ".osm":     count_osm_xml,
    ".pbf":     count_pbf,
}


def count_file(path: Path) -> dict:
    suffix = path.suffix.lower()
    # Handle double extension e.g. .osm.pbf
    if path.name.endswith(".osm.pbf"):
        suffix = ".pbf"
    handler = HANDLERS.get(suffix)
    if not handler:
        return {"error": f"Unsupported format: {suffix}"}
    return {"file": str(path), **handler(path)}


def print_result(result: dict):
    print()
    for k, v in result.items():
        print(f"  {k:<25} {v:,}" if isinstance(v, int) else f"  {k:<25} {v}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])

    if target.is_dir():
        files = [
            p for p in sorted(target.rglob("*"))
            if p.suffix.lower() in HANDLERS or p.name.endswith(".osm.pbf")
        ]
        if not files:
            print(f"No supported files found in {target}")
            sys.exit(1)
        for f in files:
            print_result(count_file(f))
    else:
        print_result(count_file(target))