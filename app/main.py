from fastapi import FastAPI

from app.api.routes import router
from app.api.demand import router as demand_router

def create_app():
    app = FastAPI()
    app.include_router(router)
    app.include_router(demand_router)
    return app

app = create_app()