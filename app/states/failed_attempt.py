from typing import Optional
from dataclasses import dataclass, field

@dataclass
class FailedRouteAttempt:
    id: str
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    origin_geohash: str
    dest_geohash: str
    user_id: Optional[str]
    failure_reason: Optional[str]
    timestamp: float


@dataclass
class DemandHotspot:
    """A cluster of failed attempts sharing the same geohash cell."""
    geohash: str
    center_lat: float
    center_lng: float
    attempt_count: int
    unique_users: int
    first_seen: str
    last_seen: str
    point_type: str                                  # "origin" or "destination"
    sample_reasons: list = field(default_factory=list)