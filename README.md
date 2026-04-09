# 🗺️ SPC Wayfinding

> An accessibility-focused sidewalk routing application for Southwestern Pennsylvania, built on real sidewalk data from the Southwestern Pennsylvania Commission (SPC).

![Wayfnding Demo Screenshot](./static/WayfindingDemo.png)

## Overview

SPC Wayfinding helps users navigate sidewalks and pedestrian infrastructure focused on the Southwestern Pennsylvania region. Unlike general-purpose mapping tools, this application integrates SPC's own sidewalk network data and supports **accessibility routing profiles** — allowing users to find routes that account for FILL IN  factors relevant to people with mobility needs.

The application primarily covers the geographic bounding box of the SPC region:

- **Longitude:** -80.52° to -78.80°
- **Latitude:** 39.72° to 41.15°

---

## Architecture

The app is composed of **four Docker services** that start up in a specific order:

```
Browser (port 5173)
      │
      ▼
  frontend          – Vite/Node.js frontend
      │
      ▼
    api             – Python/FastAPI backend (port 8000)
      │         │
      ▼         ▼
  valhalla    postgres
  routing     database
  engine      (port 5432)
 (port 8002)
```

| Service | Image / Build | Port | Role |
|---|---|---|---|
| `frontend` | `node:22-alpine` | `5173` | Vite-based frontend UI served to the browser |
| `api` | Custom (`Dockerfile`) | `8000` | FastAPI backend — handles routing requests, logging, and business logic |
| `valhalla` | Custom (`Dockerfile.valhalla`) | `8002` | [Valhalla](https://github.com/valhalla/valhalla) routing engine — computes pedestrian paths from OSM + SPC data |
| `postgres` | `postgres:16` | `5432` | PostgreSQL database for logging and persistent data |

### Startup Order

Docker Compose enforces a strict startup sequence to ensure each service is ready before the next one depends on it:

1. **`valhalla`** starts first and bootstraps the routing tile data
2. **`postgres`** starts after Valhalla and waits until it passes a health check
3. **`api`** starts only after both Postgres and Valhalla are healthy
4. **`frontend`** starts last, once the API is healthy

---

## Prerequisites

- [Docker](https://www.docker.com/get-started) (v20+ recommended)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- Approximately **2 GB of free disk space** (routing tile data for the SPC region is large)
- A **Geoapify API key** (used for geocoding — converting addresses to coordinates)

---

## Environment Variables

Create a `.env` file in the project root before running. The following variables are required:

```env
# API key for the Geoapify geocoding service
GEOAPIFY_API_KEY=your_geoapify_key_here

# Secret key for admin-protected API endpoints
ADMIN_API_KEY=your_admin_key_here

# Set to "true" to force Valhalla to rebuild routing tiles from scratch
# Only needed if you update the underlying map/sidewalk data
REBUILD_TILES=false
```

> ⚠️ Never commit your `.env` file to version control. Add it to `.gitignore`.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/wayfinding.git
cd wayfinding
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### 3. Build and start all services

```bash
docker-compose up -d --build
```

This single command will:
- Build the `api` and `valhalla` Docker images from the local Dockerfiles
- Pull the `postgres` and `node` base images
- Run `bootstrap_tiles.sh` inside the Valhalla container to download and process OSM + SPC sidewalk data into routing tiles
- Start all four services in the correct order in the background

>   **The first build takes a while.** Valhalla has up to a 10-minute startup window (`start_period: 600s`) to finish processing map tiles before it is considered healthy. Subsequent starts are much faster since tiles are cached in `./data/valhalla`.

>   **If you are developing on Windows**, ensure that your Wayfinding\scripts\bootstrap_tiles.sh script is saved with LF line endings rather than CRLF(Go to the file and click CRLF in bottom right and switch to LF). Docker runs a Linux environment that cannot interpret Windows-style line endings which are automatically appended during Git download.

### 4. Verify all services are running

```bash
docker-compose ps
```

All four services should show a status of `Up` (or `Up (healthy)` once health checks pass).

You can also check individual service health:

```bash
# Valhalla routing engine
curl http://localhost:8002/status

# API backend
curl http://localhost:8000/valhalla/health
```

### 5. Open the app

Navigate to **http://localhost:5173** in your browser.

---

## Useful Commands

```bash
# Start services without rebuilding images
docker-compose up -d

# View live logs from all services
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f api

# Stop all services
docker-compose down

# Stop all services and delete the database volume (full reset)
docker-compose down -v

# Force Valhalla to rebuild routing tiles
REBUILD_TILES=true docker-compose up -d
```

---

## Data & Tile Caching

Valhalla routing tiles are stored in `./data/valhalla/` on your host machine (mounted as a Docker volume). This means:

- Tiles persist across container restarts — you won't need to reprocess them every time
- To update the routing data (e.g., after new SPC sidewalk data is available), set `REBUILD_TILES=true` and restart

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Node.js 22, Vite |
| Backend API | Python 3.11+, FastAPI, Uvicorn |
| Routing Engine | [Valhalla](https://github.com/valhalla/valhalla) (via [gis-ops Docker image](https://github.com/gis-ops/docker-valhalla)) |
| Map Data Processing | [osmium-tool](https://osmcode.org/osmium-tool/), GDAL, pyosmium |
| Database | PostgreSQL 16 |
| Geocoding | [Geoapify](https://www.geoapify.com/) |
| Containerization | Docker, Docker Compose |

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## License

<!-- TODO: Add your license -->

---

## Acknowledgments

- [Southwestern Pennsylvania Commission (SPC)](https://www.spcregion.org/) for sidewalk network data
- [Valhalla](https://github.com/valhalla/valhalla) open-source routing engine
- [OpenStreetMap](https://www.openstreetmap.org/) contributors
