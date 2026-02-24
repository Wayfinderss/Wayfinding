"""
CRUD API for blocked streets (do-not-use list).
Storage is in-memory per server instance; can be swapped for file/DB later.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/blocked-streets", tags=["blocked-streets"])


# ---------- Pydantic models ----------

class BlockedStreetCreate(BaseModel):
    name: str = Field(min_length=1, description="Street or place name to avoid")
    note: Optional[str] = Field(default=None, description="Optional note")


class BlockedStreetPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    note: Optional[str] = None
    active: Optional[bool] = None  # toggle: when False, not used in routing


class BlockedStreetOut(BaseModel):
    id: str
    name: str
    note: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime


# ---------- In-memory store (per server instance) ----------

class BlockedStreetStore:
    def __init__(self) -> None:
        self._items: Dict[str, BlockedStreetOut] = {}

    def create(self, data: BlockedStreetCreate) -> BlockedStreetOut:
        now = datetime.now(timezone.utc)
        item = BlockedStreetOut(
            id=str(uuid4()),
            name=data.name.strip(),
            note=(data.note.strip() if data.note else None),
            active=True,
            created_at=now,
            updated_at=now,
        )
        self._items[item.id] = item
        return item

    def list_all(self, active_only: bool = False) -> List[BlockedStreetOut]:
        items = list(self._items.values())
        if active_only:
            items = [i for i in items if i.active]
        return items

    def get(self, item_id: str) -> Optional[BlockedStreetOut]:
        return self._items.get(item_id)

    def patch(self, item_id: str, patch: BlockedStreetPatch) -> BlockedStreetOut:
        existing = self.get(item_id)
        if not existing:
            raise KeyError(item_id)
        updates = patch.model_dump(exclude_unset=True)
        if "name" in updates and updates["name"] is not None:
            updates["name"] = updates["name"].strip()
        updated = existing.model_copy(
            update={
                **updates,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._items[item_id] = updated
        return updated

    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise KeyError(item_id)
        del self._items[item_id]


store = BlockedStreetStore()


# ---------- CRUD endpoints ----------

@router.post("", response_model=BlockedStreetOut)
def create_blocked_street(body: BlockedStreetCreate) -> BlockedStreetOut:
    return store.create(body)


@router.get("", response_model=List[BlockedStreetOut])
def list_blocked_streets(active_only: bool = False) -> List[BlockedStreetOut]:
    return store.list_all(active_only=active_only)


@router.get("/{item_id}", response_model=BlockedStreetOut)
def get_blocked_street(item_id: str) -> BlockedStreetOut:
    item = store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Blocked street not found")
    return item


@router.patch("/{item_id}", response_model=BlockedStreetOut)
def patch_blocked_street(item_id: str, body: BlockedStreetPatch) -> BlockedStreetOut:
    try:
        return store.patch(item_id, body)
    except KeyError:
        raise HTTPException(status_code=404, detail="Blocked street not found")


@router.delete("/{item_id}", status_code=204)
def delete_blocked_street(item_id: str) -> None:
    try:
        store.delete(item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Blocked street not found")
