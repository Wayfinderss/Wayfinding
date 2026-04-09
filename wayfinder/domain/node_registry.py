"""
Persistent coordinate → node ID registry backed by SQLite.

Guarantees that any two ways sharing an endpoint coordinate always
get the same OSM node ID, regardless of which way is converted first
or which chunk/update triggered the conversion.

Node IDs are assigned once and never change. Way IDs are derived
from the feature's OBJECTID (already unique in the ArcGIS source).
"""

import json
import sqlite3
from pathlib import Path


# Round coordinates to ~1cm precision (5 decimal places ≈ 1.1m, 7 ≈ 1cm)
_COORD_PRECISION = 7


def _coord_key(lon: float, lat: float) -> tuple[float, float]:
    return (round(lon, _COORD_PRECISION), round(lat, _COORD_PRECISION))


class NodeRegistry:
    """
    Thread-unsafe (use one instance per process/thread).
    For concurrent CRUD, wrap calls in a lock or use a task queue.
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._bootstrap()

    def _bootstrap(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                lon   REAL NOT NULL,
                lat   REAL NOT NULL,
                id    INTEGER NOT NULL,
                PRIMARY KEY (lon, lat)
            );
            CREATE TABLE IF NOT EXISTS ways (
                object_id   INTEGER PRIMARY KEY,
                type_name   TEXT,
                status      TEXT,
                material    TEXT,
                width       REAL,
                grade       REAL,
                road_name   TEXT,
                lighting    TEXT,
                condition   TEXT,
                curb_ramp   TEXT,
                notes       TEXT,
                z_min       REAL,
                z_max       REAL,
                geometry    TEXT
            );
            CREATE TABLE IF NOT EXISTS counters (
                name  TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO counters VALUES ('next_node_id', 1);
            INSERT OR IGNORE INTO counters VALUES ('next_way_id',  1);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Node ID assignment
    # ------------------------------------------------------------------

    def get_or_create_node_id(self, lon: float, lat: float) -> int:
        """Return the canonical node ID for this coordinate, creating if needed."""
        lon, lat = _coord_key(lon, lat)
        row = self._conn.execute(
            "SELECT id FROM nodes WHERE lon=? AND lat=?", (lon, lat)
        ).fetchone()
        if row:
            return row[0]

        node_id = self._next_id("next_node_id")
        self._conn.execute(
            "INSERT INTO nodes (lon, lat, id) VALUES (?, ?, ?)", (lon, lat, node_id)
        )
        self._conn.commit()
        return node_id

    def load_into_memory(self) -> dict[tuple[float, float], int]:
        """
        Load all existing nodes into a dict for fast in-process lookups.
        Use this for bulk conversions to avoid per-node SQLite round trips.
        Returns { (lon, lat): node_id }
        """
        rows = self._conn.execute("SELECT lon, lat, id FROM nodes").fetchall()
        return {(row[0], row[1]): row[2] for row in rows}

    def bulk_insert(self, coord_to_id: dict[tuple[float, float], int]) -> None:
        """
        Insert many (lon, lat, id) entries in a single transaction.
        Skips any that already exist (INSERT OR IGNORE).
        """
        self._conn.executemany(
            "INSERT OR IGNORE INTO nodes (lon, lat, id) VALUES (?, ?, ?)",
            [(lon, lat, nid) for (lon, lat), nid in coord_to_id.items()],
        )
        self._conn.commit()

    def next_node_id(self) -> int:
        """Get and increment the node ID counter."""
        return self._next_id("next_node_id")

    # ------------------------------------------------------------------
    # Way ID assignment
    # ------------------------------------------------------------------

    def way_id_for_object(self, object_id: int) -> int:
        """
        Derive a stable way ID from the ArcGIS OBJECTID.
        We offset by a large number to avoid colliding with node IDs
        in the same OSM ID space.
        """
        return 1_000_000_000 + object_id

    # ------------------------------------------------------------------
    # Way metadata
    # ------------------------------------------------------------------

    def register_way(self, object_id: int, props: dict, geometry: dict) -> None:
        """Record object_id → GeoJSON metadata."""
        self._conn.execute("""
            INSERT OR REPLACE INTO ways (
                object_id, type_name, status, material, width, grade,
                road_name, lighting, condition, curb_ramp, notes, z_min, z_max, geometry
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            object_id,
            props.get("Type_Name"),
            props.get("Status"),
            props.get("Material"),
            props.get("Width"),
            props.get("Grade"),
            props.get("RoadName"),
            props.get("Lighting"),
            props.get("Condition"),
            props.get("CurbRamp"),
            props.get("Notes"),
            props.get("Z_Min"),
            props.get("Z_Max"),
            json.dumps(geometry),
        ))
        self._conn.commit()

    def bulk_register_ways(self, ways: list[dict]) -> None:
        """
        Register many ways in a single transaction.
        Each dict must have: object_id, props, geometry.
        """
        self._conn.executemany("""
            INSERT OR REPLACE INTO ways (
                object_id, type_name, status, material, width, grade,
                road_name, lighting, condition, curb_ramp, notes, z_min, z_max, geometry
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                w["object_id"],
                w["props"].get("Type_Name"),
                w["props"].get("Status"),
                w["props"].get("Material"),
                w["props"].get("Width"),
                w["props"].get("Grade"),
                w["props"].get("RoadName"),
                w["props"].get("Lighting"),
                w["props"].get("Condition"),
                w["props"].get("CurbRamp"),
                w["props"].get("Notes"),
                w["props"].get("Z_Min"),
                w["props"].get("Z_Max"),
                json.dumps(w["geometry"]),
            )
            for w in ways
        ])
        self._conn.commit()

    def lookup_way(self, object_id: int) -> dict | None:
        """Return all stored metadata for a way by OBJECTID."""
        row = self._conn.execute("""
            SELECT type_name, status, material, width, grade, road_name,
                   lighting, condition, curb_ramp, notes, z_min, z_max, geometry
            FROM ways WHERE object_id = ?
        """, (object_id,)).fetchone()
        if row is None:
            return None
        return {
            "object_id": object_id,
            "type_name": row[0],
            "status": row[1],
            "material": row[2],
            "width": row[3],
            "grade": row[4],
            "road_name": row[5],
            "lighting": row[6],
            "condition": row[7],
            "curb_ramp": row[8],
            "notes": row[9],
            "z_min": row[10],
            "z_max": row[11],
            "geometry": json.loads(row[12]) if row[12] else None,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _next_id(self, counter: str) -> int:
        cur = self._conn.execute(
            "UPDATE counters SET value = value + 1 WHERE name = ? RETURNING value - 1",
            (counter,),
        )
        return cur.fetchone()[0]

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()