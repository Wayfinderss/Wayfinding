from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

class TestService(ABC):
    service_name: str

    def __init__(self):
        if not hasattr(self, "service_name"):
            raise ValueError("Service must define a name")

    @abstractmethod
    def run(self, **kwargs) -> Any:
        pass