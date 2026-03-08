from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET


class GeoJSONToOSMService:

    SURFACE_MAP = {
        "concrete": "concrete",
        "asphalt": "asphalt",
        "brick": "paving_stones",
        "pavers": "paving_stones",
        "gravel": "gravel",
    }

    MIN_SEGMENT_LENGTH_M = 0.5

    @staticmethod
    def _safe_float(v):
        try:
            return float(v)
        except:
            return None

    @staticmethod
    def _segment_length(coords):

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371000
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)

            a = (
                math.sin(dphi / 2) ** 2
                + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
            )
            return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        total = 0
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            total += haversine(lat1, lon1, lat2, lon2)

        return total

    @classmethod
    def _normalize_properties(cls, props, length):
        """
        Experimental normalization layer.
        Only runs when normalization=True in convert().
        """

        tags = {}

        # Surface normalization
        material = props.get("Material")
        if material:
            material = material.lower().strip()
            surface = cls.SURFACE_MAP.get(material)
            if surface:
                tags["surface"] = surface

        # Width normalization
        width = cls._safe_float(props.get("Width"))
        if width and width > 0:
            tags["width"] = f"{width:.2f}"

        # Incline normalization
        grade = cls._safe_float(props.get("Grade"))

        if grade is None:
            zmin = cls._safe_float(props.get("Z_Min"))
            zmax = cls._safe_float(props.get("Z_Max"))

            if zmin is not None and zmax is not None:
                grade = ((zmax - zmin) / length) * 100

        if grade is not None:
            tags["incline"] = f"{grade:.1f}%"

        # Name normalization
        road = props.get("RoadName")
        if road and road.strip():
            tags["name"] = road.strip()

        return tags

    @classmethod
    def convert(cls, *, geojson_path: Path, osm_path: Path, normalize: bool = False):

        with open(geojson_path) as f:
            data = json.load(f)

        features = data.get("features", [])

        node_cache = {}
        ways = []

        node_id = 1
        way_id = 1

        # -----------------------------
        # PASS 1 — Structural filtering
        # -----------------------------

        for feature in features:

            geom = feature.get("geometry", {})
            props = feature.get("properties", {})

            if geom.get("type") != "LineString":
                continue

            coords = geom.get("coordinates", [])

            if len(coords) < 2:
                continue

            # Status filter
            if props.get("Status") and props.get("Status") != "Open":
                continue

            # Width filter
            width = cls._safe_float(props.get("Width"))
            if width is not None and width <= 0:
                continue

            # Geometry length filter
            length = cls._segment_length(coords)
            if length < cls.MIN_SEGMENT_LENGTH_M:
                continue

            way_nodes = []

            for lon, lat in coords:

                lon = cls._safe_float(lon)
                lat = cls._safe_float(lat)

                if lon is None or lat is None:
                    continue

                key = (round(lon, 6), round(lat, 6))

                if key not in node_cache:
                    node_cache[key] = node_id
                    node_id += 1

                way_nodes.append(node_cache[key])

            if len(way_nodes) < 2:
                continue

            ways.append((way_id, way_nodes, props, length))
            way_id += 1

        # -----------------------------
        # BUILD OSM XML
        # -----------------------------

        osm = ET.Element("osm", version="0.6", generator="wayfinder")

        # Write nodes
        for (lon, lat), nid in node_cache.items():

            ET.SubElement(
                osm,
                "node",
                id=str(nid),
                lon=str(lon),
                lat=str(lat),
                visible="true",
            )

        # Write ways
        for wid, node_ids, props, length in ways:

            way = ET.SubElement(osm, "way", id=str(wid), visible="true")

            for nid in node_ids:
                ET.SubElement(way, "nd", ref=str(nid))

            tags = {
                "highway": "footway",
                "footway": "sidewalk",
                "foot": "yes",
            }

            if normalize:
                tags.update(cls._normalize_properties(props, length))

            for k, v in tags.items():
                ET.SubElement(way, "tag", k=k, v=str(v))

        osm_path.parent.mkdir(parents=True, exist_ok=True)

        tree = ET.ElementTree(osm)
        tree.write(osm_path, encoding="utf-8", xml_declaration=True)