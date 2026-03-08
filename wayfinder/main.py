from integrations.logger.boostrap import Bootstrapper
from wayfinder.http.routes import router
from wayfinder.http.demand import router as demand_router
from wayfinder.http.tile_reloading import router as tile_router

from fastapi import FastAPI
from contextlib import asynccontextmanager
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend = os.getenv("DB_BACKEND", "sqlite")
    connection_string = os.getenv("DB_CONNECTION_STRING")

    try:
        Bootstrapper().bootstrap_db(
            backend=backend,
            connection_string=connection_string,
        )
        print("✓ Logger database bootstrapped")
    except Exception as e:
        print("Logger bootstrap failed:", e)

    yield

    print("Application shutting down...")


def create_app():
    api_app = FastAPI(lifespan=lifespan)

    api_app.include_router(router)
    api_app.include_router(demand_router)
    api_app.include_router(tile_router)

    return api_app


app = create_app()