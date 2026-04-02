import requests


class ValhallaAdapter:

    def __init__(self, base_url: str = "http://valhalla:8002"):
        self.base_url = base_url.rstrip("/")

    def route(self, payload: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/route",
            json=payload,
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(response.text)

        return response.json()

    def isochrone(self, payload: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/isochrone",
            json=payload,
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(response.text)

        return response.json()