from pathlib import Path
import subprocess
import tempfile
import textwrap


class GeoJSONToOSMService:

    TRANSLATION_SCRIPT = """
import ogr2osm

class WayfinderTranslation(ogr2osm.TranslationBase):

    def filter_tags(self, attrs):
        if not attrs:
            return {}

        tags = {}
        type_name = (attrs.get("Type_Name") or "").lower()

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

        status = (attrs.get("Status") or "").lower()
        if status == "open":
            tags["foot"] = "yes"
        elif status:
            tags["foot"] = "no"
            tags["access"] = "private"

        material = (attrs.get("Material") or "").lower()
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

        road = attrs.get("RoadName")
        if road:
            tags["name"] = road

        return tags
"""

    @classmethod
    def convert(
        cls,
        *,
        geojson_path: Path,
        osm_path: Path,
        node_id_base: int = 1,
        way_id_base: int = 1,
    ) -> None:
        osm_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        ) as translation_file:
            translation_file.write(textwrap.dedent(cls.TRANSLATION_SCRIPT))
            translation_path = translation_file.name

        result = subprocess.run(
            [
                "ogr2osm",
                str(geojson_path),
                "-t", translation_path,
                "-o", str(osm_path),
                "-f",
                "--positive-id",
                "--id", str(node_id_base + 1),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ogr2osm failed (exit {result.returncode}):\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )