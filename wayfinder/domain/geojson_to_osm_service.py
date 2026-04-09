"""
Converts GeoJSON features to OSM XML.

Single implementation used for both bootstrap (full dataset) and CRUD
(individual way updates). Uses numpy for vectorised elevation interpolation
and streams OSM XML directly to disk — fast enough for 350k+ features.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import numpy as np

from wayfinder.domain.node_registry import NodeRegistry


# Equirectangular distance constants for Pittsburgh (~40.44°N).
_LAT_M_PER_DEG = 111_320.0
_LON_M_PER_DEG = 111_320.0 * math.cos(math.radians(40.44))

_TIMESTAMP = "1970-01-01T00:00:01Z"
_XML_QUOTE = {'"': '&quot;', "'": '&apos;'}


def _xesc(value: str) -> str:
    """Escape XML special chars including double quotes for use in attributes."""
    return xml_escape(value, _XML_QUOTE)


# ---------------------------------------------------------------------------
# Tag translation
# ---------------------------------------------------------------------------

def tags_from_properties(attrs: dict) -> dict:
    if not attrs:
        return {}

    attrs = {k: (v.lower() if isinstance(v, str) else v) for k, v in attrs.items()}

    tags = {}
    type_name = attrs.get("Type_Name") or ""

    if type_name == "sidewalk":
        tags["highway"] = "footway"
        tags["footway"] = "sidewalk"
    elif type_name == "crosswalk":
        tags["highway"] = "footway"
        tags["footway"] = "crossing"
        tags["crossing"] = "marked"
    elif type_name == "raised crosswalk":
        tags["highway"] = "footway"
        tags["footway"] = "crossing"
        tags["crossing"] = "marked"
        tags["traffic_calming"] = "table"
    elif type_name == "steps":
        tags["highway"] = "steps"
    elif type_name == "trail":
        tags["highway"] = "path"
        tags["foot"] = "designated"
    elif type_name == "on-street walkway":
        tags["highway"] = "footway"
    else:
        tags["highway"] = "footway"

    status = attrs.get("Status") or ""
    if status == "open":
        tags["foot"] = "yes"
    elif status:
        tags["foot"] = "no"
        tags["access"] = "private"

    material = attrs.get("Material") or ""
    surface_map = {
        "concrete": "concrete",
        "asphalt": "asphalt",
        "brick": "paving_stones",
        "pavers": "paving_stones",
        "gravel": "gravel",
    }
    if material in surface_map:
        tags["surface"] = surface_map[material]

    width = attrs.get("Width")
    if width and int(width) > 0:
        tags["width"] = str(width)

    grade = attrs.get("Grade")
    if grade:
        tags["incline"] = f"{grade}%"

        # accessibility hint
        if grade <= 5:
            tags["wheelchair"] = "yes"
        elif grade <= 8:
            tags["wheelchair"] = "limited"
        else:
            tags["wheelchair"] = "no"

        # ----- Road name -----
        road = props.get("RoadName")
        if road and road.strip():
            tags["name"] = road.strip()

        # ----- Sidewalk classification -----
        type_name = props.get("Type_Name")
        if type_name and type_name.lower() == "sidewalk":
            tags["footway"] = "sidewalk"

        # ----- Access status -----
        status = props.get("Status")
        if status:
            if status.lower() == "open":
                tags["foot"] = "yes"
            else:
                tags["foot"] = "no"
                tags["access"] = "private"

        # ----- Lighting -----
        lighting = props.get("Lighting")
        if lighting:
            if str(lighting).lower() in ("yes", "true", "1"):
                tags["lit"] = "yes"

        # ----- Smoothness -----
        condition = props.get("Condition")
        if condition:
            condition = condition.lower()
            if "good" in condition:
                tags["smoothness"] = "good"
            elif "fair" in condition:
                tags["smoothness"] = "intermediate"
            elif "poor" in condition:
                tags["smoothness"] = "bad"

        # ----- Curb ramps -----
        curb = props.get("CurbRamp")
        if curb:
            if str(curb).lower() in ("yes", "true", "1"):
                tags["kerb"] = "lowered"
            else:
                tags["kerb"] = "raised"

        # ----- Debug notes (optional) -----
        notes = props.get("Notes")
        if notes and notes.strip():
            tags["note"] = notes.strip()

    return tags


# ---------------------------------------------------------------------------
# Elevation interpolation (vectorised)
# ---------------------------------------------------------------------------

def _interpolate_elevations(
    lons: np.ndarray,
    lats: np.ndarray,
    z_min: float,
    z_max: float,
    grade: float,
) -> np.ndarray:
    """
    Assign an elevation (metres) to each coordinate along a way.
    Accepts numpy arrays for lons/lats — vectorised, no Python loop.

    Z_Min / Z_Max are in feet. Grade is a percentage.
    """
    ft_to_m = 0.3048
    start_ele = z_min * ft_to_m
    end_ele = z_max * ft_to_m
    grade_frac = grade / 100.0

    dlat = np.diff(lats) * _LAT_M_PER_DEG
    dlon = np.diff(lons) * _LON_M_PER_DEG
    dists = np.sqrt(dlat ** 2 + dlon ** 2)
    rises = grade_frac * dists

    eles = np.empty(len(lons))
    eles[0] = start_ele
    for i in range(1, len(lons)):
        eles[i] = min(eles[i - 1] + rises[i - 1], end_ele)

    return eles


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class GeoJSONToOSMService:

    @classmethod
    def convert(
        cls,
        *,
        geojson_path: Path,
        osm_path: Path,
        registry: NodeRegistry,
    ) -> None:
        """
        Convert a full GeoJSON FeatureCollection to OSM XML.
        Used by bootstrap. Delegates to convert_features().
        """
        # ujson is ~3x faster than stdlib json for large files; fall back
        # gracefully if not installed.
        try:
            import ujson
            data = ujson.loads(geojson_path.read_bytes())
        except ImportError:
            data = json.loads(geojson_path.read_text())

        features = data.get("features", [])
        cls.convert_features(features=features, osm_path=osm_path, registry=registry)

    @classmethod
    def convert_features(
        cls,
        *,
        features: list[dict],
        osm_path: Path,
        registry: NodeRegistry,
    ) -> None:
        """
        Convert a list of GeoJSON features to OSM XML.

        - Loads registry into memory for O(1) node ID lookups
        - Uses numpy for vectorised elevation interpolation
        - Streams XML directly to disk — no in-memory element tree
        """
        osm_path.parent.mkdir(parents=True, exist_ok=True)

        total = len(features)

        # Load existing nodes into memory for fast in-process lookups
        mem: dict[tuple[float, float], int] = registry.load_into_memory()
        next_id: int = registry.next_node_id()
        new_nodes: dict[tuple[float, float], int] = {}

        def _get_or_create(lon: float, lat: float) -> int:
            nonlocal next_id
            key = (round(lon, 7), round(lat, 7))
            nid = mem.get(key)
            if nid is not None:
                return nid
            nid = new_nodes.get(key)
            if nid is not None:
                return nid
            nid = next_id
            next_id += 1
            new_nodes[key] = nid
            mem[key] = nid
            return nid

        coord_to_id: dict[tuple[float, float], int] = {}
        coord_to_ele: dict[tuple[float, float], float] = {}
        way_data: list[tuple[int, list[int], dict]] = []

        for i, feature in enumerate(features):
            if i % 25_000 == 0 and i > 0:
                print(f"  Converting features: {i:,} / {total:,}")

            props = feature.get("properties") or {}
            geom = feature.get("geometry") or {}
            coords = cls._flatten_coords(geom)
            if not coords:
                continue

            object_id = props.get("OBJECTID") or props.get("objectid")
            way_id = (
                registry.way_id_for_object(int(object_id))
                if object_id
                else registry._next_id("next_way_id")
            )

            lons_arr = np.array([c[0] for c in coords], dtype=np.float64)
            lats_arr = np.array([c[1] for c in coords], dtype=np.float64)

            z_min = float(props.get("Z_Min") or 0.0)
            z_max = float(props.get("Z_Max") or 0.0)
            grade = float(props.get("Grade") or 0.0)

            # Guard against NaN/inf from bad source data
            if not all(math.isfinite(v) for v in (z_min, z_max, grade)):
                z_min, z_max, grade = 0.0, 0.0, 0.0

            eles = _interpolate_elevations(lons_arr, lats_arr, z_min, z_max, grade)

            node_ids = []
            for (lon, lat), ele in zip(coords, eles.tolist()):
                key = (round(lon, 7), round(lat, 7))
                nid = _get_or_create(lon, lat)
                if key not in coord_to_id:
                    coord_to_id[key] = nid
                    coord_to_ele[key] = ele
                node_ids.append(nid)

            way_data.append((way_id, node_ids, tags_from_properties(props)))

        # Flush new nodes to registry in one batch
        if new_nodes:
            registry._conn.execute(
                "UPDATE counters SET value = ? WHERE name = 'next_node_id'",
                (next_id,),
            )
            registry.bulk_insert(new_nodes)
            print(f"  Registry: {len(new_nodes):,} new nodes, {len(mem):,} total")

        # Stream OSM XML to disk
        print(f"  Writing OSM XML ({len(coord_to_id):,} nodes, {len(way_data):,} ways)…")
        with open(osm_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<osm version="0.6" generator="wayfinder">\n')

            for (lon, lat), node_id in coord_to_id.items():
                ele = coord_to_ele.get((lon, lat))
                if ele is not None and math.isfinite(ele):
                    f.write(
                        f'  <node id="{node_id}" lat="{lat}" lon="{lon}"'
                        f' version="1" timestamp="{_TIMESTAMP}" visible="true">\n'
                        f'    <tag k="ele" v="{round(ele, 2)}"/>\n'
                        f'  </node>\n'
                    )
                else:
                    f.write(
                        f'  <node id="{node_id}" lat="{lat}" lon="{lon}"'
                        f' version="1" timestamp="{_TIMESTAMP}" visible="true"/>\n'
                    )

            for way_id, node_ids, tags in way_data:
                f.write(
                    f'  <way id="{way_id}" version="1"'
                    f' timestamp="{_TIMESTAMP}" visible="true">\n'
                )
                for nid in node_ids:
                    f.write(f'    <nd ref="{nid}"/>\n')
                for k, v in tags.items():
                    f.write(f'    <tag k="{_xesc(k)}" v="{_xesc(str(v))}"/>\n')
                f.write('  </way>\n')

            f.write('</osm>\n')

    @staticmethod
    def _flatten_coords(geom: dict) -> list[tuple[float, float]]:
        gtype = geom.get("type", "")
        coords = geom.get("coordinates", [])
        if gtype == "LineString":
            return [(c[0], c[1]) for c in coords]
        if gtype == "MultiLineString":
            return [(c[0], c[1]) for line in coords for c in line]
        return []