# Elevation Profile Feature

## What it does

When you pick a start and end point on the map, a chart appears at the bottom of the screen showing the hills and dips along your route — how much you'll climb, how much you'll descend, and where it happens.

## How it works

There are two separate requests happening when you set a route:

1. **Route request** — goes to our backend, gets the path drawn on the map and the turn-by-turn directions. 

2. **Elevation request** — goes directly to a Valhalla routing server (via a local proxy) and asks for elevation readings every 30 metres along the same route. The response includes an array of height values that get turned into the chart.

These two requests are independent. If the elevation request fails, the map and directions still work normally.

## The chart

- X-axis: distance from start (miles)
- Y-axis: elevation change relative to your starting point (feet)
- Header shows total **↑ gain** and **↓ loss** in feet

The chart only appears when elevation data is available. When you clear the route, it disappears.

## Key files

| File | What it does |
|------|-------------|
| `src/ElevationProfile.tsx` | The chart component (Recharts area chart) |
| `src/Map.tsx` | Triggers the elevation fetch when start + end are set; passes data to the chart |
| `vite.config.ts` | Proxies `/api/route` → `valhalla1.openstreetmap.de/route` |

## Why a separate request?

The backend (`getDirections`) is optimised for our app's routing logic and geocoding. Elevation data needs to come straight from Valhalla with a specific `elevation_interval` parameter that our backend doesn't pass through. Keeping them separate means neither breaks the other.

## Gotcha: GET not POST

The public Valhalla instance at `valhalla1.openstreetmap.de` only accepts the route request as a **GET** with the payload in a `?json=` query string — not as a POST body. The elevation fetch is written accordingly.