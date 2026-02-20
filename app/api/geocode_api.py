import os
import logging
from fastapi import APIRouter, HTTPException
import httpx
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/geocode", tags=["geocode"])

HERE_API_KEY = os.getenv("HERE_API_KEY")
if not HERE_API_KEY:
    raise ValueError("HERE_API_KEY not found in environment variables")

# Set up logging
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
                },
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                # Geocoding API returns position with lat/lng
                position = item.get("position", {})
                lat = position.get("lat")
                lon = position.get("lng")  # HERE uses "lng" not "lon"
                
                if lat is not None and lon is not None:
                    address = item.get("address", {})
                    label = address.get("label", "") or item.get("title", "")
                    
                    results.append({
                        "label": label,
                        "address": label,
                        "lat": float(lat),
                        "lon": float(lon),
                    })
            
            return {"results": results}
            
    except httpx.HTTPError as e:
        logger.error(f"HERE API HTTP error: {e}")
        raise HTTPException(status_code=500, detail=f"HERE API error: {str(e)}")
    except Exception as e:
        logger.error(f"Geocoding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")