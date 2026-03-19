//install leaflet, react-leaflet, @types/leaflet.
//run npm install react react-dom leaflet react-leaflet

import { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { geocodeAddress, getDirections } from './services/api';
import MapClickHandler from './MapClickHandler';
import RouteMarkers from './RouteMarkers';
import RouteLayer from './RouteLayer';
import Sidebar from './Sidebar';
import Controlpanel from './Controlpanel';
import ElevationProfile from './ElevationProfile';
import 'leaflet/dist/leaflet.css';

// Placeholder step data (TODO: replace with real routing API results)
const PLACEHOLDER_STEPS = [
  { instruction: 'Head north on Forbes Ave toward Craig St', detail: '0.2 mi · 1 min' },
  { instruction: 'Turn right onto Craig St', detail: '0.1 mi · 1 min' },
  { instruction: 'Turn left onto Fifth Ave', detail: '1.3 mi · 4 min' },
  { instruction: 'Keep right to stay on Fifth Ave', detail: '0.6 mi · 2 min' },
  { instruction: 'Turn right onto Morewood Ave', detail: '0.3 mi · 1 min' },
  { instruction: 'Arrive at your destination on the right', detail: '—' },
];

interface Location {
  lat: number;
  lon: number;
}

// ─── Helpers: two-step elevation fetch via Vite proxy ────────────────────────
//
// Step 1: GET /api/route → get encoded polyline6 shape for the route
// Step 2: POST /api/height with the encoded shape + range:true → get
//         [{distance, height}] array from Valhalla's dedicated elevation service
//
// The public valhalla1.openstreetmap.de /route endpoint rejects unknown keys
// like `elevation_interval`, so we use the separate /height endpoint instead.

// Decode a Valhalla polyline6 string into [{lat, lon}] coordinate list.
// Valhalla uses precision=6 (multiply by 1e-6) and encodes lon before lat
// in some versions — but the standard is lat,lon. We decode as lat/lon here.
function decodePolyline6(encoded: string): { lat: number; lon: number }[] {
  const coords: { lat: number; lon: number }[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let b: number;
    let shift = 0;
    let result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += dlat;

    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += dlng;

    coords.push({ lat: lat * 1e-6, lon: lng * 1e-6 });
  }
  return coords;
}

// Normalized elevation data returned to the caller / stored in state.
export interface ElevationSample {
  distance: number;      // cumulative distance in miles
  elevation: number;     // absolute elevation in feet
  relativeElevation: number; // change from start in feet
}

async function fetchElevationData(
  start: Location,
  end: Location,
  signal: AbortSignal,
): Promise<ElevationSample[]> {
  // ── Step 1: route shape ────────────────────────────────────────────────────
  const routePayload = {
    locations: [
      { lat: start.lat, lon: start.lon },
      { lat: end.lat, lon: end.lon },
    ],
    costing: 'pedestrian',
  };

  const routeRes = await fetch('/api/route', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(routePayload),
    signal,
  });

  if (!routeRes.ok) {
    throw new Error(`Route fetch failed: ${routeRes.status} ${routeRes.statusText}`);
  }

  const routeData = await routeRes.json();
  const encodedShape: string | undefined = routeData?.trip?.legs?.[0]?.shape;

  if (!encodedShape) {
    throw new Error('No shape in route response');
  }

  // ── Step 2: elevation for each shape point ────────────────────────────────
  // Decode polyline6 → shape array, then ask /height with range:true
  const shapePoints = decodePolyline6(encodedShape);

  // Resample to at most 200 points to stay within service limits
  const MAX_POINTS = 200;
  let sampledPoints = shapePoints;
  if (shapePoints.length > MAX_POINTS) {
    const step = shapePoints.length / MAX_POINTS;
    sampledPoints = Array.from({ length: MAX_POINTS }, (_, i) =>
      shapePoints[Math.round(i * step)],
    );
    // Always include the last point
    sampledPoints[MAX_POINTS - 1] = shapePoints[shapePoints.length - 1];
  }

  const heightPayload = {
    shape: sampledPoints.map((p) => ({ lat: p.lat, lon: p.lon })),
    resample_distance: 30, // metres between resampled elevation points
    range: true,           // include cumulative distance in response
  };

  const heightRes = await fetch('/api/height', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(heightPayload),
    signal,
  });

  if (!heightRes.ok) {
    throw new Error(`Height fetch failed: ${heightRes.status} ${heightRes.statusText}`);
  }

  const heightData = await heightRes.json();
  // Response: { shape: [{lat, lon, height}], range_height: [[distance_m, height_m], ...] }
  const rangeHeight: [number, number][] | undefined = heightData?.range_height;

  if (!Array.isArray(rangeHeight) || rangeHeight.length === 0) {
    throw new Error('No range_height in height response');
  }

  const metersToFeet = 3.28084;
  const metersToMiles = 0.000621371;
  const startElevFt = rangeHeight[0][1] * metersToFeet;

  return rangeHeight.map(([distM, elevM]) => {
    const elevFt = elevM * metersToFeet;
    return {
      distance: distM * metersToMiles,
      elevation: Math.round(elevFt),
      relativeElevation: Math.round(elevFt - startElevFt),
    };
  });
}

export default function Map() {
  const [startPoint, setStartPoint] = useState<Location | null>(null);
  const [endPoint, setEndPoint] = useState<Location | null>(null);
  const [routePolyline, setRoutePolyline] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [steps, setSteps] = useState<typeof PLACEHOLDER_STEPS | null>(null);
  const [searched, setSearched] = useState(false);

  // Processed elevation samples for the chart (from /api/height via Vite proxy)
  const [elevationSamples, setElevationSamples] = useState<ElevationSample[] | null>(null);

  // AbortController ref so we can cancel stale elevation requests on clear / re-route
  const elevationAbortRef = useRef<AbortController | null>(null);

  // ─── Elevation fetch: triggered whenever both endpoints are resolved ─────────
  useEffect(() => {
    if (!startPoint || !endPoint) {
      setElevationSamples(null);
      return;
    }

    // Cancel any in-flight elevation request
    elevationAbortRef.current?.abort();
    const controller = new AbortController();
    elevationAbortRef.current = controller;

    fetchElevationData(startPoint, endPoint, controller.signal)
      .then((samples) => {
        console.log(
          `Elevation: ${samples.length} samples,`,
          `last distance ${samples[samples.length - 1]?.distance.toFixed(2)} mi`,
        );
        setElevationSamples(samples);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return; // intentional cancel — ignore
        console.error('Elevation fetch error:', err);
        // Non-fatal: route highlighting still works without elevation
        setElevationSamples(null);
      });

    return () => {
      controller.abort();
    };
  }, [startPoint, endPoint]);

  // ─── Geocode → route ─────────────────────────────────────────────────────────
  const handleSearch = async () => {
    if (!from.trim() || !to.trim()) return;
    setIsLoading(true);

    try {
      const fromResults = await geocodeAddress(from);
      const toResults = await geocodeAddress(to);

      if (fromResults.length && toResults.length) {
        const start = fromResults[0];
        const end = toResults[0];

        setStartPoint({ lat: start.lat, lon: start.lon });
        setEndPoint({ lat: end.lat, lon: end.lon });
        await fetchRoute({ lat: start.lat, lon: start.lon }, { lat: end.lat, lon: end.lon });
      }
    } catch (error) {
      setErrorMessage('Failed to geocode addresses');
    } finally {
      setIsLoading(false);
    }
  };

  // Automatically fetch route when both points are set via map clicks
  useEffect(() => {
    if (startPoint && endPoint) {
      fetchRoute(startPoint, endPoint);
    }
  }, [startPoint, endPoint]);

  const handleLocationSelect = (lat: number, lon: number) => {
    if (!startPoint) {
      setStartPoint({ lat, lon });
      setEndPoint(null);
      setRoutePolyline(null);
      setErrorMessage(null);
    } else if (!endPoint) {
      setEndPoint({ lat, lon });
    } else {
      // Third click: reset and start over
      setStartPoint({ lat, lon });
      setEndPoint(null);
      setRoutePolyline(null);
      setErrorMessage(null);
      setElevationSamples(null);
      elevationAbortRef.current?.abort();
    }
  };

  // ─── Route fetch (backend — getDirections) ───────────────────────────────────
  const fetchRoute = async (start: Location, end: Location) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const data = await getDirections({
        origin_lat: start.lat,
        origin_lon: start.lon,
        destination_lat: end.lat,
        destination_lon: end.lon,
        costing: 'pedestrian',
      });
      console.log('Full routing response:', JSON.stringify(data, null, 2));

      if (data.error_code) {
        if (data.error_code === 442) {
          setErrorMessage('No route found - these locations are not connected by sidewalks');
        } else if (data.error_code === 171) {
          setErrorMessage('No sidewalks found near one or both locations');
        } else {
          setErrorMessage(`Routing error: ${data.error}`);
        }
        setRoutePolyline(null);
        return;
      }

      const encodedShape = data.summary?.legs?.[0]?.shape;

      if (!encodedShape) {
        setErrorMessage('Invalid response from routing engine');
        return;
      }

      setRoutePolyline(encodedShape);
      setSearched(true);
    } catch (err) {
      console.error('routing error', err);
      setErrorMessage('Failed to get directions');
      setRoutePolyline(null);
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Clear everything, cancel stale elevation requests ───────────────────────
  const clearRoute = () => {
    elevationAbortRef.current?.abort();
    elevationAbortRef.current = null;

    setStartPoint(null);
    setEndPoint(null);
    setRoutePolyline(null);
    setErrorMessage(null);
    setSteps(null);
    setSearched(false);
    setFrom('');
    setTo('');
    setElevationSamples(null);
  };

  const sharedProps = { startPoint, endPoint, isLoading, errorMessage, routePolyline, clearRoute };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>

      {/* Sidebar — sits on the left */}
      <Sidebar
        {...sharedProps}
        from={from}
        to={to}
        setFrom={setFrom}
        setTo={setTo}
        handleSearch={handleSearch}
        steps={steps}
        searched={searched}
      />

      {/* Right side — control panel on top, map + elevation below */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Controlpanel {...sharedProps} />

        {/* Map fills remaining vertical space */}
        <MapContainer
          center={[40.4421676, -79.9959]}
          zoom={13}
          scrollWheelZoom={true}
          style={{ flex: 1, width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onLocationSelect={handleLocationSelect} />
          <RouteMarkers startPoint={startPoint} endPoint={endPoint} />
          <RouteLayer encodedPolyline={routePolyline} />
        </MapContainer>

        {/* Elevation profile — only rendered when elevation data is available */}
        <ElevationProfile elevationSamples={elevationSamples} />
      </div>

    </div>
  );
}