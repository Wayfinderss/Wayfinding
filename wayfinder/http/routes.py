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


class ValhallaLocation(BaseModel):
    lat: float
    lon: float


class DirectionsOptions(BaseModel):
    units: Optional[str] = None


class PedestrianCostingOptions(BaseModel):
    incline: Optional[int] = None
    use_stairs: Optional[float] = None


class CostingOptions(BaseModel):
    pedestrian: Optional[PedestrianCostingOptions] = None


class RouteRequest(BaseModel):
    locations: list[ValhallaLocation]
    costing: str = "pedestrian"
    directions_options: Optional[DirectionsOptions] = None
    shape_format: Optional[str] = None
    elevation_interval: Optional[int] = None
    costing_options: Optional[CostingOptions] = None
    exclude_locations: Optional[list[ValhallaLocation]] = None
    user_id: Optional[str] = None


@router.post("/route")
def route(request: RouteRequest):
    """
    Compute a route between two coordinates.
    """
    controller = _get_route_controller()

    origin = request.locations[0]
    destination = request.locations[1]

    options: dict[str, object] = {}
    if request.directions_options is not None:
        options["directions_options"] = request.directions_options.model_dump(exclude_none=True)
    if request.shape_format is not None:
        options["shape_format"] = request.shape_format
    if request.elevation_interval is not None:
        options["elevation_interval"] = request.elevation_interval
    if request.costing_options is not None:
        options["costing_options"] = request.costing_options.model_dump(exclude_none=True)
    if request.exclude_locations is not None:
        options["exclude_locations"] = [{"lat": loc.lat, "lon": loc.lon} for loc in request.exclude_locations]

    return controller.get_route(
        origin_lat=origin.lat,
        origin_lng=origin.lon,
        dest_lat=destination.lat,
        dest_lng=destination.lon,
        costing=request.costing,
        options=options or None,
        user_id=request.user_id,
    )