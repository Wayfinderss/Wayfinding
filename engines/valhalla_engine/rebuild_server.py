"""
Lightweight internal HTTP server that runs inside the valhalla container.
Runs as PID 1 and manages valhalla_service as a child subprocess.

Exposes:
  POST /rebuild  — builds tiles then restarts valhalla_service
  GET  /health   — liveness check
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from engines.valhalla_engine.tile_builder import ValhallaTileBuilder

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VALHALLA_CONFIG  = Path(os.environ.get("VALHALLA_CONFIG", "/app/data/valhalla/valhalla.json"))
NETWORK_PBF      = Path(os.environ.get("NETWORK_PBF",     "/app/data/valhalla/network.osm.pbf"))
TILES_DIR        = Path(os.environ.get("VALHALLA_TILES",  "/app/data/valhalla/tiles"))
LISTEN_PORT      = int(os.environ.get("REBUILD_SERVER_PORT", "9001"))
VALHALLA_BIN     = os.environ.get("VALHALLA_BIN", "/usr/local/bin/valhalla_service")
VALHALLA_THREADS = os.environ.get("VALHALLA_THREADS", "1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [rebuild_server] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

_rebuild_lock = threading.Lock()
_builder = ValhallaTileBuilder(TILES_DIR)

# ---------------------------------------------------------------------------
# valhalla_service process management
# ---------------------------------------------------------------------------

_valhalla_proc: subprocess.Popen | None = None
_valhalla_lock = threading.Lock()


def start_valhalla() -> None:
    global _valhalla_proc
    with _valhalla_lock:
        log.info("Starting valhalla_service...")
        _valhalla_proc = subprocess.Popen(
            [VALHALLA_BIN, str(VALHALLA_CONFIG), VALHALLA_THREADS],
            env={**os.environ, "PATH": "/usr/local/bin:" + os.environ.get("PATH", "")},
        )
        log.info("valhalla_service started (pid %d)", _valhalla_proc.pid)


def restart_valhalla() -> None:
    global _valhalla_proc
    with _valhalla_lock:
        if _valhalla_proc and _valhalla_proc.poll() is None:
            log.info("Stopping valhalla_service (pid %d)...", _valhalla_proc.pid)
            _valhalla_proc.terminate()
            try:
                _valhalla_proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                log.warning("valhalla_service did not stop cleanly — killing")
                _valhalla_proc.kill()
                _valhalla_proc.wait()
        log.info("Restarting valhalla_service...")
        _valhalla_proc = subprocess.Popen(
            [VALHALLA_BIN, str(VALHALLA_CONFIG), VALHALLA_THREADS],
            env={**os.environ, "PATH": "/usr/local/bin:" + os.environ.get("PATH", "")},
        )
        log.info("valhalla_service restarted (pid %d)", _valhalla_proc.pid)


def watch_valhalla() -> None:
    """Restart valhalla_service if it exits unexpectedly."""
    global _valhalla_proc
    while True:
        time.sleep(2)
        with _valhalla_lock:
            if _valhalla_proc and _valhalla_proc.poll() is not None:
                log.warning("valhalla_service exited unexpectedly — restarting")
                _valhalla_proc = subprocess.Popen(
                    [VALHALLA_BIN, str(VALHALLA_CONFIG), VALHALLA_THREADS],
                    env={**os.environ, "PATH": "/usr/local/bin:" + os.environ.get("PATH", "")},
                )
                log.info("valhalla_service restarted (pid %d)", _valhalla_proc.pid)


# ---------------------------------------------------------------------------
# Rebuild
# ---------------------------------------------------------------------------

def run_rebuild() -> tuple[bool, str]:
    with _rebuild_lock:
        log.info("Rebuild started")
        try:
            _builder.build_and_swap(
                config_path=VALHALLA_CONFIG,
                osm_path=NETWORK_PBF,
            )
        except Exception as exc:
            log.exception("Rebuild failed")
            return False, str(exc)
        log.info("Tiles built — restarting valhalla_service")
        restart_valhalla()
        log.info("Rebuild complete")
        return True, "ok"


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class RebuildHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/rebuild":
            self._respond(404, {"error": "not found"})
            return
        success, message = run_rebuild()
        if success:
            self._respond(200, {"status": "ok"})
        else:
            self._respond(500, {"error": message})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        log.info(fmt, *args)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _handle_shutdown(signum, frame):
    log.info("Shutting down...")
    if _valhalla_proc and _valhalla_proc.poll() is None:
        _valhalla_proc.terminate()
        _valhalla_proc.wait()
    raise SystemExit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    # Start valhalla_service as a managed child
    start_valhalla()

    # Watch for unexpected exits in a background thread
    watcher = threading.Thread(target=watch_valhalla, daemon=True)
    watcher.start()

    server = http.server.HTTPServer(("0.0.0.0", LISTEN_PORT), RebuildHandler)
    log.info("Listening on port %d", LISTEN_PORT)
    server.serve_forever()