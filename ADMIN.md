# Wayfinder Admin Panel

The admin panel is a built-in browser UI for managing the sidewalk network and viewing demand analytics. It is served by the frontend at:

**http://localhost:5173/admin**

All actions require the `ADMIN_API_KEY` set in your `.env` file. Enter it in the **Admin API Key** field at the top of the page — it is sent as an `X-API-Key` header with every request.

A **tile rebuild status indicator** polls `GET /ways/status` every 5 seconds and shows whether a rebuild is currently running and whether the last one encountered an error.

---

## Tabs

### Lookup

Look up a sidewalk way by its SPC `OBJECTID` to confirm it exists in the node registry. Returns the internal Valhalla `way_id` mapped to that object.

**Calls:** `GET /ways/{object_id}`

---

### Add

Add a new sidewalk way to the routing network. Paste a GeoJSON Feature with `OBJECTID` in the properties block. On success, the way is merged into the canonical network PBF and a tile rebuild is queued automatically.

**Calls:** `POST /ways/`

**Expected input:**

```json
{
  "type": "Feature",
  "properties": {
    "OBJECTID": 123,
    "surface": "asphalt"
  },
  "geometry": {
    "type": "LineString",
    "coordinates": [[-79.9959, 40.4406], [-79.9900, 40.4450]]
  }
}
```

Returns `202 Accepted` immediately. The tile rebuild runs in the background (~2 minutes). Monitor progress in the rebuild status indicator at the top of the page.

---

### Update

Update an existing sidewalk way. The old way is deleted from the network PBF by `OBJECTID` first, then the new version is inserted, and a tile rebuild is queued. `OBJECTID` must be present in the feature's properties.

**Calls:** `PUT /ways/`

Uses the same GeoJSON Feature format as Add. Returns `404` if the `OBJECTID` does not exist in the registry.

---

### Delete

Remove a sidewalk way from the routing network permanently by its `OBJECTID`. The way is filtered out of the canonical network PBF and a tile rebuild is queued.

**Calls:** `DELETE /ways/{object_id}`

> ⚠️ This is irreversible without re-adding the way manually or re-running the bootstrap process.

---

### Rebuild

Trigger a full tile rebuild from the current network data without making any changes to the sidewalk ways. Useful after manual data corrections or if the routing tiles become stale.

**Calls:** `POST /ways/rebuild`

Routing stays live throughout the rebuild. The existing tiles remain in service until the new ones are built and atomically swapped into place.

---

### Demand Analytics

View analytics derived from **failed routing attempts** — requests where the routing engine could not find a valid path. This data is useful for identifying gaps in the sidewalk network and prioritizing infrastructure improvements.

There are three sub-tabs:

#### Hotspots

Geographic clusters of failed routing requests, grouped by geohash cell. Each hotspot represents a location where users are repeatedly trying to start or end a route but the network cannot serve them.

| Field | Description |
|---|---|
| `geohash` | The geohash cell identifier |
| `point_type` | `"origin"` or `"destination"` |
| `center_lat` / `center_lng` | Approximate center of the cell |
| `attempt_count` | Total failed attempts from/to this cell |
| `unique_users` | Number of distinct users who attempted |
| `first_seen` / `last_seen` | Timestamp range of attempts |
| `failure_reasons` | Sample of recorded failure reasons |

**Filters:** minimum attempt threshold (default 3), result limit (default 50).

#### Route Pairs

The most frequently attempted origin–destination combinations that failed. Useful for identifying specific missing connections in the network — e.g., two neighborhoods with no routable sidewalk path between them.

**Filters:** minimum attempt threshold (default 2), result limit (default 20).

#### Near Location

Returns all failed routing attempts near a specific coordinate. Enter a latitude and longitude to retrieve nearby failures — useful for investigating a specific area of the network.

---

## How Tile Rebuilds Work

Every write operation (Add, Update, Delete, Bulk Upsert, Rebuild) triggers a background tile rebuild. The rebuild process:

1. Builds new tiles into a staging directory
2. Atomically swaps the staging tiles into the live directory
3. Signals Valhalla to reload — routing stays live throughout

A threading lock prevents concurrent rebuilds. If a rebuild is already running when a second operation is submitted, the API returns `409 Conflict`. The status indicator at the top of the admin page reflects this state in real time.