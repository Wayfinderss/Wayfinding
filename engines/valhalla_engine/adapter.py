from engines.valhalla_engine.actor_loader import ActorLoader

class ValhallaAdapter:
    def __init__(self, actor_loader: ActorLoader):
        self.actor_loader = actor_loader

    def route(self, payload: dict) -> dict:
        actor = self.actor_loader.get_actor()
        return actor.route(payload)