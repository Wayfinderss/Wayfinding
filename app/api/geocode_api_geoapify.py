import os
import logging
import httpx
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/geocode", tags=["geocode"])

def _get_geoapify_api_key() -> str | None:
    # Don't crash the whole API at import time if the key is missing.
    # We instead return a clean 503 from the endpoint.
    return os.getenv("GEOAPIFY_API_KEY")

logger = logging.getLogger(__name__)


@router.get("/autocomplete")
async def geocode_autocomplete(q: str):
    """
    Geoapify Geocoding API - returns address suggestions WITH coordinates.
    Uses the /v1/geocode/autocomplete endpoint with US filter and Pittsburgh bias.
    """
    try:
        api_key = _get_geoapify_api_key()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="GEOAPIFY_API_KEY is not set. Add it to your environment (or a .env file) and restart the server.",
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.geoapify.com/v1/geocode/autocomplete",
                params={
                    "text": q,
                    "apiKey": api_key,
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


@router.get("/reverse")
async def reverse_geocode(lat: float, lon: float):
    """
    Geoapify Reverse Geocoding API.
    Uses /v1/geocode/reverse and returns a single best-match label/address.
    """
    try:
        api_key = _get_geoapify_api_key()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="GEOAPIFY_API_KEY is not set. Add it to your environment (or a .env file) and restart the server.",
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.geoapify.com/v1/geocode/reverse",
                params={
                    "lat": lat,
                    "lon": lon,
                    "apiKey": api_key,
                    "limit": 1,
                },
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()

        features = data.get("features", [])
        if not features:
            return {"label": "", "address": "", "lat": lat, "lon": lon}

        props = (features[0] or {}).get("properties", {}) or {}
        label = props.get("formatted") or props.get("name") or ""

        return {
            "label": label,
            "address": label,
            "lat": props.get("lat", lat),
            "lon": props.get("lon", lon),
        }

    except httpx.HTTPError as e:
        logger.error(f"Geoapify reverse API HTTP error: {e}")
        raise HTTPException(status_code=500, detail=f"Geoapify API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reverse geocoding error: {str(e)}")