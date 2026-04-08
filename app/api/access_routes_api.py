from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/access-routes", tags=["access-routes"])


# ---------- Pydantic models ----------

class AccessRouteCreate(BaseModel):
    name: str = Field(min_length=1)
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    costing: str = "pedestrian"


class AccessRoutePatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None
    costing: Optional[str] = None


class AccessRouteOut(BaseModel):
    id: str
    name: str
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    costing: str
    created_at: datetime
    updated_at: datetime


# ---------- “Manager” (like JobManager) ----------

class AccessRouteStore:
    def __init__(self) -> None:
        self._routes: Dict[str, AccessRouteOut] = {}

    def create(self, data: AccessRouteCreate) -> AccessRouteOut:
        now = datetime.now(timezone.utc)
        route = AccessRouteOut(
            id=str(uuid4()),
            created_at=now,
            updated_at=now,
            **data.model_dump(),
        )
        self._routes[route.id] = route
        return route

    def list(self) -> List[AccessRouteOut]:
        return list(self._routes.values())

    def get(self, route_id: str) -> Optional[AccessRouteOut]:
        return self._routes.get(route_id)

    def patch(self, route_id: str, patch: AccessRoutePatch) -> AccessRouteOut:
        existing = self.get(route_id)
        if not existing:
            raise KeyError(route_id)

        updates = patch.model_dump(exclude_unset=True)
        updated = existing.model_copy(
            update={
                **updates,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._routes[route_id] = updated
        return updated

    def delete(self, route_id: str) -> None:
        if route_id not in self._routes:
            raise KeyError(route_id)
        del self._routes[route_id]


store = AccessRouteStore()


# ---------- CRUD endpoints ----------

@router.post("", response_model=AccessRouteOut)
def create_access_route(body: AccessRouteCreate):
    return store.create(body)


@router.get("", response_model=list[AccessRouteOut])
def list_access_routes():
    return store.list()


@router.get("/{route_id}", response_model=AccessRouteOut)
def get_access_route(route_id: str):
    route = store.get(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Access route not found")
    return route


@router.patch("/{route_id}", response_model=AccessRouteOut)
def patch_access_route(route_id: str, body: AccessRoutePatch):
    try:
        return store.patch(route_id, body)
    except KeyError:
        raise HTTPException(status_code=404, detail="Access route not found")


@router.delete("/{route_id}", status_code=204)
def delete_access_route(route_id: str):
    try:
        store.delete(route_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Access route not found")