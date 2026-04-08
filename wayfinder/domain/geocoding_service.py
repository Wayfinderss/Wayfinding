import os
import logging
import httpx
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GeoapifyGeocodingService:
    _BASE_URL = "https://api.geoapify.com/v1/geocode"
    _PITTSBURGH_BIAS = "proximity:-79.9585,40.4321"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def autocomplete(self, query: str, limit: int = 5) -> list[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._BASE_URL}/autocomplete",
                params={
                    "text": query,
                    "apiKey": self._api_key,
                    "limit": limit,
                    "filter": "countrycode:us",
                    "bias": self._PITTSBURGH_BIAS,
                },
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_autocomplete(data)

    async def reverse(self, lat: float, lon: float) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._BASE_URL}/reverse",
                params={"lat": lat, "lon": lon, "apiKey": self._api_key, "limit": 1},
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_reverse(data, lat, lon)

    def _parse_autocomplete(self, data: Dict[str, Any]) -> list[Dict[str, Any]]:
        results = []
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
        return results

    def _parse_reverse(self, data: Dict[str, Any], fallback_lat: float, fallback_lon: float) -> Dict[str, Any]:
        features = data.get("features", [])
        if not features:
            return {"label": "", "address": "", "lat": fallback_lat, "lon": fallback_lon}

        props = features[0].get("properties", {})
        label = props.get("formatted") or props.get("name") or ""
        return {
            "label": label,
            "address": label,
            "lat": props.get("lat", fallback_lat),
            "lon": props.get("lon", fallback_lon),
        }