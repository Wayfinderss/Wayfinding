from typing import Dict, Any
from engines.valhalla_engine.actor_loader import ActorLoader


class ValhallaAdapter:
    def __init__(self, actor_loader: ActorLoader):
        self._actor_loader = actor_loader
        self._actor = self._actor_loader.get_actor()

    def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._actor.route(payload)
        except Exception as e:
            raise RuntimeError(str(e)) from e