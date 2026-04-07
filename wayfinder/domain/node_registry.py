"""
Persistent coordinate → node ID registry backed by SQLite.

Guarantees that any two ways sharing an endpoint coordinate always
get the same OSM node ID, regardless of which way is converted first
or which chunk/update triggered the conversion.

Node IDs are assigned once and never change. Way IDs are derived
from the feature's OBJECTID (already unique in the ArcGIS source).
"""

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