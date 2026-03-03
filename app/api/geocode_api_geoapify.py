import os
import logging
import httpx
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/geocode", tags=["geocode"])

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
if not GEOAPIFY_API_KEY:
    raise ValueError("GEOAPIFY_API_KEY not found in environment variables")

logger = logging.getLogger(__name__)


@router.get("/autocomplete")
async def geocode_autocomplete(q: str):
    """
    Geoapify Geocoding API - returns address suggestions WITH coordinates.
    Uses the /v1/geocode/autocomplete endpoint with US filter and Pittsburgh bias.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.geoapify.com/v1/geocode/autocomplete",
                params={
                    "text": q,
                    "apiKey": GEOAPIFY_API_KEY,
                    "limit": 5,
                    "filter": "countrycode:us",
                    "bias": "proximity:-79.9585,40.4321",  # ← lon,lat order
                    "type": "amenity",                      # ← prioritize POIs
                },
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()

        results: list[dict] = []
        for item in data.get("features", []):
            props = item.get("properties", {})
            lat = props.get("lat")
            lon = props.get("lon")
            if lat is None or lon is None:
                continue
            results.append({
                "label": props.get("formatted", ""),
                "address": props.get("formatted", ""),
                "lat": lat,
                "lon": lon,
            })

        return {"results": results}

    except httpx.HTTPError as e:
        logger.error(f"Geoapify API HTTP error: {e}")
        raise HTTPException(status_code=500, detail=f"Geoapify API error: {str(e)}")
    except Exception as e:
        logger.error(f"Geocoding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")