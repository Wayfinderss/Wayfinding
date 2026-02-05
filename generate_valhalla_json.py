import json
import typing
from typing import Any, get_origin


def is_typing_placeholder(value: Any) -> bool:
    """
    Returns True if value is a typing construct like Optional[str], Union[int, None], list[str], etc.
    """
    return (
        isinstance(value, type) or
        get_origin(value) is not None
    )

def strip_typing_placeholders(obj: Any):
    if is_typing_placeholder(obj):
        return None

    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            cleaned_value = strip_typing_placeholders(v)
            if cleaned_value is not None:
                cleaned[k] = cleaned_value
        return cleaned

    if isinstance(obj, list):
        return [
            strip_typing_placeholders(v)
            for v in obj
            if not is_typing_placeholder(v)
        ]

    return obj


def main():
    from config_file import config  # or paste config directly

    cleaned = strip_typing_placeholders(config)

    with open("valhalla.json", "w") as f:
        json.dump(cleaned, f, indent=2)

    print("✅ valhalla.json generated successfully")


if __name__ == "__main__":
    main()
