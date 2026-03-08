from wayfinder.application.tile_build_pipeline import TileBuildPipeline
from concurrent.futures import ThreadPoolExecutor, as_completed
from wayfinder.config.paths import (
    CUSTOM_GEOJSON_PATH,
    TILES_DIR,
    VALHALLA_CONFIG_PATH,
    VALHALLA_DATA_DIR,
)

import shutil
import json
import time
import requests

from engines.valhalla_engine.config_builder import ValhallaConfigBuilder


MAX_RETRIES = 5

ARCGIS_BASE_URL = (
    "https://services3.arcgis.com/MV5wh5WkCMqlwISp/arcgis/rest/services/"
    "Sidewalks/FeatureServer/0/query"
)

REQUEST_TIMEOUT_SECONDS = 60
OBJECT_ID_CHUNK_SIZE = 200


def generate_config_file():

    builder = ValhallaConfigBuilder(
        tiles_dir=TILES_DIR,
    )

    config_path = builder.write(VALHALLA_CONFIG_PATH)

    print(f"Valhalla config generated: {config_path}")

    return config_path


def _load_existing_geojson():

    if not CUSTOM_GEOJSON_PATH.exists():
        return None

    try:
        data = json.loads(CUSTOM_GEOJSON_PATH.read_text())
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    if "features" not in data:
        return None

    return data


def _fetch_object_ids():

    r = requests.get(
        ARCGIS_BASE_URL,
        params={
            "where": "1=1",
            "returnIdsOnly": "true",
            "f": "json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    r.raise_for_status()

    payload = r.json()

    object_ids = payload.get("objectIds", [])

    if not object_ids:
        raise RuntimeError("No object IDs returned")

    return sorted(object_ids)


def _fetch_geojson_chunk(ids):

    where = f"OBJECTID IN ({','.join(str(i) for i in ids)})"

    params = {
        "where": where,
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
    }

    for attempt in range(MAX_RETRIES):

        r = requests.get(
            ARCGIS_BASE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        try:
            r.raise_for_status()
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 ** attempt)
            continue

        if "application/json" not in r.headers.get("content-type", ""):
            time.sleep(2 ** attempt)
            continue

        try:
            payload = r.json()
        except Exception:
            time.sleep(2 ** attempt)
            continue

        return payload

    raise RuntimeError("Chunk fetch failed")


def _download_all_geojson():

    object_ids = _fetch_object_ids()

    print(f"Found {len(object_ids)} ArcGIS features")

    chunks = [
        object_ids[i:i + OBJECT_ID_CHUNK_SIZE]
        for i in range(0, len(object_ids), OBJECT_ID_CHUNK_SIZE)
    ]

    all_features = []

    with ThreadPoolExecutor(max_workers=16) as executor:

        futures = [
            executor.submit(_fetch_geojson_chunk, chunk)
            for chunk in chunks
        ]

        for future in as_completed(futures):

            payload = future.result()

            all_features.extend(payload.get("features", []))

    return {
        "type": "FeatureCollection",
        "features": all_features,
    }


def generate_json(force=False):

    if not force:

        existing = _load_existing_geojson()

        if existing:
            print("GeoJSON already exists")
            return existing

    print("Downloading ArcGIS sidewalks")

    data = _download_all_geojson()

    CUSTOM_GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    CUSTOM_GEOJSON_PATH.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    print(f"Saved {len(data['features'])} features")

    return data


def tiles_exist():

    return TILES_DIR.exists() and any(TILES_DIR.rglob("*.gph"))


def main():

    print("==== Valhalla Tile Bootstrap ====")

    VALHALLA_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for item in VALHALLA_DATA_DIR.iterdir():

        if item.is_file() or item.is_symlink():
            item.unlink()

        elif item.is_dir():
            shutil.rmtree(item)

    if not VALHALLA_CONFIG_PATH.exists():

        print("Generating Valhalla config")

        generate_config_file()

    generate_json()

    if tiles_exist():

        print("Tiles already exist")

        return

    result = TileBuildPipeline().run(
        geojson_path=CUSTOM_GEOJSON_PATH,
        force=False,
    )

    print("Tiles built")

    print(result)


if __name__ == "__main__":
    main()