"""
Invalid Route Demand Pipeline
=============================
Catches failed walkway route attempts, logs them to a database, and
spatially clusters them using geohashing so that nearby attempts (even
20 feet apart) are grouped together for infrastructure planning.

The pipeline is backend-agnostic: use SQLite locally and PostgreSQL in
the cloud — same code, same interface.

Usage:
    from invalid_route_pipeline.pipeline import InvalidRoutePipeline

    # Local development
    pipeline = InvalidRoutePipeline(backend="sqlite", connection_string="walkway_demand.db")

    # Cloud
    pipeline = InvalidRoutePipeline(backend="postgres", connection_string="host=... dbname=...")

    # Log a failed route
    pipeline.log_failed_route(
        origin_lat=40.7128, origin_lng=-74.0060,
        dest_lat=40.7138, dest_lng=-74.0050,
        user_id="user_abc",
        failure_reason="no_walkway",
    )

    # Query hotspots
    hotspots = pipeline.get_demand_hotspots(min_attempts=5)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from wayfinder.domain.geohashing_service import Geohasher
from integrations.logger.databases_backend import DatabaseBackend
from integrations.logger.backend_factory import BackendFactory
from wayfinder.domain.schema_creator_service import SchemaCreatorService
from wayfinder.domain.failed_attempt import FailedRouteAttempt, DemandHotspot


# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

# Geohash precision controls grouping radius:
#   Precision 7 ≈ 153m × 153m  (wider grouping)
#   Precision 8 ≈  38m ×  19m  (≈ 60–120 feet — good default)
#   Precision 9 ≈   5m ×   5m  (very tight)
DEFAULT_GEOHASH_PRECISION = 8

# -------------------------------------------------------------------------
# Pipeline
# -------------------------------------------------------------------------

class InvalidRoutePipeline:
    """
    End-to-end pipeline for logging failed route attempts and surfacing
    demand hotspots where walkway infrastructure is missing.
    """

    def __init__(
        self,
        backend: str = "sqlite",
        connection_string: str = "walkway_demand.db",
        geohash_precision: int = DEFAULT_GEOHASH_PRECISION,
        auto_create_schema: bool = False,
    ):
        """
        Args:
            backend:             "sqlite" or "postgres"
            connection_string:   File path (sqlite) or DSN (postgres).
            geohash_precision:   Geohash length — controls grouping radius.
            auto_create_schema:  If True, run CREATE TABLE IF NOT EXISTS on
                                 init. Set False if you manage schema separately.
        """
        self.db: DatabaseBackend = BackendFactory.get_backend(backend, connection_string)
        self.precision = geohash_precision
        self.geohasher = Geohasher()

        if auto_create_schema:
            SchemaCreatorService().create_schema(
                backend=backend,
                connection_string=connection_string,
            )

    # ------------------------------------------------------------------
    # Core: log a failed route
    # ------------------------------------------------------------------

    def log_failed_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        user_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> FailedRouteAttempt:
        """
        Call this whenever your router fails to find a valid walkway route.
        """
        ts = timestamp or time.time()
        p = self.db.placeholder

        attempt = FailedRouteAttempt(
            id=str(uuid.uuid4()),
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            origin_geohash=self.geohasher.encode(origin_lat, origin_lng, self.precision),
            dest_geohash=self.geohasher.encode(dest_lat, dest_lng, self.precision),
            user_id=user_id,
            failure_reason=failure_reason,
            timestamp=ts,
        )

        with self.db.connection() as conn:
            # ---- Insert raw attempt ----
            self.db.execute(conn, f"""
                INSERT INTO failed_route_attempts
                    (id, origin_lat, origin_lng, dest_lat, dest_lng,
                     origin_geohash, dest_geohash, user_id, failure_reason, timestamp)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
            """, (
                attempt.id,
                attempt.origin_lat, attempt.origin_lng,
                attempt.dest_lat, attempt.dest_lng,
                attempt.origin_geohash, attempt.dest_geohash,
                attempt.user_id, attempt.failure_reason, attempt.timestamp,
            ))

            # ---- Update demand summary for both origin and destination ----
            upsert_sql = self.db.upsert_demand_sql()
            for gh, point_type in [
                (attempt.origin_geohash, "origin"),
                (attempt.dest_geohash, "destination"),
            ]:
                params = (gh, point_type, ts, ts, gh, gh, ts)
                self.db.execute(conn, upsert_sql, params)

        return attempt

    # ------------------------------------------------------------------
    # Query: demand hotspots
    # ------------------------------------------------------------------

    def get_demand_hotspots(
        self,
        min_attempts: int = 3,
        since_timestamp: Optional[float] = None,
        limit: int = 50,
    ) -> list[DemandHotspot]:
        """
        Top demand hotspots ranked by attempt count.

        Args:
            min_attempts:    Minimum failed attempts to qualify.
            since_timestamp: Only count attempts after this epoch time.
            limit:           Max hotspots to return.
        """
        p = self.db.placeholder
        ts_display = self.db.timestamp_to_display

        query = f"""
            SELECT
                ds.geohash,
                ds.point_type,
                ds.attempt_count,
                ds.unique_users,
                {ts_display('ds.first_seen')} AS first_seen,
                {ts_display('ds.last_seen')}  AS last_seen
            FROM demand_summary ds
            WHERE ds.attempt_count >= {p}
        """
        params: list = [min_attempts]

        if since_timestamp:
            query += f" AND ds.last_seen >= {p}"
            params.append(since_timestamp)

        query += f" ORDER BY ds.attempt_count DESC LIMIT {p}"
        params.append(limit)

        hotspots = []
        with self.db.connection() as conn:
            cursor = self.db.execute(conn, query, params)
            rows = self.db.fetchall(cursor)

            for row in rows:
                gh, point_type, count, users, first, last = row
                lat, lng = self.geohasher.decode(gh)

                reasons_cursor = self.db.execute(conn, f"""
                    SELECT DISTINCT failure_reason
                    FROM failed_route_attempts
                    WHERE (origin_geohash = {p} OR dest_geohash = {p})
                      AND failure_reason IS NOT NULL
                    LIMIT 5
                """, (gh, gh))
                reasons = [r[0] for r in self.db.fetchall(reasons_cursor)]

                hotspots.append(DemandHotspot(
                    geohash=gh,
                    center_lat=lat,
                    center_lng=lng,
                    attempt_count=count,
                    unique_users=users,
                    first_seen=first,
                    last_seen=last,
                    point_type=point_type,
                    sample_reasons=reasons,
                ))

        return hotspots

    # ------------------------------------------------------------------
    # Query: attempts near a point
    # ------------------------------------------------------------------

    def get_attempts_near(
        self, lat: float, lng: float, include_neighbors: bool = True
    ) -> list[dict]:
        """
        All failed attempts near a given coordinate. Searches the geohash
        cell containing the point plus its 8 neighbors (to avoid missing
        attempts that fall on a cell boundary).
        """
        center_gh = self.geohasher.encode(lat, lng, self.precision)
        geohashes = self.geohasher.neighbors(center_gh) + [center_gh] if include_neighbors else [center_gh]

        p = self.db.placeholder
        placeholders = ",".join(p for _ in geohashes)
        columns = [
            "id", "origin_lat", "origin_lng", "dest_lat", "dest_lng",
            "origin_geohash", "dest_geohash", "user_id",
            "failure_reason", "timestamp",
        ]
        col_list = ", ".join(columns)
        query = f"""
            SELECT {col_list} FROM failed_route_attempts
            WHERE origin_geohash IN ({placeholders})
               OR dest_geohash IN ({placeholders})
            ORDER BY timestamp DESC
        """

        with self.db.connection() as conn:
            cursor = self.db.execute(conn, query, geohashes + geohashes)
            rows = self.db.fetchall(cursor)
            return [dict(zip(columns, row)) for row in rows]

    # ------------------------------------------------------------------
    # Query: top route pairs
    # ------------------------------------------------------------------

    def get_top_route_pairs(
        self, min_attempts: int = 2, limit: int = 20
    ) -> list[dict]:
        """
        Most-requested origin→destination pairs (by geohash cell).
        Identifies specific missing walkway connections.
        """
        p = self.db.placeholder
        ts_display = self.db.timestamp_to_display

        query = f"""
            SELECT
                origin_geohash,
                dest_geohash,
                COUNT(*)                                    AS attempt_count,
                COUNT(DISTINCT user_id)                     AS unique_users,
                {ts_display('MIN(timestamp)')} AS first_seen,
                {ts_display('MAX(timestamp)')} AS last_seen
            FROM failed_route_attempts
            GROUP BY origin_geohash, dest_geohash
            HAVING COUNT(*) >= {p}
            ORDER BY COUNT(*) DESC
            LIMIT {p}
        """

        with self.db.connection() as conn:
            cursor = self.db.execute(conn, query, (min_attempts, limit))
            rows = self.db.fetchall(cursor)

        results = []
        for o_gh, d_gh, count, users, first, last in rows:
            o_lat, o_lng = self.geohasher.decode(o_gh)
            d_lat, d_lng = self.geohasher.decode(d_gh)
            results.append({
                "origin_geohash": o_gh,  "origin_lat": o_lat,  "origin_lng": o_lng,
                "dest_geohash": d_gh,    "dest_lat": d_lat,    "dest_lng": d_lng,
                "attempt_count": count,  "unique_users": users,
                "first_seen": first,     "last_seen": last,
            })
        return results

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def rebuild_demand_summary(self):
        """
        Full recompute of demand_summary from raw attempts.
        Run periodically or after bulk imports.
        """
        with self.db.connection() as conn:
            self.db.execute(conn, "DELETE FROM demand_summary")

            self.db.execute(conn, """
                INSERT INTO demand_summary
                    (geohash, point_type, attempt_count, unique_users, first_seen, last_seen)
                SELECT origin_geohash, 'origin',
                       COUNT(*), COUNT(DISTINCT user_id),
                       MIN(timestamp), MAX(timestamp)
                FROM failed_route_attempts
                GROUP BY origin_geohash
            """)

            self.db.execute(conn, """
                INSERT INTO demand_summary
                    (geohash, point_type, attempt_count, unique_users, first_seen, last_seen)
                SELECT dest_geohash, 'destination',
                       COUNT(*), COUNT(DISTINCT user_id),
                       MIN(timestamp), MAX(timestamp)
                FROM failed_route_attempts
                GROUP BY dest_geohash
            """)

    def purge_old_attempts(self, older_than_days: int = 365) -> int:
        """Remove attempts older than the given number of days."""
        p = self.db.placeholder
        cutoff = time.time() - (older_than_days * 86400)
        with self.db.connection() as conn:
            cursor = self.db.execute(
                conn,
                f"DELETE FROM failed_route_attempts WHERE timestamp < {p}",
                (cutoff,),
            )
        self.rebuild_demand_summary()
        return cursor.rowcount