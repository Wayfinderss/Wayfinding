import os
import logging
from fastapi import APIRouter, HTTPException
from wayfinder.domain.geocoding_service import GeoapifyGeocodingService

router = APIRouter(prefix="/geocode", tags=["geocode"])
logger = logging.getLogger(__name__)


def _get_service() -> GeoapifyGeocodingService:
    api_key = os.getenv("GEOAPIFY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEOAPIFY_API_KEY not set")
    return GeoapifyGeocodingService(api_key)


@router.get("/autocomplete")
async def geocode_autocomplete(q: str):
    service = _get_service()
    try:
        results = await service.autocomplete(q)
        return {"results": results}
    except Exception as e:
        logger.error(f"Autocomplete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reverse")
async def reverse_geocode(lat: float, lon: float):
    service = _get_service()
    try:
        return await service.reverse(lat, lon)
    except Exception as e:
        logger.error(f"Reverse geocode error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))