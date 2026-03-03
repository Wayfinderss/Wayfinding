"""
Database schema definitions for the Invalid Route Demand pipeline.

This module holds the canonical schema and provides helpers to create it
against either SQLite (local dev) or PostgreSQL (cloud). Run this BEFORE
any other pipeline code to set up your database.

Usage — standalone schema creation:

    # SQLite (local testing)
    python schema.py --backend sqlite --db walkway_demand.db

    # PostgreSQL (cloud)
    python schema.py --backend postgres --db "host=... dbname=... user=... password=..."

Usage — from Python:

    from invalid_route_pipeline.schema import create_schema

    create_schema(backend="sqlite", connection_string="walkway_demand.db")
    create_schema(backend="postgres", connection_string="host=...")
"""

# -------------------------------------------------------------------------
# Raw SQL — written in a dialect-neutral way where possible, with small
# branches for SQLite vs PostgreSQL differences.
# -------------------------------------------------------------------------

# The core tables are identical across backends except for type mappings:
#   SQLite:  TEXT, REAL, INTEGER
#   Postgres: TEXT/UUID, DOUBLE PRECISION, INTEGER, TIMESTAMPTZ

def _exec_postgres(dsn: str, sql: str, echo: bool):
    try:
        import psycopg2
    except ImportError:
        raise ImportError(
            "psycopg2 is required for PostgreSQL. "
            "Install it with: pip install psycopg2-binary"
        )
    if echo:
        print(f"[postgres] Connecting to {dsn}")
        print(sql)
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    if echo:
        print("[postgres] Done.")

def _exec_sqlite(db_path: str, sql: str, echo: bool):
    import sqlite3
    if echo:
        print(f"[sqlite] Connecting to {db_path}")
        print(sql)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(sql)
    conn.close()
    if echo:
        print("[sqlite] Done.")

class SchemaCreatorService:

    SQLITE_SCHEMA = """
    -- ===========================================================================
    -- failed_route_attempts
    -- Every individual failed routing attempt. This is the raw event log.
    -- ===========================================================================
    CREATE TABLE IF NOT EXISTS failed_route_attempts (
        id              TEXT PRIMARY KEY,
        origin_lat      REAL        NOT NULL,
        origin_lng      REAL        NOT NULL,
        dest_lat        REAL        NOT NULL,
        dest_lng        REAL        NOT NULL,
        origin_geohash  TEXT        NOT NULL,
        dest_geohash    TEXT        NOT NULL,
        user_id         TEXT,
        failure_reason  TEXT,
        timestamp       REAL        NOT NULL      -- Unix epoch seconds
    );
    
    -- Indexes: these are critical for the hotspot and nearby queries.
    CREATE INDEX IF NOT EXISTS idx_fra_origin_geohash  ON failed_route_attempts(origin_geohash);
    CREATE INDEX IF NOT EXISTS idx_fra_dest_geohash    ON failed_route_attempts(dest_geohash);
    CREATE INDEX IF NOT EXISTS idx_fra_timestamp        ON failed_route_attempts(timestamp);
    CREATE INDEX IF NOT EXISTS idx_fra_user_id          ON failed_route_attempts(user_id);
    
    -- ===========================================================================
    -- demand_summary
    -- Pre-aggregated counts per geohash cell. Updated on each insert and can
    -- be fully rebuilt from failed_route_attempts at any time.
    -- ===========================================================================
    CREATE TABLE IF NOT EXISTS demand_summary (
        geohash         TEXT    NOT NULL,
        point_type      TEXT    NOT NULL CHECK(point_type IN ('origin', 'destination')),
        attempt_count   INTEGER NOT NULL DEFAULT 0,
        unique_users    INTEGER NOT NULL DEFAULT 0,
        first_seen      REAL,
        last_seen       REAL,
        PRIMARY KEY (geohash, point_type)
    );
    """


    POSTGRES_SCHEMA = """
    -- ===========================================================================
    -- failed_route_attempts
    -- ===========================================================================
    CREATE TABLE IF NOT EXISTS failed_route_attempts (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        origin_lat      DOUBLE PRECISION    NOT NULL,
        origin_lng      DOUBLE PRECISION    NOT NULL,
        dest_lat        DOUBLE PRECISION    NOT NULL,
        dest_lng        DOUBLE PRECISION    NOT NULL,
        origin_geohash  VARCHAR(12)         NOT NULL,
        dest_geohash    VARCHAR(12)         NOT NULL,
        user_id         VARCHAR(255),
        failure_reason  VARCHAR(100),
        timestamp       DOUBLE PRECISION    NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_fra_origin_geohash  ON failed_route_attempts(origin_geohash);
    CREATE INDEX IF NOT EXISTS idx_fra_dest_geohash    ON failed_route_attempts(dest_geohash);
    CREATE INDEX IF NOT EXISTS idx_fra_timestamp        ON failed_route_attempts(timestamp);
    CREATE INDEX IF NOT EXISTS idx_fra_user_id          ON failed_route_attempts(user_id);
    
    -- Composite index for the route-pair aggregation query
    CREATE INDEX IF NOT EXISTS idx_fra_route_pair
        ON failed_route_attempts(origin_geohash, dest_geohash);
    
    -- ===========================================================================
    -- demand_summary
    -- ===========================================================================
    CREATE TABLE IF NOT EXISTS demand_summary (
        geohash         VARCHAR(12) NOT NULL,
        point_type      VARCHAR(11) NOT NULL CHECK(point_type IN ('origin', 'destination')),
        attempt_count   INTEGER     NOT NULL DEFAULT 0,
        unique_users    INTEGER     NOT NULL DEFAULT 0,
        first_seen      DOUBLE PRECISION,
        last_seen       DOUBLE PRECISION,
        PRIMARY KEY (geohash, point_type)
    );
    """

    # -------------------------------------------------------------------------
    # Schema creation helpers
    # -------------------------------------------------------------------------

    def create_schema(self, backend: str, connection_string: str, echo: bool = False):
        """
        Create all tables and indexes in the target database.

        Args:
            backend:            "sqlite" or "postgres"
            connection_string:  For sqlite, the file path (e.g. "walkway_demand.db").
                                For postgres, a libpq connection string or DSN.
            echo:               If True, print the SQL being executed.
        """
        if backend == "sqlite":
            self._create_sqlite(connection_string, echo)
        elif backend == "postgres":
            self._create_postgres(connection_string, echo)
        else:
            raise ValueError(f"Unsupported backend: {backend!r}. Use 'sqlite' or 'postgres'.")

    # ---- SQLite ----

    def _create_sqlite(self, db_path: str, echo: bool):
        _exec_sqlite(db_path, self.SQLITE_SCHEMA, echo)

    # ---- PostgreSQL ----

    def _create_postgres(self, dsn: str, echo: bool):
        _exec_postgres(dsn, self.POSTGRES_SCHEMA, echo)

    def run(self, **kwargs):
        self.create_schema(**kwargs)
