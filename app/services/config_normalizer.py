from app.services.base import TestService
from app.states.config_state import ValhallaConfigState
from app.services.register import register


from typing import Any, get_origin

@register("config_normalizer")
class ValhallaConfigNormalizer(TestService):
    service_name = "config_normalizer"
    @staticmethod
    def is_typing_placeholder(value: Any) -> bool:
        return isinstance(value, type) or get_origin(value) is not None

    def normalize(self, state: ValhallaConfigState) -> ValhallaConfigState:
        cleaned = self._strip(state.to_dict())
        self._assert_no_data_paths(cleaned)
        return ValhallaConfigState(cleaned)

    def _strip(self, obj: Any):
        if self.is_typing_placeholder(obj):
            return None
        if isinstance(obj, dict):
            return {
                k: v for k, v in
                ((k, self._strip(v)) for k, v in obj.items())
                if v is not None
            }
        if isinstance(obj, list):
            return [
                self._strip(v)
                for v in obj
                if not self.is_typing_placeholder(v)
            ]
        return obj

    def _assert_no_data_paths(self, obj: Any):
        if isinstance(obj, str) and obj.startswith("/data"):
            raise RuntimeError(f"Illegal /data path detected: {obj}")
        if isinstance(obj, dict):
            for v in obj.values():
                self._assert_no_data_paths(v)
        if isinstance(obj, list):
            for v in obj:
                self._assert_no_data_paths(v)

    def run(self, state: ValhallaConfigState, **kwargs) -> ValhallaConfigState:
        if not isinstance(state, ValhallaConfigState):
            raise TypeError("ValhallaConfigNormalizer expects ValhallaConfigState")
        return self.normalize(state)
