from wayfinder.application.tile_build_pipeline import TileBuildPipeline
from wayfinder.application.geohash_spitter_pipeline import GeohasherSplittingPipeline
from concurrent.futures import ThreadPoolExecutor, as_completed
from wayfinder.config.paths import (
    CUSTOM_GEOJSON_PATH,
    CHUNKS_DIR,
    TILES_DIR,
    VALHALLA_CONFIG_PATH,
    VALHALLA_DATA_DIR,
)

import argparse
import shutil
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from engines.valhalla_engine.config_builder import ValhallaConfigBuilder


MAX_RETRIES = 5
MAX_WORKERS = 32
OBJECT_ID_CHUNK_SIZE = 200
REQUEST_TIMEOUT_SECONDS = 60

ARCGIS_BASE_URL = (
    "https://services3.arcgis.com/MV5wh5WkCMqlwISp/arcgis/rest/services/"
    "Sidewalks/FeatureServer/0/query"
)


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        read=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist={500, 502, 503, 504},
        allowed_methods={"GET"},
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _make_session()


def generate_config_file():
    builder = ValhallaConfigBuilder(tiles_dir=TILES_DIR)
    config_path = builder.write(VALHALLA_CONFIG_PATH)
    print(f"Valhalla config generated: {config_path}")
    return config_path


def _geojson_is_valid() -> bool:
    if not CUSTOM_GEOJSON_PATH.exists():
        return False
    try:
        head = CUSTOM_GEOJSON_PATH.read_bytes()[:256].decode("utf-8", errors="ignore")
        return "FeatureCollection" in head and "features" in head
    except Exception:
        return False


def _load_existing_geojson():
    try:
        return json.loads(CUSTOM_GEOJSON_PATH.read_text())
    except Exception:
        return None


def _fetch_object_ids(session: requests.Session) -> list[int]:
    params = {"where": "1=1", "returnIdsOnly": "true", "f": "json"}
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(ARCGIS_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            r.raise_for_status()
            object_ids = r.json().get("objectIds") or []
            if not object_ids:
                raise RuntimeError("No object IDs returned")
            return sorted(object_ids)
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            print(f"Failed to fetch object IDs ({exc}), retrying in {wait}s…")
            time.sleep(wait)
    raise RuntimeError("_fetch_object_ids failed after all retries")


def _fetch_geojson_chunk(session: requests.Session, ids: list[int]) -> list:
    where = f"OBJECTID IN ({','.join(map(str, ids))})"
    params = {"where": where, "outFields": "*", "outSR": "4326", "f": "geojson"}

    for attempt in range(MAX_RETRIES):
        try:
            r = _SESSION.get(ARCGIS_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            r.raise_for_status()
            if "application/json" not in r.headers.get("content-type", ""):
                raise ValueError(f"Unexpected content-type: {r.headers.get('content-type')}")
            return r.json().get("features", [])
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            print(f"Chunk {ids[0]}–{ids[-1]} failed ({exc}), retrying in {wait}s…")
            time.sleep(wait)

    raise RuntimeError("Chunk fetch failed after all retries")


def _download_all_geojson(session: requests.Session) -> dict:
    object_ids = _fetch_object_ids(session)
    print(f"Found {len(object_ids)} ArcGIS features")

    chunks = [
        object_ids[i : i + OBJECT_ID_CHUNK_SIZE]
        for i in range(0, len(object_ids), OBJECT_ID_CHUNK_SIZE)
    ]

    all_features: list = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_geojson_chunk, session, chunk): chunk for chunk in chunks}
        for future in as_completed(futures):
            try:
                all_features.extend(future.result())
            except Exception as exc:
                chunk = futures[future]
                raise RuntimeError(f"Failed on chunk starting at {chunk[0]}") from exc

    return {"type": "FeatureCollection", "features": all_features}


def generate_json(force: bool = False) -> dict:
    if not force and _geojson_is_valid():
        print("GeoJSON already exists, loading from disk")
        return _load_existing_geojson()

    print("Downloading ArcGIS sidewalks…")
    data = _download_all_geojson(_SESSION)

    CUSTOM_GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    CUSTOM_GEOJSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved {len(data['features'])} features → {CUSTOM_GEOJSON_PATH}")

    return data


def tiles_exist() -> bool:
    return TILES_DIR.exists() and any(TILES_DIR.rglob("*.gph"))


def _clear_valhalla_data():
    """Only wipe files/dirs that aren't the config, to survive partial re-runs."""
    for item in VALHALLA_DATA_DIR.iterdir():
        if item == VALHALLA_CONFIG_PATH:
            continue
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Valhalla tiles")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force a full rebuild: wipe derived data and redownload/reconvert everything.",
    )
    args = parser.parse_args()

    print("==== Valhalla Tile Bootstrap ====")

    VALHALLA_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not VALHALLA_CONFIG_PATH.exists():
        print("Generating Valhalla config")
        generate_config_file()

    if tiles_exist() and not args.rebuild:
        print("Tiles already exist, skipping bootstrap")
        return

    if args.rebuild:
        _clear_valhalla_data()

    data = generate_json(force=args.rebuild)

    statuses = {f.get("properties", {}).get("Status") for f in data["features"]}
    print(f"Status values in dataset: {statuses}")

    chunks = GeohasherSplittingPipeline(precision=16, skip_closed=False).run(data)
    total_features = sum(len(v) for v in chunks.values())
    print(f"Splitter: {len(chunks)} buckets, {total_features} features")

    pipeline = TileBuildPipeline()
    result = pipeline.run(chunks=chunks, force=args.rebuild)
    print("Tiles built")
    print(result)


if __name__ == "__main__":
    main()