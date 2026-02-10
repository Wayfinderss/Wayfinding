from pathlib import Path
import json
from app.services.base import TestService
from app.services.register import register

@register("config_writer")
class ValhallaConfigWriter(TestService):
    service_name = "config_writer"

    def run(self, state, output_path: Path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.is_dir():
            raise ValueError(
                f"ConfigWriter expected a file path, got directory: {output_path}"
            )
        with open(output_path, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
