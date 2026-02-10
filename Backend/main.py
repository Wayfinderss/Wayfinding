from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Coord(BaseModel):
    lat1: float
    lng2: float

@app.post("/geo")
def get_geojson(coord: Coord):
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [coord.lng, coord.lat]
        },
        "properties": {}
    }
