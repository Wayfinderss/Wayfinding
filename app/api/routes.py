from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.routing_service import ValhallaRouteService


router = APIRouter(prefix="/valhalla", tags=["valhalla"])


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    costing: str = "pedestrian"
    options: Dict[str, Any] = Field(default_factory=dict)


@router.post("/route")
def route(request: RouteRequest):
    routing_service = ValhallaRouteService()
    return routing_service.request_route(
        origin_lat=request.origin_lat,
        origin_lng=request.origin_lon,
        dest_lat=request.dest_lat,
        dest_lng=request.dest_lon,
        costing=request.costing,
    )