import os
import logging
import httpx                                        # ← added
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/geocode", tags=["geocode"])

HERE_API_KEY = os.getenv("HERE_API_KEY")
if not HERE_API_KEY:
    raise ValueError("HERE_API_KEY not found in environment variables")

logger = logging.getLogger(__name__)


@router.get("/autocomplete")
async def geocode_autocomplete(q: str):
    """
    HERE Geocoding API - returns address suggestions WITH coordinates.
    Uses Geocoding API instead of Autocomplete to ensure lat/lon are always present.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://geocode.search.hereapi.com/v1/geocode",
                params={
                    "q": q,
                    "apikey": HERE_API_KEY,
                    "limit": 5,
                    "in": "countryCode:USA",  # ISO 3166-1 alpha-3
                    "at": "40.4406,-79.9959",   # ← Pittsburgh, PA bias
                },
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()

        results: list[dict] = []
        for item in data.get("items", []):
            pos = item.get("position", {})
            # HERE returns lat/lng keys
            lat = pos.get("lat")
            lon = pos.get("lng") or pos.get("lon")
            if lat is None or lon is None:
                continue
            results.append({
                "label": item.get("title", ""),
                "address": item.get("address", {}).get("label", ""),
                "lat": lat,
                "lon": lon,
            })

        return {"results": results}

    except httpx.HTTPError as e:
        logger.error(f"HERE API HTTP error: {e}")
        raise HTTPException(status_code=500, detail=f"HERE API error: {str(e)}")
    except Exception as e:
        logger.error(f"Geocoding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")