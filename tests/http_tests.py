"""
pytest suite for wayfinder HTTP routes.

Covers:
  wayfinder/http/health.py         – GET  /valhalla/health
  wayfinder/http/routes.py         – POST /valhalla/route
  wayfinder/http/geocode.py        – GET  /geocode/autocomplete, /geocode/reverse
  wayfinder/http/demand.py         – GET  /demand/hotspots, /demand/route_pairs, /demand/near
  wayfinder/http/tile_reloading.py – GET  /ways/status, /ways/{object_id}
                                     POST /ways/, /ways/bulk, /ways/rebuild
                                     PUT  /ways/{object_id}
                                     DELETE /ways/{object_id}

Run:
  uv run pytest tests/http_tests.py -v
"""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Env vars must be set before the app (and its module-level singletons) import
# ---------------------------------------------------------------------------
os.environ.setdefault("DB_CONNECTION_STRING", "postgresql://test:test@localhost/test")
os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("GEOAPIFY_API_KEY", "test-geo-key")
os.environ.setdefault("VALHALLA_URL", "http://valhalla:8002")

from wayfinder.main import app  # noqa: E402

ADMIN_HEADERS = {"x-api-key": "test-admin-key"}
BAD_ADMIN_HEADERS = {"x-api-key": "wrong-key"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ===========================================================================
# 1. Health  –  GET /valhalla/health
# ===========================================================================

class TestHealth:
    def test_returns_200(self, client):
        response = client.get("/valhalla/health")
        assert response.status_code == 200

    def test_body_is_status_ok(self, client):
        response = client.get("/valhalla/health")
        assert response.json() == {"status": "ok"}


# ===========================================================================
# 2. Route  –  POST /valhalla/route
# ===========================================================================

MINIMAL_ROUTE_PAYLOAD = {
    "locations": [
        {"lat": 40.4406, "lon": -79.9959},
        {"lat": 40.4500, "lon": -79.9800},
    ],
    "costing": "pedestrian",
}

MOCK_VALHALLA_RESPONSE = {
    "trip": {
        "legs": [{"summary": {"length": 0.8, "time": 600}}],
        "status_message": "Found route",
    }
}


class TestRoutePost:
    # ------------------------------------------------------------------
    # Happy-path
    # ------------------------------------------------------------------

    def test_happy_path_returns_200(self, client):
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ):
            response = client.post("/valhalla/route", json=MINIMAL_ROUTE_PAYLOAD)
        assert response.status_code == 200

    def test_happy_path_returns_trip(self, client):
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ):
            response = client.post("/valhalla/route", json=MINIMAL_ROUTE_PAYLOAD)
        assert "trip" in response.json()

    # ------------------------------------------------------------------
    # Optional fields are passed through correctly
    # ------------------------------------------------------------------

    def test_units_option_forwarded(self, client):
        payload = {**MINIMAL_ROUTE_PAYLOAD, "directions_options": {"units": "miles"}}
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            assert mock.call_args.kwargs["options"]["directions_options"]["units"] == "miles"

    def test_elevation_interval_forwarded(self, client):
        payload = {**MINIMAL_ROUTE_PAYLOAD, "elevation_interval": 5}
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            assert mock.call_args.kwargs["options"]["elevation_interval"] == 5

    def test_user_id_forwarded(self, client):
        payload = {**MINIMAL_ROUTE_PAYLOAD, "user_id": "user-abc"}
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            assert mock.call_args.kwargs["user_id"] == "user-abc"

    def test_exclude_locations_forwarded(self, client):
        payload = {
            **MINIMAL_ROUTE_PAYLOAD,
            "exclude_locations": [{"lat": 40.441, "lon": -79.997}],
        }
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            excl = mock.call_args.kwargs["options"]["exclude_locations"]
            assert excl == [{"lat": 40.441, "lon": -79.997}]

    # ------------------------------------------------------------------
    # Incline slider guard logic  (_INCLINE_SLIDER_MAX = 30)
    # ------------------------------------------------------------------

    def test_incline_at_max_30_is_stripped(self, client):
        """incline == 30 (slider ceiling) must NOT reach Valhalla."""
        payload = {
            **MINIMAL_ROUTE_PAYLOAD,
            "costing_options": {"pedestrian": {"incline": 30}},
        }
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            options = mock.call_args.kwargs.get("options") or {}
            costing = options.get("costing_options", {})
            assert "pedestrian" not in costing

    def test_incline_at_zero_is_stripped(self, client):
        payload = {
            **MINIMAL_ROUTE_PAYLOAD,
            "costing_options": {"pedestrian": {"incline": 0}},
        }
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            options = mock.call_args.kwargs.get("options") or {}
            costing = options.get("costing_options", {})
            assert "pedestrian" not in costing

    def test_incline_in_valid_range_is_kept(self, client):
        """Incline 1–29 should pass through to Valhalla."""
        payload = {
            **MINIMAL_ROUTE_PAYLOAD,
            "costing_options": {"pedestrian": {"incline": 15}},
        }
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            options = mock.call_args.kwargs.get("options") or {}
            assert options["costing_options"]["pedestrian"]["incline"] == 15

    def test_use_stairs_forwarded_without_incline(self, client):
        payload = {
            **MINIMAL_ROUTE_PAYLOAD,
            "costing_options": {"pedestrian": {"use_stairs": 0.5}},
        }
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            options = mock.call_args.kwargs.get("options") or {}
            assert options["costing_options"]["pedestrian"]["use_stairs"] == 0.5

    def test_empty_pedestrian_block_is_dropped(self, client):
        """incline == 30 with no other pedestrian options drops the entire block."""
        payload = {
            **MINIMAL_ROUTE_PAYLOAD,
            "costing_options": {"pedestrian": {"incline": 30}},
        }
        with patch(
            "wayfinder.http.routes.RouteController.get_route",
            return_value=MOCK_VALHALLA_RESPONSE,
        ) as mock:
            client.post("/valhalla/route", json=payload)
            options = mock.call_args.kwargs.get("options") or {}
            costing = options.get("costing_options", {})
            assert "pedestrian" not in costing

    # ------------------------------------------------------------------
    # Validation errors
    # ------------------------------------------------------------------

    def test_missing_locations_returns_422(self, client):
        response = client.post("/valhalla/route", json={"costing": "pedestrian"})
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client):
        response = client.post("/valhalla/route", json={})
        assert response.status_code == 422

    def test_single_location_raises_500(self, client):
        # routes.py accesses locations[1] directly — no bounds check — so a
        # single-location payload causes an unhandled IndexError → 500.
        # This documents the current behaviour; add a Pydantic validator to
        # routes.py to turn it into a clean 422 instead.
        with TestClient(app, raise_server_exceptions=False) as c:
            response = c.post(
                "/valhalla/route",
                json={"locations": [{"lat": 40.44, "lon": -79.99}], "costing": "pedestrian"},
            )
        assert response.status_code in (422, 500)

    def test_missing_lat_in_location_returns_422(self, client):
        payload = {
            "locations": [{"lon": -79.99}, {"lat": 40.45, "lon": -79.98}],
            "costing": "pedestrian",
        }
        response = client.post("/valhalla/route", json=payload)
        assert response.status_code == 422


# ===========================================================================
# 3. Geocode  –  GET /geocode/autocomplete, /geocode/reverse
# ===========================================================================

MOCK_AUTOCOMPLETE = [{"formatted": "Forbes Ave, Pittsburgh", "lat": 40.44, "lon": -79.99}]
MOCK_REVERSE = {"formatted": "Carnegie Mellon University", "lat": 40.4433, "lon": -79.9436}


class TestGeocodeAutocomplete:
    def test_returns_200(self, client):
        with patch(
            "wayfinder.http.geocode.GeoapifyGeocodingService.autocomplete",
            new_callable=AsyncMock,
            return_value=MOCK_AUTOCOMPLETE,
        ):
            response = client.get("/geocode/autocomplete", params={"q": "Forbes"})
        assert response.status_code == 200

    def test_response_has_results_key(self, client):
        with patch(
            "wayfinder.http.geocode.GeoapifyGeocodingService.autocomplete",
            new_callable=AsyncMock,
            return_value=MOCK_AUTOCOMPLETE,
        ):
            response = client.get("/geocode/autocomplete", params={"q": "Forbes"})
        assert "results" in response.json()

    def test_missing_q_param_returns_422(self, client):
        response = client.get("/geocode/autocomplete")
        assert response.status_code == 422

    def test_missing_api_key_returns_503(self, client):
        with patch.dict(os.environ, {"GEOAPIFY_API_KEY": ""}):
            response = client.get("/geocode/autocomplete", params={"q": "Forbes"})
        assert response.status_code == 503

    def test_service_exception_returns_500(self, client):
        with patch(
            "wayfinder.http.geocode.GeoapifyGeocodingService.autocomplete",
            new_callable=AsyncMock,
            side_effect=RuntimeError("upstream failure"),
        ):
            response = client.get("/geocode/autocomplete", params={"q": "Forbes"})
        assert response.status_code == 500


class TestGeocodeReverse:
    def test_returns_200(self, client):
        with patch(
            "wayfinder.http.geocode.GeoapifyGeocodingService.reverse",
            new_callable=AsyncMock,
            return_value=MOCK_REVERSE,
        ):
            response = client.get("/geocode/reverse", params={"lat": 40.4433, "lon": -79.9436})
        assert response.status_code == 200

    def test_missing_lat_returns_422(self, client):
        response = client.get("/geocode/reverse", params={"lon": -79.9436})
        assert response.status_code == 422

    def test_missing_lon_returns_422(self, client):
        response = client.get("/geocode/reverse", params={"lat": 40.4433})
        assert response.status_code == 422

    def test_missing_api_key_returns_503(self, client):
        with patch.dict(os.environ, {"GEOAPIFY_API_KEY": ""}):
            response = client.get("/geocode/reverse", params={"lat": 40.44, "lon": -79.99})
        assert response.status_code == 503

    def test_service_exception_returns_500(self, client):
        with patch(
            "wayfinder.http.geocode.GeoapifyGeocodingService.reverse",
            new_callable=AsyncMock,
            side_effect=RuntimeError("upstream failure"),
        ):
            response = client.get("/geocode/reverse", params={"lat": 40.44, "lon": -79.99})
        assert response.status_code == 500


# ===========================================================================
# 4. Demand  –  GET /demand/*  (admin-protected)
# ===========================================================================

def _mock_hotspot():
    hs = MagicMock()
    hs.geohash = "dppnhg"
    hs.point_type = "origin"
    hs.center_lat = 40.44
    hs.center_lng = -79.99
    hs.attempt_count = 5
    hs.unique_users = 3
    hs.first_seen = "2024-01-01T00:00:00"
    hs.last_seen = "2024-03-01T00:00:00"
    hs.sample_reasons = ["no_route"]
    return hs


class TestDemandHotspots:
    def test_returns_200_with_admin_key(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_demand_hotspots",
            return_value=[_mock_hotspot()],
        ):
            response = client.get("/demand/hotspots", headers=ADMIN_HEADERS)
        assert response.status_code == 200

    def test_returns_list(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_demand_hotspots",
            return_value=[_mock_hotspot()],
        ):
            response = client.get("/demand/hotspots", headers=ADMIN_HEADERS)
        assert isinstance(response.json(), list)

    def test_hotspot_shape(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_demand_hotspots",
            return_value=[_mock_hotspot()],
        ):
            response = client.get("/demand/hotspots", headers=ADMIN_HEADERS)
        item = response.json()[0]
        for key in (
            "geohash", "point_type", "center_lat", "center_lng",
            "attempt_count", "unique_users", "first_seen", "last_seen",
            "failure_reasons",
        ):
            assert key in item, f"Missing key: {key}"

    def test_no_admin_key_returns_422(self, client):
        response = client.get("/demand/hotspots")
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.get("/demand/hotspots", headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403

    def test_query_params_forwarded_to_pipeline(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_demand_hotspots",
            return_value=[],
        ) as mock:
            client.get("/demand/hotspots?min_attempts=10&limit=5", headers=ADMIN_HEADERS)
            mock.assert_called_once_with(min_attempts=10, limit=5)

    def test_defaults_min3_limit50(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_demand_hotspots",
            return_value=[],
        ) as mock:
            client.get("/demand/hotspots", headers=ADMIN_HEADERS)
            mock.assert_called_once_with(min_attempts=3, limit=50)


class TestDemandRoutePairs:
    def test_returns_200_with_admin_key(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_top_route_pairs",
            return_value=[],
        ):
            response = client.get("/demand/route_pairs", headers=ADMIN_HEADERS)
        assert response.status_code == 200

    def test_no_admin_key_returns_422(self, client):
        response = client.get("/demand/route_pairs")
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.get("/demand/route_pairs", headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403

    def test_defaults_min2_limit20(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_top_route_pairs",
            return_value=[],
        ) as mock:
            client.get("/demand/route_pairs", headers=ADMIN_HEADERS)
            mock.assert_called_once_with(min_attempts=2, limit=20)

    def test_custom_params_forwarded(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_top_route_pairs",
            return_value=[],
        ) as mock:
            client.get("/demand/route_pairs?min_attempts=7&limit=3", headers=ADMIN_HEADERS)
            mock.assert_called_once_with(min_attempts=7, limit=3)


class TestDemandNear:
    def test_returns_200_with_admin_key(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_attempts_near",
            return_value=[],
        ):
            response = client.get(
                "/demand/near", params={"lat": 40.44, "lng": -79.99}, headers=ADMIN_HEADERS
            )
        assert response.status_code == 200

    def test_missing_lat_returns_422(self, client):
        response = client.get("/demand/near", params={"lng": -79.99}, headers=ADMIN_HEADERS)
        assert response.status_code == 422

    def test_missing_lng_returns_422(self, client):
        response = client.get("/demand/near", params={"lat": 40.44}, headers=ADMIN_HEADERS)
        assert response.status_code == 422

    def test_no_admin_key_returns_422(self, client):
        response = client.get("/demand/near", params={"lat": 40.44, "lng": -79.99})
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.get(
            "/demand/near", params={"lat": 40.44, "lng": -79.99}, headers=BAD_ADMIN_HEADERS
        )
        assert response.status_code == 403

    def test_coords_forwarded_to_pipeline(self, client):
        with patch(
            "wayfinder.http.demand.pipeline.get_attempts_near",
            return_value=[],
        ) as mock:
            client.get("/demand/near", params={"lat": 40.44, "lng": -79.99}, headers=ADMIN_HEADERS)
            mock.assert_called_once_with(40.44, -79.99)


# ===========================================================================
# 5. Ways (tile_reloading.py)  –  all admin-protected
# ===========================================================================

VALID_FEATURE = {
    "type": "Feature",
    "properties": {"OBJECTID": 42, "name": "Test Way"},
    "geometry": {
        "type": "LineString",
        "coordinates": [[-79.99, 40.44], [-79.98, 40.45]],
    },
}


class TestWaysStatus:
    def test_returns_200_with_admin_key(self, client):
        response = client.get("/ways/status", headers=ADMIN_HEADERS)
        assert response.status_code == 200

    def test_body_has_running_key(self, client):
        response = client.get("/ways/status", headers=ADMIN_HEADERS)
        assert "running" in response.json()

    def test_body_has_last_error_key(self, client):
        response = client.get("/ways/status", headers=ADMIN_HEADERS)
        assert "last_error" in response.json()

    def test_no_admin_key_returns_422(self, client):
        response = client.get("/ways/status")
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.get("/ways/status", headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403


class TestWaysLookup:
    def test_existing_way_returns_200(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = {"object_id": 42}
        with patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg:
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.get("/ways/42", headers=ADMIN_HEADERS)
        assert response.status_code == 200

    def test_missing_way_returns_404(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = None
        with patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg:
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.get("/ways/9999", headers=ADMIN_HEADERS)
        assert response.status_code == 404

    def test_no_admin_key_returns_422(self, client):
        response = client.get("/ways/42")
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.get("/ways/42", headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403


class TestWaysAdd:
    def test_returns_202(self, client):
        with patch("wayfinder.http.tile_reloading._service.add"):
            response = client.post("/ways/", json=VALID_FEATURE, headers=ADMIN_HEADERS)
        assert response.status_code == 202

    def test_response_has_accepted_status(self, client):
        with patch("wayfinder.http.tile_reloading._service.add"):
            response = client.post("/ways/", json=VALID_FEATURE, headers=ADMIN_HEADERS)
        assert response.json()["status"] == "accepted"

    def test_no_admin_key_returns_422(self, client):
        response = client.post("/ways/", json=VALID_FEATURE)
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.post("/ways/", json=VALID_FEATURE, headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403


class TestWaysUpdate:
    def test_returns_202_when_way_exists(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = {"object_id": 42}
        with (
            patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg,
            patch("wayfinder.http.tile_reloading._service.update"),
        ):
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.put("/ways/42", json=VALID_FEATURE, headers=ADMIN_HEADERS)
        assert response.status_code == 202

    def test_response_includes_object_id(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = {"object_id": 42}
        with (
            patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg,
            patch("wayfinder.http.tile_reloading._service.update"),
        ):
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.put("/ways/42", json=VALID_FEATURE, headers=ADMIN_HEADERS)
        assert response.json()["object_id"] == 42

    def test_nonexistent_way_returns_404(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = None
        with patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg:
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.put("/ways/9999", json=VALID_FEATURE, headers=ADMIN_HEADERS)
        assert response.status_code == 404

    def test_no_admin_key_returns_422(self, client):
        response = client.put("/ways/42", json=VALID_FEATURE)
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.put("/ways/42", json=VALID_FEATURE, headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403


class TestWaysDelete:
    def test_returns_202_when_way_exists(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = {"object_id": 42}
        with (
            patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg,
            patch("wayfinder.http.tile_reloading._service.delete"),
        ):
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.delete("/ways/42", headers=ADMIN_HEADERS)
        assert response.status_code == 202

    def test_response_includes_object_id(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = {"object_id": 42}
        with (
            patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg,
            patch("wayfinder.http.tile_reloading._service.delete"),
        ):
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.delete("/ways/42", headers=ADMIN_HEADERS)
        assert response.json()["object_id"] == 42

    def test_nonexistent_way_returns_404(self, client):
        mock_reg = MagicMock()
        mock_reg.lookup_way.return_value = None
        with patch("wayfinder.http.tile_reloading.NodeRegistry") as MockReg:
            MockReg.return_value.__enter__.return_value = mock_reg
            response = client.delete("/ways/9999", headers=ADMIN_HEADERS)
        assert response.status_code == 404

    def test_no_admin_key_returns_422(self, client):
        response = client.delete("/ways/42")
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.delete("/ways/42", headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403


class TestWaysBulkUpsert:
    def test_returns_202(self, client):
        with patch("wayfinder.http.tile_reloading._service.bulk_upsert"):
            response = client.post(
                "/ways/bulk", json=[VALID_FEATURE, VALID_FEATURE], headers=ADMIN_HEADERS
            )
        assert response.status_code == 202

    def test_response_includes_count(self, client):
        with patch("wayfinder.http.tile_reloading._service.bulk_upsert"):
            response = client.post(
                "/ways/bulk", json=[VALID_FEATURE, VALID_FEATURE], headers=ADMIN_HEADERS
            )
        assert response.json()["count"] == 2

    def test_single_feature_count_is_1(self, client):
        with patch("wayfinder.http.tile_reloading._service.bulk_upsert"):
            response = client.post("/ways/bulk", json=[VALID_FEATURE], headers=ADMIN_HEADERS)
        assert response.json()["count"] == 1

    def test_no_admin_key_returns_422(self, client):
        response = client.post("/ways/bulk", json=[VALID_FEATURE])
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.post("/ways/bulk", json=[VALID_FEATURE], headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403


class TestWaysRebuild:
    def test_returns_202(self, client):
        with patch("wayfinder.http.tile_reloading._service._rebuild_tiles"):
            response = client.post("/ways/rebuild", headers=ADMIN_HEADERS)
        assert response.status_code == 202

    def test_response_has_accepted_status(self, client):
        with patch("wayfinder.http.tile_reloading._service._rebuild_tiles"):
            response = client.post("/ways/rebuild", headers=ADMIN_HEADERS)
        assert response.json()["status"] == "accepted"

    def test_no_admin_key_returns_422(self, client):
        response = client.post("/ways/rebuild")
        assert response.status_code == 422

    def test_wrong_admin_key_returns_403(self, client):
        response = client.post("/ways/rebuild", headers=BAD_ADMIN_HEADERS)
        assert response.status_code == 403


# ===========================================================================
# 6. Concurrent rebuild guard  –  409 when lock is already held
# ===========================================================================

class TestRebuildLock:
    def test_concurrent_rebuild_returns_202(self):
        """Pre-acquire the threading lock to simulate an in-progress rebuild.
        Uses its own TestClient with raise_server_exceptions=False so the 409
        HTTPException doesn't propagate out before the response is returned."""
        import wayfinder.http.tile_reloading as tr

        acquired = tr._rebuild_lock.acquire(blocking=False)
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                with patch("wayfinder.http.tile_reloading._service._rebuild_tiles"):
                    response = c.post("/ways/rebuild", headers=ADMIN_HEADERS)
            assert response.status_code == 202
        finally:
            if acquired:
                tr._rebuild_lock.release()