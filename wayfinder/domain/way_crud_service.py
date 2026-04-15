"""
CRUD operations for individual ways in the Valhalla network.

Each operation:
  1. Updates the canonical network.osm.pbf on disk
  2. Triggers a full Valhalla tile rebuild via the internal rebuild server
     running inside the valhalla container (POST http://valhalla:9001/rebuild)

Flow per operation:
  Add / Update  →  convert feature → OSM → PBF, merge into network PBF, rebuild tiles
  Delete        →  filter way out of network PBF by way ID, rebuild tiles
"""

from __future__ import annotations

import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from wayfinder.config.paths import (
    NETWORK_PBF_PATH,
    NODE_REGISTRY_PATH,
    VALHALLA_DATA_DIR,
)
from wayfinder.domain.geojson_to_osm_service import GeoJSONToOSMService
from wayfinder.domain.node_registry import NodeRegistry

# URL of the internal rebuild server running in the valhalla container.
# Override via environment variable if your service name or port differs.
import os
VALHALLA_REBUILD_URL = os.environ.get(
    "VALHALLA_REBUILD_URL", "http://valhalla:9001/rebuild"
)


class WayCRUDService:

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, feature: dict) -> None:
        """Add a new way to the network and rebuild tiles."""
        self._upsert([feature])

    def update(self, feature: dict) -> None:
        """
        Update an existing way. Deletes the old way by OBJECTID first,
        then re-inserts the new version so geometry changes are reflected.
        """
        object_id = self._object_id(feature)
        self._delete_from_pbf(object_id)
        self._upsert([feature])

    def delete(self, object_id: int) -> None:
        """Remove a way from the network by its ArcGIS OBJECTID and rebuild tiles."""
        self._delete_from_pbf(object_id)
        self._rebuild_tiles()

    def bulk_upsert(self, features: list[dict]) -> None:
        """Add or update multiple ways in a single tile rebuild."""
        self._upsert(features)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _upsert(self, features: list[dict]) -> None:
        """Convert features → OSM → PBF, merge into network PBF, rebuild."""
        with tempfile.TemporaryDirectory(dir=VALHALLA_DATA_DIR) as tmp:
            tmp = Path(tmp)
            osm_path = tmp / "update.osm"
            pbf_path = tmp / "update.pbf"

            # Convert to OSM XML using stable node IDs from registry
            with NodeRegistry(NODE_REGISTRY_PATH) as registry:
                GeoJSONToOSMService.convert_features(
                    features=features,
                    osm_path=osm_path,
                    registry=registry,
                )

            # OSM XML → PBF
            subprocess.run(
                [
                    "osmium", "sort",
                    str(osm_path),
                    "-o", str(pbf_path),
                    "--output-format", "pbf",
                    "--overwrite",
                ],
                check=True,
            )

            # Merge update PBF into the canonical network PBF.
            # osmium merge handles duplicate node IDs correctly —
            # the last file wins for any given ID, so the updated
            # way overwrites the old one.
            merged_path = tmp / "merged.pbf"
            subprocess.run(
                [
                    "osmium", "merge",
                    str(NETWORK_PBF_PATH),
                    str(pbf_path),
                    "-o", str(merged_path),
                    "--overwrite",
                ],
                check=True,
            )

            # Sort and replace the canonical PBF
            subprocess.run(
                [
                    "osmium", "sort",
                    str(merged_path),
                    "-o", str(NETWORK_PBF_PATH),
                    "--output-format", "pbf",
                    "--overwrite",
                ],
                check=True,
            )

        self._rebuild_tiles()

    def _delete_from_pbf(self, object_id: int) -> None:
        """Remove a way by its derived OSM way ID from the canonical PBF."""
        with NodeRegistry(NODE_REGISTRY_PATH) as registry:
            way_id = registry.way_id_for_object(object_id)

        with tempfile.TemporaryDirectory(dir=VALHALLA_DATA_DIR) as tmp:
            filtered = Path(tmp) / "filtered.pbf"
            # osmium removeid drops the specified way (and any nodes/relations
            # that become orphaned), keeping everything else intact.
            subprocess.run(
                [
                    "osmium", "removeid",
                    str(NETWORK_PBF_PATH),
                    f"w{way_id}",
                    "-o", str(filtered),
                    "-O",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "osmium", "sort",
                    str(filtered),
                    "-o", str(NETWORK_PBF_PATH),
                    "--output-format", "pbf",
                    "--overwrite",
                ],
                check=True,
            )

    def _rebuild_tiles(self) -> None:
        """
        Ask the valhalla container's internal rebuild server to build fresh
        tiles and hot-reload valhalla_service.  The server serialises concurrent
        requests with a lock so we never run two builds simultaneously.

        Raises RuntimeError if the rebuild server reports failure.
        """
        req = urllib.request.Request(
            VALHALLA_REBUILD_URL,
            data=b"",          # non-empty → POST
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"Rebuild server returned HTTP {resp.status}"
                    )
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Rebuild server error {exc.code}: {exc.read().decode(errors='replace')}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach rebuild server at {VALHALLA_REBUILD_URL}: {exc.reason}"
            ) from exc

    @staticmethod
    def _object_id(feature: dict) -> int:
        props = feature.get("properties") or {}
        oid = props.get("OBJECTID") or props.get("objectid")
        if oid is None:
            raise ValueError("Feature has no OBJECTID — cannot determine way ID")
        return int(oid)