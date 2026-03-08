from pathlib import Path
import json
import xml.etree.ElementTree as ET


class GeoJSONToOSMService:

    @staticmethod
    def _safe_float(v):
        try:
            return float(v)
        except:
            return None

    @classmethod
    def convert(cls, *, geojson_path: Path, osm_path: Path):

        with open(geojson_path) as f:
            data = json.load(f)

        features = data.get("features", [])

        node_cache = {}
        ways = []

        node_id = 1
        way_id = 1

        # -----------------------------
        # PASS 1: collect nodes + ways
        # -----------------------------

        for feature in features:

            geom = feature.get("geometry", {})
            props = feature.get("properties", {})

            if geom.get("type") != "LineString":
                continue

            coords = geom.get("coordinates", [])
            way_nodes = []

            for coord in coords:

                lon = cls._safe_float(coord[0])
                lat = cls._safe_float(coord[1])

                if lon is None or lat is None:
                    continue

                key = (round(lon, 6), round(lat, 6))

                if key not in node_cache:
                    node_cache[key] = node_id
                    node_id += 1

                way_nodes.append(node_cache[key])

            if len(way_nodes) < 2:
                continue

            ways.append((way_id, way_nodes, props))
            way_id += 1

        # -----------------------------
        # BUILD OSM XML
        # -----------------------------

        osm = ET.Element("osm", version="0.6", generator="wayfinder")

        # WRITE ALL NODES FIRST
        for (lon, lat), nid in node_cache.items():

            ET.SubElement(
                osm,
                "node",
                id=str(nid),
                lon=str(lon),
                lat=str(lat),
                visible="true",
            )

        # WRITE ALL WAYS SECOND
        for wid, node_ids, props in ways:

            way = ET.SubElement(osm, "way", id=str(wid), visible="true")

            for nid in node_ids:
                ET.SubElement(way, "nd", ref=str(nid))

            tags = {
                "highway": "footway",
                "foot": "yes",
                "footway": "sidewalk",
                "source": "WestmorelandCountyGIS",
            }

            if props.get("RoadName"):
                tags["name"] = props["RoadName"]

            if props.get("Material"):
                tags["surface"] = str(props["Material"]).lower()

            if props.get("Width"):
                tags["width"] = str(props["Width"])

            if props.get("Grade"):
                tags["incline"] = f"{props['Grade']}%"

            for k, v in tags.items():
                ET.SubElement(way, "tag", k=k, v=str(v))

        osm_path.parent.mkdir(parents=True, exist_ok=True)

        tree = ET.ElementTree(osm)
        tree.write(osm_path, encoding="utf-8", xml_declaration=True)