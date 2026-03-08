from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any


class GeoJSONToOSMService:
    """
    Stateless transformation service.
    Converts sidewalk GeoJSON into OSM XML.
    """

    @staticmethod
    def filter_features_by_grade(
        features: list[Dict[str, Any]],
        *,
        max_grade: float | None = None,
        min_grade: float | None = None,
    ) -> list[Dict[str, Any]]:
        """
        Filter GeoJSON features based on incline (Grade property).

        Args:
            features: List of GeoJSON feature dicts
            max_grade: Maximum allowed grade percentage
            min_grade: Minimum allowed grade percentage

        Returns:
            Filtered list of features
        """
        filtered = []

        for feature in features:
            props = feature.get("properties", {})
            grade = props.get("Grade")

            if grade is None:
                continue

            try:
                grade = float(grade)
            except (ValueError, TypeError):
                continue

            if max_grade is not None and grade > max_grade:
                continue

            if min_grade is not None and grade < min_grade:
                continue

            filtered.append(feature)

        return filtered

    @staticmethod
    def convert(
        geojson_path: Path,
        osm_path: Path,
        *,
        max_grade: float | None = None,
        min_grade: float | None = None,
    ) -> None:
        """
        Convert GeoJSON sidewalk data to OSM XML format.

        Args:
            geojson_path: Path to input GeoJSON file
            osm_path: Path to output OSM XML file
            max_grade: Optional maximum allowed incline %
            min_grade: Optional minimum allowed incline %
        """
        with open(geojson_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)

        features = data.get("features", [])

        if max_grade is not None or min_grade is not None:
            features = GeoJSONToOSMService.filter_features_by_grade(
                features,
                max_grade=max_grade,
                min_grade=min_grade,
            )

        node_id = -1
        way_id = -1
        node_cache: dict[str, int] = {}
        nodes: list[dict[str, str]] = []
        ways: list[dict[str, Any]] = []

        for feature in features:
            geom = feature.get("geometry", {})
            props = feature.get("properties", {})

            if geom.get("type") != "LineString":
                continue

            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue

            way_nodes: list[int] = []

            for coord in coords:
                if not isinstance(coord, (list, tuple)) or len(coord) < 2:
                    continue

                try:
                    lon = float(coord[0])
                    lat = float(coord[1])
                except (TypeError, ValueError):
                    continue

                coord_key = f"{lon:.7f},{lat:.7f}"

                if coord_key not in node_cache:
                    node_cache[coord_key] = node_id
                    nodes.append(
                        {
                            "id": str(node_id),
                            "lat": f"{lat:.7f}",
                            "lon": f"{lon:.7f}",
                        }
                    )
                    node_id -= 1

                way_nodes.append(node_cache[coord_key])

            if len(way_nodes) < 2:
                continue

            tags: list[tuple[str, str]] = [
                ("highway", "footway"),
                ("foot", "yes"),
            ]

            if props.get("Type_Name") == "Sidewalk":
                tags.append(("footway", "sidewalk"))

            road_name = str(props.get("RoadName", "")).strip()
            if road_name:
                tags.append(("name", road_name))

            try:
                width = float(props.get("Width", 0))
                if width > 0:
                    tags.append(("width", str(width)))
            except (TypeError, ValueError):
                pass

            material = str(props.get("Material", "")).strip().lower()
            tags.append(("surface", material or "paved"))

            try:
                grade = props.get("Grade")
                if grade is not None:
                    tags.append(("incline", f"{float(grade):.1f}%"))
            except (TypeError, ValueError):
                pass

            tags.append(("source", "Westmoreland County GIS"))

            ways.append(
                {
                    "id": str(way_id),
                    "nodes": way_nodes,
                    "tags": tags,
                }
            )
            way_id -= 1

        osm = ET.Element("osm", version="0.6", generator="wayfinder")

        for node in nodes:
            ET.SubElement(
                osm,
                "node",
                id=node["id"],
                lat=node["lat"],
                lon=node["lon"],
                visible="true",
            )

        for way_data in ways:
            way = ET.SubElement(osm, "way", id=way_data["id"], visible="true")

            for node_ref in way_data["nodes"]:
                ET.SubElement(way, "nd", ref=str(node_ref))

            for key, value in way_data["tags"]:
                ET.SubElement(way, "tag", k=key, v=value)

        osm_path.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(osm).write(
            osm_path,
            encoding="utf-8",
            xml_declaration=True,
        )