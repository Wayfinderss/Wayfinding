from fastapi import APIRouter
from wayfinder.controllers.admin_tile_controller import AdminTileController

router = APIRouter(prefix="/valhalla", tags=["valhalla"])
route_controller = AdminTileController()

@router.post("/rebuild_tiles")
def rebuild_tiles():
    return route_controller.rebuild_tiles()