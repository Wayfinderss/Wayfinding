from typing import Optional
import os
import time

from fastapi import APIRouter
from pydantic import BaseModel

from integrations.logger.postgres_backend import PostgresBackend
from wayfinder.controllers.valhalla_controller import RouteController
from wayfinder.domain.schema_creator_service import SchemaCreatorService


router = APIRouter(prefix="/valhalla", tags=["valhalla"])


route_controller: RouteController | None = None


def _get_db_backend() -> str:
    return os.getenv("DB_BACKEND", "postgres")


def _get_db_connection_string() -> str:
    return os.getenv(
        "DB_CONNECTION_STRING",
        "host=postgres port=5432 dbname=wayfinding_logger user=postgres password=secret",
    )


def _create_route_controller() -> RouteController:
    return RouteController(
        valhalla_url=os.getenv("VALHALLA_URL", "http://valhalla:8002"),
        db_backend=_get_db_backend(),
        db_connection_string=_get_db_connection_string(),
    )


def _ensure_database_ready(backend: str, connection_string: str) -> None:
    if backend != "postgres":
        return

    last_error: Exception | None = None
    for _ in range(10):
        try:
            PostgresBackend(connection_string).create_database()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2)

    raise RuntimeError("Failed to create or connect to PostgreSQL database") from last_error


def _initialize_route_controller() -> None:
    global route_controller

    if route_controller is not None:
        return

    db_backend = _get_db_backend()
    db_connection_string = _get_db_connection_string()

    _ensure_database_ready(db_backend, db_connection_string)
    SchemaCreatorService().create_schema(
        backend=db_backend,
        connection_string=db_connection_string,
    )
    route_controller = _create_route_controller()


def _get_route_controller() -> RouteController:
    if route_controller is None:
        _initialize_route_controller()
    return route_controller


@router.on_event("startup")
def startup() -> None:
    _initialize_route_controller()


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    costing: str = "pedestrian"
    user_id: Optional[str] = None


@router.post("/route")
def route(request: RouteRequest):
    """
    Compute a route between two coordinates.
    """
    controller = _get_route_controller()

    return controller.get_route(
        origin_lat=request.origin_lat,
        origin_lng=request.origin_lon,
        dest_lat=request.dest_lat,
        dest_lng=request.dest_lon,
        user_id=request.user_id,
    )