import json
import subprocess
from pathlib import Path
import requests

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

ARCGIS_BASE_URL = "https://YOUR_ARCGIS_URL/FeatureServer/0/query"

DATA_DIR = Path("/data")

GEOJSON_PATH = DATA_DIR / "sidewalks.geojson"
OSM_PATH = DATA_DIR / "sidewalks.osm"
PBF_PATH = DATA_DIR / "Sidewalks.osm.pbf"

VALHALLA_CONFIG = DATA_DIR / "valhalla.json"

PAGE_SIZE = 1000
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": "wayfinder-valhalla-bootstrap/1.0"
}

# -------------------------------------------------------------------
# Download ArcGIS GeoJSON using pagination
# -------------------------------------------------------------------

def download_geojson() -> dict:

    print("Downloading ArcGIS GeoJSON")

    features = []
    offset = 0

    while True:

        response = requests.get(
            ARCGIS_BASE_URL,
            headers=HEADERS,
            params={
                "where": "1=1",
                "outFields": "*",
                "outSR": "4326",
                "f": "geojson",
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

        if "features" not in payload:
            raise RuntimeError("ArcGIS response missing 'features'")

        batch = payload["features"]

        features.extend(batch)

        print(f"Downloaded {len(features)} features")

        if len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return {
        "type": "FeatureCollection",
        "features": features,
    }


# -------------------------------------------------------------------
# Save GeoJSON
# -------------------------------------------------------------------

def save_geojson(data: dict):

    print(f"Saving GeoJSON → {GEOJSON_PATH}")

    with open(GEOJSON_PATH, "w") as f:
        json.dump(data, f)


# -------------------------------------------------------------------
# Convert GeoJSON → OSM XML
# -------------------------------------------------------------------

def convert_geojson_to_osm():

    print("Converting GeoJSON → OSM XML")

    subprocess.run(
        [
            "ogr2ogr",
            "-f",
            "OSM",
            str(OSM_PATH),
            str(GEOJSON_PATH),
        ],
        check=True,
    )


# -------------------------------------------------------------------
# Convert OSM → PBF
# -------------------------------------------------------------------

def convert_osm_to_pbf():

    print("Converting OSM → PBF")

    subprocess.run(
        [
            "osmium",
            "cat",
            str(OSM_PATH),
            "-o",
            str(PBF_PATH),
        ],
        check=True,
    )


# -------------------------------------------------------------------
# Build Valhalla tiles
# -------------------------------------------------------------------

def build_valhalla_tiles():

    print("Building Valhalla tiles")

    subprocess.run(
        [
            "valhalla_build_tiles",
            "-c",
            str(VALHALLA_CONFIG),
            str(PBF_PATH),
        ],
        check=True,
    )


# -------------------------------------------------------------------
# Main pipeline
# -------------------------------------------------------------------

def main():

    print("==== Valhalla Tile Bootstrap ====")

    DATA_DIR.mkdir(exist_ok=True)

    # Skip build if tiles exist
    tiles_dir = DATA_DIR / "tiles"
    if tiles_dir.exists() and any(tiles_dir.rglob("*.gph")):
        print("Tiles already exist — skipping bootstrap")
        return

    geojson = download_geojson()

    save_geojson(geojson)

    convert_geojson_to_osm()

    convert_osm_to_pbf()

    build_valhalla_tiles()

    print("Valhalla bootstrap complete")


# -------------------------------------------------------------------

if __name__ == "__main__":
    main()