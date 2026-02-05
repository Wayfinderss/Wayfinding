from typing import Optional
from pathlib import Path

# Absolute project root
ROOT = Path(__file__).resolve().parent

VALHALLA_DATA = ROOT / "tiles"
TRANSIT_DIR = ROOT / "transit"
TRANSIT_FEEDS_DIR = ROOT / "transit_feeds"
ELEVATION_DIR = ROOT / "elevation"

config = {
    "mjolnir": {
        "max_cache_size": 1000000000,
        "id_table_size": 1300000000,
        "use_lru_mem_cache": False,
        "lru_mem_cache_hard_control": False,
        "use_simple_mem_cache": False,

        "user_agent": Optional[str],
        "tile_url": Optional[str],
        "tile_url_gz": Optional[bool],
        "tile_url_user_pw": Optional[str],
        "concurrency": Optional[int],

        # 🔴 FIXED PATHS
        "tile_dir": str(VALHALLA_DATA),
        "tile_extract": str(VALHALLA_DATA / "tiles.tar"),
        "traffic_extract": str(VALHALLA_DATA / "traffic.tar"),

        "incident_dir": Optional[str],
        "incident_log": Optional[str],
        "shortcut_caching": Optional[bool],
        "graph_lua_name": Optional[str],

        "admin": str(VALHALLA_DATA / "admin.sqlite"),
        "landmarks": str(VALHALLA_DATA / "landmarks.sqlite"),
        "timezone": str(VALHALLA_DATA / "tz_world.sqlite"),

        "transit_dir": str(TRANSIT_DIR),
        "transit_feeds_dir": str(TRANSIT_FEEDS_DIR),

        "transit_bounding_box": Optional[str],
        "transit_pbf_limit": 20000,

        "hierarchy": True,
        "shortcuts": True,

        "keep_all_osm_node_ids": False,
        "keep_osm_node_ids": False,

        "include_platforms": False,
        "include_driveways": True,
        "include_construction": False,
        "include_bicycle": True,
        "include_pedestrian": True,
        "include_driving": True,

        "import_bike_share_stations": False,
        "global_synchronized_cache": False,
        "max_concurrent_reader_users": 1,
        "reclassify_links": True,

        "default_speeds_config": Optional[str],

        "data_processing": {
            "infer_internal_intersections": True,
            "infer_turn_channels": True,
            "apply_country_overrides": True,
            "grid_divisions_within_tile": 32,
            "use_admin_db": True,
            "use_direction_on_ways": False,
            "allow_alt_name": False,
            "use_urban_tag": False,
            "use_rest_area": False,
            "scan_tar": False,
        },

        "logging": {
            "type": "std_out",
            "color": True,
            "file_name": "path_to_some_file.log",
            "max_file_size": Optional[int],
            "max_archived_files": Optional[int],
        },
    },

    "additional_data": {
        "elevation": str(ELEVATION_DIR),
        "elevation_url": Optional[str],
        "elevation_url_user_pw": Optional[str],
    },
    "loki": {
        "actions": [
            "locate",
            "route",
            "height",
            "sources_to_targets",
            "optimized_route",
            "isochrone",
            "trace_route",
            "trace_attributes",
            "transit_available",
            "expansion",
            "centroid",
            "status",
            "tile",
        ],
        "use_connectivity": True,
        "service_defaults": {
            "radius": 0,
            "minimum_reachability": 50,
            "search_cutoff": 35000,
            "node_snap_tolerance": 5,
            "street_side_tolerance": 5,
            "street_side_max_distance": 1000,
            "heading_tolerance": 60,
            "mvt_min_zoom_road_class": [7, 7, 8, 11, 11, 12, 13, 14],
            "mvt_cache_dir": Optional[str],
            "mvt_cache_min_zoom": 11,
        },
        "logging": {
            "type": "std_out",
            "color": True,
            "file_name": "path_to_some_file.log",
            "long_request": 100.0,
            "max_file_size": Optional[int],
            "max_archived_files": Optional[int],
        },
        "service": {"proxy": "ipc:///tmp/loki"},
    },
    "thor": {
        "logging": {
            "type": "std_out",
            "color": True,
            "file_name": "path_to_some_file.log",
            "long_request": 110.0,
            "max_file_size": Optional[int],
            "max_archived_files": Optional[int],
        },
        "source_to_target_algorithm": "select_optimal",
        "service": {"proxy": "ipc:///tmp/thor"},
        "max_reserved_labels_count_astar": 2000000,
        "max_reserved_labels_count_bidir_astar": 1000000,
        "max_reserved_labels_count_dijkstras": 4000000,
        "max_reserved_labels_count_bidir_dijkstras": 2000000,
        "clear_reserved_memory": False,
        "extended_search": False,
        "costmatrix": {
            "check_reverse_connection": True,
            "allow_second_pass": False,
            "max_reserved_locations": 25,
            "max_iterations": 2800,
            "min_iterations": 100,
            "hierarchy_limits": {
                "max_up_transitions": {
                    "1": 400,
                    "2": 100,
                },
                "expand_within_distance": {"0": 1e8, "1": 20000, "2": 5000},
            },
        },
        "bidirectional_astar": {
            "threshold_delta": 420.0,
            "alternative_cost_extend": 1.2,
            "alternative_iterations_delta": 100000,
            "hierarchy_limits": {
                "max_up_transitions": {
                    "1": 400,
                    "2": 100,
                },
                "expand_within_distance": {"0": 1e8, "1": 20000, "2": 5000},
            },
        },
        "unidirectional_astar": {
            "hierarchy_limits": {
                "max_up_transitions": {
                    "1": 400,
                    "2": 100,
                },
                "expand_within_distance": {"0": 1e8, "1": 100000, "2": 5000},
            }
        },
    },
    "odin": {
        "logging": {
            "type": "std_out",
            "color": True,
            "file_name": "path_to_some_file.log",
            "max_file_size": Optional[int],
            "max_archived_files": Optional[int],
        },
        "service": {"proxy": "ipc:///tmp/odin"},
        "markup_formatter": {
            "markup_enabled": False,
            "phoneme_format": "<TEXTUAL_STRING> (<span class=<QUOTES>phoneme<QUOTES>>/<VERBAL_STRING>/</span>)",
        },
    },
    "meili": {
        "mode": "auto",
        "customizable": [
            "mode",
            "search_radius",
            "turn_penalty_factor",
            "gps_accuracy",
            "interpolation_distance",
            "sigma_z",
            "beta",
            "max_route_distance_factor",
            "max_route_time_factor",
        ],
        "verbose": False,
        "default": {
            "sigma_z": 4.07,
            "gps_accuracy": 5.0,
            "beta": 3,
            "max_route_distance_factor": 5,
            "max_route_time_factor": 5,
            "max_search_radius": 100,
            "breakage_distance": 2000,
            "interpolation_distance": 10,
            "search_radius": 50,
            "geometry": False,
            "route": True,
            "turn_penalty_factor": 0,
        },
        "auto": {"turn_penalty_factor": 200, "search_radius": 50},
        "pedestrian": {"turn_penalty_factor": 100, "search_radius": 50},
        "bicycle": {"turn_penalty_factor": 140},
        "multimodal": {"turn_penalty_factor": 70},
        "logging": {
            "type": "std_out",
            "color": True,
            "file_name": "path_to_some_file.log",
            "max_file_size": Optional[int],
            "max_archived_files": Optional[int],
        },
        "service": {"proxy": "ipc:///tmp/meili"},
        "grid": {"size": 500, "cache_size": 100240},
    },
    "httpd": {
        "service": {
            "listen": "tcp://*:8002",
            "loopback": "ipc:///tmp/loopback",
            "interrupt": "ipc:///tmp/interrupt",
            "drain_seconds": 28,
            "shutdown_seconds": 1,
            "timeout_seconds": -1,
        }
    },
    "service_limits": {
        "auto": {
            "max_distance": 5000000.0,
            "max_locations": 20,
            "max_matrix_distance": 400000.0,
            "max_matrix_location_pairs": 2500,
        },
        "bus": {
            "max_distance": 5000000.0,
            "max_locations": 50,
            "max_matrix_distance": 400000.0,
            "max_matrix_location_pairs": 2500,
        },
        "taxi": {
            "max_distance": 5000000.0,
            "max_locations": 20,
            "max_matrix_distance": 400000.0,
            "max_matrix_location_pairs": 2500,
        },
        "pedestrian": {
            "max_distance": 250000.0,
            "max_locations": 50,
            "max_matrix_distance": 200000.0,
            "max_matrix_location_pairs": 2500,
            "min_transit_walking_distance": 1,
            "max_transit_walking_distance": 10000,
        },
        "motor_scooter": {
            "max_distance": 500000.0,
            "max_locations": 50,
            "max_matrix_distance": 200000.0,
            "max_matrix_location_pairs": 2500,
        },
        "motorcycle": {
            "max_distance": 500000.0,
            "max_locations": 50,
            "max_matrix_distance": 200000.0,
            "max_matrix_location_pairs": 2500,
        },
        "bicycle": {
            "max_distance": 500000.0,
            "max_locations": 50,
            "max_matrix_distance": 200000.0,
            "max_matrix_location_pairs": 2500,
        },
        "multimodal": {
            "max_distance": 500000.0,
            "max_locations": 50,
            "max_matrix_distance": 0.0,
            "max_matrix_location_pairs": 0,
        },
        "status": {"allow_verbose": False},
        "transit": {
            "max_distance": 500000.0,
            "max_locations": 50,
            "max_matrix_distance": 200000.0,
            "max_matrix_location_pairs": 2500,
        },
        "truck": {
            "max_distance": 5000000.0,
            "max_locations": 20,
            "max_matrix_distance": 400000.0,
            "max_matrix_location_pairs": 2500,
        },
        "skadi": {"max_shape": 750000, "min_resample": 10.0},
        "isochrone": {
            "max_contours": 4,
            "max_time_contour": 120,
            "max_distance": 25000.0,
            "max_locations": 1,
            "max_distance_contour": 200,
        },
        "trace": {
            "max_distance": 200000.0,
            "max_gps_accuracy": 100.0,
            "max_search_radius": 100.0,
            "max_shape": 16000,
            "max_alternates": 3,
            "max_alternates_shape": 100,
        },
        "bikeshare": {
            "max_distance": 500000.0,
            "max_locations": 50,
            "max_matrix_distance": 200000.0,
            "max_matrix_location_pairs": 2500,
        },
        "centroid": {"max_distance": 200000.0, "max_locations": 5},
        "max_exclude_locations": 50,
        "max_reachability": 100,
        "max_radius": 200,
        "max_timedep_distance": 500000,
        "max_timedep_distance_matrix": 0,
        "max_alternates": 2,
        "max_exclude_polygons_length": 10000,
        "min_linear_cost_factor": 1,
        "max_linear_cost_edges": 50000,
        "max_distance_disable_hierarchy_culling": 0,
        "hierarchy_limits": {
            "allow_modification": False,
            "costmatrix": {
                "max_allowed_up_transitions": {
                    "1": 400,
                    "2": 100,
                },
                "max_expand_within_distance": {"0": 1e8, "1": 100000, "2": 5000},
            },
            "unidirectional_astar": {
                "max_allowed_up_transitions": {
                    "1": 400,
                    "2": 100,
                },
                "max_expand_within_distance": {"0": 1e8, "1": 100000, "2": 5000},
            },
            "bidirectional_astar": {
                "max_allowed_up_transitions": {
                    "1": 400,
                    "2": 100,
                },
                "max_expand_within_distance": {"0": 1e8, "1": 20000, "2": 5000},
            },
        },
        "allow_hard_exclusions": False,
    },
    "statsd": {
        "host": Optional[str],
        "port": 8125,
        "prefix": "valhalla",
        "batch_size": Optional[int],
        "tags": Optional[list],
    },
}