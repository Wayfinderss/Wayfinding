from pathlib import Path
import json

class ValhallaConfigBuilder:
    """
    Responsible for generating and writing a complete Valhalla config.

    This is an engine-level lifecycle component.
    It does not depend on wayfinder-layer abstractions.
    """

    def __init__(
        self,
        tiles_dir: Path,
        valhalla_data_dir: Path,
        transit_dir: Path,
        transit_feeds_dir: Path,
        elevation_dir: Path,
        listen_address: str = "tcp://*:8002",
    ):
        self.tiles_dir = tiles_dir
        self.valhalla_data_dir = valhalla_data_dir
        self.transit_dir = transit_dir
        self.transit_feeds_dir = transit_feeds_dir
        self.elevation_dir = elevation_dir
        self.listen_address = listen_address

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_dict(self) -> dict:
        """
        Returns the full Valhalla configuration dictionary.
        """

        return {
            "mjolnir": {
                "tile_dir": str(self.tiles_dir),
                "tile_extract": str(self.tiles_dir / "tiles.tar"),
                "traffic_extract": str(self.tiles_dir / "traffic.tar"),
                "admin": str(self.valhalla_data_dir / "admin.sqlite"),
                "landmarks": str(self.valhalla_data_dir / "landmarks.sqlite"),
                "timezone": str(self.valhalla_data_dir / "tz_world.sqlite"),
                "transit_dir": str(self.transit_dir),
                "transit_feeds_dir": str(self.transit_feeds_dir),
                "hierarchy": True,
                "shortcuts": True,
                "include_bicycle": True,
                "include_pedestrian": True,
                "include_driving": True,
                "data_processing": {
                    "infer_internal_intersections": True,
                    "infer_turn_channels": True,
                    "apply_country_overrides": True,
                    "grid_divisions_within_tile": 32,
                },
                "logging": {
                    "type": "std_out",
                    "color": True,
                },
            },
            "additional_data": {
                "elevation": str(self.elevation_dir),
            },
            "loki": {
                "actions": [
                    "locate",
                    "route",
                    "isochrone",
                    "trace_route",
                    "trace_attributes",
                    "status",
                    "tile",
                ],
                "use_connectivity": True,
                "service": {"proxy": "ipc:///tmp/loki"},
                "logging": {
                    "type": "std_out",
                    "color": True,
                },
            },
            "thor": {
                "source_to_target_algorithm": "select_optimal",
                "service": {"proxy": "ipc:///tmp/thor"},
                "logging": {
                    "type": "std_out",
                    "color": True,
                },
            },
            "odin": {
                "service": {"proxy": "ipc:///tmp/odin"},
                "logging": {
                    "type": "std_out",
                    "color": True,
                },
            },
            "meili": {
                "mode": "auto",
                "default": {
                    "sigma_z": 4.07,
                    "gps_accuracy": 5.0,
                    "beta": 3,
                    "search_radius": 50,
                    "route": True,
                },
                "service": {"proxy": "ipc:///tmp/meili"},
                "logging": {
                    "type": "std_out",
                    "color": True,
                },
            },
            "httpd": {
                "service": {
                    "listen": self.listen_address,
                    "loopback": "ipc:///tmp/loopback",
                    "interrupt": "ipc:///tmp/interrupt",
                    "drain_seconds": 28,
                    "shutdown_seconds": 1,
                    "timeout_seconds": -1,
                }
            },
            "service_limits": {
                "pedestrian": {
                    "max_distance": 250000.0,
                    "max_locations": 50,
                    "max_matrix_distance": 200000.0,
                    "max_matrix_location_pairs": 2500,
                },
                "auto": {
                    "max_distance": 5000000.0,
                    "max_locations": 20,
                    "max_matrix_distance": 400000.0,
                    "max_matrix_location_pairs": 2500,
                },
                "bicycle": {
                    "max_distance": 500000.0,
                    "max_locations": 50,
                    "max_matrix_distance": 200000.0,
                    "max_matrix_location_pairs": 2500,
                },
                "isochrone": {
                    "max_contours": 4,
                    "max_time_contour": 120,
                    "max_distance": 25000.0,
                    "max_locations": 1,
                },
                "trace": {
                    "max_distance": 200000.0,
                    "max_shape": 16000,
                },
            },
        }

    def write(self, output_path: Path) -> Path:
        output_path = Path(output_path)

        # Ensure base directories exist
        self.tiles_dir.mkdir(parents=True, exist_ok=True)
        self.valhalla_data_dir.mkdir(parents=True, exist_ok=True)
        self.transit_dir.mkdir(parents=True, exist_ok=True)
        self.transit_feeds_dir.mkdir(parents=True, exist_ok=True)
        self.elevation_dir.mkdir(parents=True, exist_ok=True)

        config = self.build_dict()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)

        print(f"✓ Valhalla config written to {output_path}")

        return output_path