# engines/valhalla/actor_loader.py

from pathlib import Path
from threading import Lock
from valhalla import Actor
from config_builder import ValhallaConfigBuilder


class ActorLoader:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._actor: Actor | None = None
        self._lock = Lock()

    def get_actor(self) -> Actor:
        if self._actor is None:
            with self._lock:
                if self._actor is None:
                    self._actor = self._load_actor()

        return self._actor

    def reload(self) -> Actor:
        with self._lock:
            self._actor = self._load_actor()
            return self._actor

    def _load_actor(self) -> Actor:
        if not self.config_path.exists():
            raise RuntimeError(
                f"Valhalla config not found at {self.config_path}"
            )

        ValhallaConfigBuilder(self.config_path).write(self.config_path)
        print(f"Loading Valhalla Actor from {self.config_path}")
        return Actor(str(self.config_path))