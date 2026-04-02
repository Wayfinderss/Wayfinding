from pathlib import Path
import ijson


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
        except Exception:
            return None

    @classmethod
    def _normalize_properties(cls, props, length):

        tags = {}

        # ----- Surface -----
        material = props.get("Material")
        if material:
            material = material.lower().strip()
            surface = cls.SURFACE_MAP.get(material)
            if surface:
                tags["surface"] = surface

        # ----- Width -----
        width = cls._safe_float(props.get("Width"))
        if width and width > 0:
            tags["width"] = f"{width:.2f}"

        # ----- Grade / Incline -----
        grade = cls._safe_float(props.get("Grade"))

        if grade is None:
            zmin = cls._safe_float(props.get("Z_Min"))
            zmax = cls._safe_float(props.get("Z_Max"))

            if zmin is not None and zmax is not None and length > 0:
                grade = ((zmax - zmin) / length) * 100

        if grade is not None:
            tags["incline"] = f"{grade:.1f}%"

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

    @classmethod
    def convert(
        cls,
        *,
        geojson_path: Path,
        osm_path: Path,
        normalize: bool = True,
        node_id_base: int = 0,
        way_id_base: int = 0,
    ):

        node_cache = {}
        ways = []

        # When chunk-building tiles, multiple converted PBFs are merged together.
        # If node/way IDs overlap across chunks, `osmium merge --overwrite` can drop
        # earlier objects. Offsetting IDs per chunk keeps merges deterministic.
        node_id = node_id_base + 1
        way_id = way_id_base + 1

        with open(geojson_path, "rb") as f:

            features = ijson.items(f, "features.item")

            for feature in features:

                geom = feature.get("geometry", {})
                props = feature.get("properties", {})

                if geom.get("type") != "LineString":
                    continue

                coords = geom.get("coordinates", [])

                if len(coords) < 2:
                    continue

                # status filter (case-insensitive; preserves prior behavior of only
                # filtering when the field is present and non-empty)
                status = props.get("Status")
                if status:
                    if str(status).strip().lower() != "open":
                        continue

                length = cls._safe_float(props.get("Feet")) * 0.3048

                way_nodes = []
                valid = True

                for lon, lat in coords:

                    lon = cls._safe_float(lon)
                    lat = cls._safe_float(lat)

                    if lon is None or lat is None:
                        valid = False
                        break

                    # quantized key (fast hash)
                    key = (int(lon * 1e6), int(lat * 1e6))

                    if key not in node_cache:
                        node_cache[key] = node_id
                        node_id += 1

                    way_nodes.append(node_cache[key])

                if not valid or len(way_nodes) < 2:
                    continue

                ways.append((way_id, way_nodes, props, length))
                way_id += 1

        osm_path.parent.mkdir(parents=True, exist_ok=True)

        with open(osm_path, "w", encoding="utf-8") as out:

            out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            out.write('<osm version="0.6" generator="wayfinder">\n')

            # write nodes
            for (lon_i, lat_i), nid in node_cache.items():

                lon = lon_i / 1e6
                lat = lat_i / 1e6

                out.write(
                    f'<node id="{nid}" lon="{lon}" lat="{lat}" visible="true"/>\n'
                )

            # write ways
            for wid, node_ids, props, length in ways:

                out.write(f'<way id="{wid}" visible="true">\n')

                for nid in node_ids:
                    out.write(f'<nd ref="{nid}"/>\n')

                tags = {
                    "highway": "footway",
                    "footway": "sidewalk",
                    "foot": "yes",
                }

                if normalize:
                    tags.update(cls._normalize_properties(props, length))

                import html

                for k, v in tags.items():
                    k = html.escape(str(k), quote=True)
                    v = html.escape(str(v), quote=True)
                    out.write(f'<tag k="{k}" v="{v}"/>\n')

                out.write("</way>\n")

            out.write("</osm>\n")