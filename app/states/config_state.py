class ValhallaConfigState:
    def __init__(self, config: dict):
        self.config = config

    def to_dict(self) -> dict:
        return self.config
