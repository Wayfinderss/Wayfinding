from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.pipeline_api import router
from app.api.geocode_api import router as geocode_router
import app.services.register_all
import logging
logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="Wayfinding API")
    
    # CORS middleware (allows frontend to call API)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API routers
    app.include_router(router)  # valhalla pipeline endpoints
    app.include_router(geocode_router)  # HERE geocoding endpoints
    
    # Serve demo page at root
    @app.get("/")
    def index():
        return FileResponse("static/index.html")
    
    # Serve static assets (CSS, JS, etc.) under /static
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    return app


app = create_app()