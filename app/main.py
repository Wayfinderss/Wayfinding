from fastapi import FastAPI

from app.api.pipeline_api import router
import app.services.register_all

def create_app():
    app = FastAPI()
    app.include_router(router)
    return app

app = create_app()