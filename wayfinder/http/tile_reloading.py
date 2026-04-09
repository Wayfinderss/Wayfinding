from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from wayfinder.domain.way_crud_service import WayCRUDService
from wayfinder.domain.node_registry import NodeRegistry
from wayfinder.config.paths import NODE_REGISTRY_PATH, NETWORK_PBF_PATH, VALHALLA_CONFIG_PATH
from wayfinder.http.dependencies import require_admin
import threading

router = APIRouter(prefix="/ways", tags=["ways"], dependencies=[Depends(require_admin)])
_service = WayCRUDService()

# Prevent concurrent rebuilds — only one tile build at a time
_rebuild_lock = threading.Lock()
_rebuild_status: dict = {"running": False, "last_error": None}


class Feature(BaseModel):
    type: str
    properties: dict
    geometry: dict


def _extract_object_id(feature: Feature) -> int:
    props = feature.properties
    oid = props.get("OBJECTID") or props.get("objectid")
    if not oid:
        raise HTTPException(status_code=400, detail="Feature has no OBJECTID in properties")
    return int(oid)


def _verify_object_id(object_id: int) -> int:
    """Confirm the object_id exists in the node registry."""
    with NodeRegistry(NODE_REGISTRY_PATH) as registry:
        way_id = registry.way_id_for_object(object_id)
        existing = registry.object_id_for_way(way_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"No way found for object_id {object_id}")
    return object_id


def _run_locked(fn, *args, **kwargs):
    if not _rebuild_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A tile rebuild is already in progress")
    _rebuild_status["running"] = True
    _rebuild_status["last_error"] = None
    try:
        fn(*args, **kwargs)
    except Exception as e:
        _rebuild_status["last_error"] = str(e)
        raise
    finally:
        _rebuild_status["running"] = False
        _rebuild_lock.release()


@router.get("/status")
def rebuild_status():
    return _rebuild_status


@router.get("/{object_id}")
def lookup_way(object_id: int):
    from wayfinder.domain.node_registry import NodeRegistry
    from wayfinder.config.paths import NODE_REGISTRY_PATH
    with NodeRegistry(NODE_REGISTRY_PATH) as registry:
        result = registry.lookup_way(object_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No way found for object_id {object_id}")
    return result


def _verify_object_id(object_id: int) -> int:
    from wayfinder.domain.node_registry import NodeRegistry
    from wayfinder.config.paths import NODE_REGISTRY_PATH
    with NodeRegistry(NODE_REGISTRY_PATH) as registry:
        result = registry.lookup_way(object_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No way found for object_id {object_id}")
    return object_id


@router.get("/{object_id}")
def lookup_way(object_id: int):
    """Check whether a way exists in the registry by its OBJECTID."""
    with NodeRegistry(NODE_REGISTRY_PATH) as registry:
        way_id = registry.way_id_for_object(object_id)
        existing = registry.object_id_for_way(way_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"No way found for object_id {object_id}")
    return {"object_id": object_id, "way_id": way_id}


@router.post("/", status_code=202)
def add_way(feature: Feature, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_locked, _service.add, feature.model_dump())
    return {"status": "accepted"}


@router.put("/{object_id}", status_code=202)
def update_way(feature: Feature, background_tasks: BackgroundTasks, object_id: Optional[int] = None):
    oid = object_id or _extract_object_id(feature)
    _verify_object_id(oid)
    background_tasks.add_task(_run_locked, _service.update, feature.model_dump())
    return {"status": "accepted", "object_id": oid}


@router.delete("/{object_id}", status_code=202)
def delete_way(background_tasks: BackgroundTasks, object_id: Optional[int] = None, feature: Optional[Feature] = None):
    oid = object_id or (feature and _extract_object_id(feature))
    if not oid:
        raise HTTPException(status_code=400, detail="object_id is required for delete")
    _verify_object_id(oid)
    background_tasks.add_task(_run_locked, _service.delete, oid)
    return {"status": "accepted", "object_id": oid}


@router.post("/bulk", status_code=202)
def bulk_upsert(features: list[Feature], background_tasks: BackgroundTasks):
    background_tasks.add_task(
        _run_locked, _service.bulk_upsert, [f.model_dump() for f in features]
    )
    return {"status": "accepted", "count": len(features)}


@router.post("/rebuild", status_code=202)
def rebuild_tiles(background_tasks: BackgroundTasks):
    """Trigger a full tile rebuild without any OSM changes."""
    background_tasks.add_task(
        _run_locked,
        _service._tile_builder.build_and_swap,
        config_path=VALHALLA_CONFIG_PATH,
        osm_path=NETWORK_PBF_PATH,
    )
    return {"status": "accepted"}