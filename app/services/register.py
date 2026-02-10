from typing import Dict
from app.services.base import TestService

VALHALLA_SERVICE_REGISTRY: Dict[str, TestService] = {}

def register(name: str):
    def decorator(cls):
        if name in VALHALLA_SERVICE_REGISTRY:
            raise RuntimeError(f"Service '{name}' already registered")
        VALHALLA_SERVICE_REGISTRY[name] = cls()
        return cls
    return decorator




