import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import { geocodeAddress, reverseGeocode } from './services/api';
import MapClickHandler from './MapClickHandler';
import RouteMarkers from './RouteMarkers';
import RouteLayer from './RouteLayer';
import Sidebar from './Left-Sidebar';
import RightSidebar from './Right-Sidebar';
import Controlpanel from './Controlpanel';
import ElevationProfile from './ElevationProfile';
import ElevationMarker from './ElevationMarker';
import 'leaflet/dist/leaflet.css';

function InvalidateSize({ trigger }: { trigger: any }) {
  const map = useMap();
  useEffect(() => {
    setTimeout(() => map.invalidateSize(), 300);
  }, [trigger]);
  return null;
}

interface Location {
  lat: number;
  lon: number;
}

interface ValhallaLocation {
  type?: 'break';
  lat: number;
  lon: number;
  original_index?: number;
}

interface ValhallaManeuver {
  type: number;
  instruction: string;
  time?: number;
  length?: number;
}

interface ValhallaLeg {
  shape: string;
  maneuvers: ValhallaManeuver[];
  summary?: {
    length?: number;
    time?: number;
  };
  elevation?: number[];
  elevation_interval?: number;
}

interface ValhallaTrip {
  locations?: ValhallaLocation[];
  legs: ValhallaLeg[];
}

interface ValhallaSuccessResponse {
  status: 'ok';
  trip: ValhallaTrip;
}

interface ValhallaErrorResponse {
  status: 'no_route';
  error_code: number;
  error_message: string;
}

type ValhallaRouteResponse = ValhallaSuccessResponse | ValhallaErrorResponse;

export default function Map() {
  const [startPoint, setStartPoint] = useState<Location | null>(null);
  const [endPoint, setEndPoint] = useState<Location | null>(null);
  const [routePolyline, setRoutePolyline] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [fullRouteData, setFullRouteData] = useState<any | null>(null);

  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [steps, setSteps] = useState<{ instruction: string; detail: string }[] | null>(null);
  const [searched, setSearched] = useState(false);
  const [routeSummary, setRouteSummary] = useState<{ totalDistanceMi: number; totalTimeMin: number } | null>(null);

  const [activeBasemap, setTileKey] = useState(0);
  const [showElevation, setShowElevation] = useState(true);
  const [avoidStaircases, setAvoidStaircases] = useState(false);
  const [incline, setIncline] = useState<number | null>(null);

  // Incremented every time the user presses Apply in RightSidebar.
  // Including this in the reroute effect guarantees a fresh route request
  // even when incline/avoidStaircases values haven't changed — which is
  // exactly the case when recovering from a routing error back to a value
  // that previously worked.

  const handleApplySettings = (newAvoidStaircases: boolean, newIncline: number | null) => {
    setAvoidStaircases(newAvoidStaircases);
    setIncline(newIncline);
    if (startPoint && endPoint) {
      fetchRoute(startPoint, endPoint, newAvoidStaircases, newIncline);
    }
  };

  const [hoveredFraction, setHoveredFraction] = useState<number | null>(null);

  const handleSearch = async () => {
    if (!from.trim() || !to.trim()) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const fromResults = await geocodeAddress(from);
      const toResults = await geocodeAddress(to);

      if (fromResults.length && toResults.length) {
        const start = fromResults[0];
        const end = toResults[0];

        setStartPoint({ lat: start.lat, lon: start.lon });
        setEndPoint({ lat: end.lat, lon: end.lon });

        await fetchRoute(
          { lat: start.lat, lon: start.lon },
          { lat: end.lat, lon: end.lon },
          avoidStaircases,
          incline
        );
      } else {
        setErrorMessage('No matching addresses found');
      }
    } catch (error) {
      console.error('Geocoding error:', error);
      setErrorMessage('Failed to geocode addresses');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (startPoint && endPoint) {
      fetchRoute(startPoint, endPoint, avoidStaircases, incline);
    }
  }, [startPoint, endPoint]);

  const handleLocationSelect = async (lat: number, lon: number) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const result = await reverseGeocode(lat, lon);
      const label =
        result?.address ??
        result?.label ??
        `${lat.toFixed(6)}, ${lon.toFixed(6)}`;

      if (!startPoint) {
        setStartPoint({ lat, lon });
        setFrom(label);
        setEndPoint(null);
        setTo('');
        setRoutePolyline(null);
        setSearched(false);
        setSteps(null);
      } else if (!endPoint) {
        setEndPoint({ lat, lon });
        setTo(label);
      } else {
        setStartPoint({ lat, lon });
        setFrom(label);
        setEndPoint(null);
        setTo('');
        setRoutePolyline(null);
        setErrorMessage(null);
        setSearched(false);
        setSteps(null);
      }
    } catch (error) {
      console.error('Reverse geocoding failed:', error);
      setErrorMessage('Failed to get address from map click');
    } finally {
      setIsLoading(false);
    }
  };

  // Decode a Valhalla-encoded polyline (precision 6) into [lat, lon] pairs
  const decodePolyline = (encoded: string): [number, number][] => {
    const coords: [number, number][] = [];
    let index = 0, lat = 0, lon = 0;
    while (index < encoded.length) {
      let b, shift = 0, result = 0;
      do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      lat += (result & 1) ? ~(result >> 1) : result >> 1;
      shift = 0; result = 0;
      do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      lon += (result & 1) ? ~(result >> 1) : result >> 1;
      coords.push([lat / 1e6, lon / 1e6]);
    }
    return coords;
  };

  // Extract INTERIOR coordinates of stair maneuvers to use as exclude_locations.
  // We must NOT use the entry/exit nodes — those are shared with adjacent edges
  // and may coincide with the route start/end, causing Valhalla error 442.
  // Interior points belong only to the stair edge, so excluding them blocks
  // only that edge without affecting any other part of the graph.
  const extractStairLocations = (data: ValhallaSuccessResponse): { lat: number; lon: number }[] => {
    const leg = data.trip?.legs?.[0];
    if (!leg) return [];
    const coords = decodePolyline(leg.shape);
    const excludes: { lat: number; lon: number }[] = [];
    for (const maneuver of leg.maneuvers) {
      if ((maneuver as any).type === 40) {
        const begin: number = (maneuver as any).begin_shape_index;
        const end: number   = (maneuver as any).end_shape_index;
        const interior: number[] = [];
        for (let i = begin + 1; i < end; i++) interior.push(i);
        if (interior.length > 0) {
          const mid = coords[interior[Math.floor(interior.length / 2)]];
          if (mid) excludes.push({ lat: mid[0], lon: mid[1] });
        } else {
          const a = coords[begin];
          const b = coords[end];
          if (a && b) {
            excludes.push({ lat: (a[0] + b[0]) / 2, lon: (a[1] + b[1]) / 2 });
          }
        }
      }
    }
    return excludes;
  };

  const callValhalla = async (
    start: Location,
    end: Location,
    inclineValue: number | null,
    excludeLocations?: { lat: number; lon: number }[]
  ): Promise<{ response: Response; data: ValhallaRouteResponse }> => {
    const body: any = {
      locations: [
        { lat: start.lat, lon: start.lon },
        { lat: end.lat, lon: end.lon }
      ],
      costing: 'pedestrian',
      directions_options: { units: 'miles' },
      elevation_interval: 10,
      user_id: null,
    };
    if (inclineValue !== null && inclineValue > 0) {
      body.costing_options = { pedestrian: { incline: inclineValue } };
    }
    if (excludeLocations && excludeLocations.length > 0) {
      body.exclude_locations = excludeLocations;
    }
    const response = await fetch('/valhalla/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const rawText = await response.text();
    let data: ValhallaRouteResponse;
    try {
      data = JSON.parse(rawText) as ValhallaRouteResponse;
    } catch {
      throw new Error('Routing service returned invalid JSON');
    }
    return { response, data };
  };

  const applyRouteData = (data: ValhallaSuccessResponse) => {
    setFullRouteData(data);
    const encodedShape = data.trip?.legs?.[0]?.shape;
    if (!encodedShape) {
      setErrorMessage('Invalid response from routing engine');
      return;
    }
    setRoutePolyline(encodedShape);
    const maneuvers = data.trip?.legs?.[0]?.maneuvers ?? [];
    const parsedSteps = maneuvers.map((m) => {
      const distance = m.length ? m.length.toFixed(2) : '0';
      const minutes = m.time ? Math.round(m.time / 60) : 0;
      return {
        instruction: m.instruction,
        detail: m.length && m.length > 0 ? `${distance} mi · ${minutes} min` : '—',
      };
    });
    setSteps(parsedSteps);
    const leg = data.trip?.legs?.[0];
    const totalDistanceMi = leg?.summary?.length ?? maneuvers.reduce((sum, m) => sum + (m.length ?? 0), 0);
    const totalTimeSec = leg?.summary?.time ?? maneuvers.reduce((sum, m) => sum + (m.time ?? 0), 0);
    setRouteSummary({ totalDistanceMi, totalTimeMin: Math.round(totalTimeSec / 60) });
    setSearched(true);
  };

  const fetchRoute = async (
    start: Location,
    end: Location,
    avoidStairs: boolean = false,
    inclineValue: number | null = null
  ) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // Pass 1: get the baseline route
      const { response: resp1, data: data1 } = await callValhalla(start, end, inclineValue);

      if (!resp1.ok || data1.status !== 'ok') {
        setErrorMessage('Routing error');
        setRoutePolyline(null);
        return;
      }

      if (!avoidStairs) {
        applyRouteData(data1 as ValhallaSuccessResponse);
        return;
      }

      // Pass 2: check if this route uses stairs
      const stairLocations = extractStairLocations(data1 as ValhallaSuccessResponse);
      console.log('[avoidStairs] Pass 1 stair locations found:', stairLocations);

      if (stairLocations.length === 0) {
        console.log('[avoidStairs] No stairs in route, using as-is');
        applyRouteData(data1 as ValhallaSuccessResponse);
        return;
      }

      // Pass 3: retry with stair nodes excluded
      console.log('[avoidStairs] Retrying with exclude_locations:', stairLocations);
      const { response: resp2, data: data2 } = await callValhalla(start, end, inclineValue, stairLocations);
      console.log('[avoidStairs] Pass 2 response status:', resp2.status, 'data.status:', data2.status);

      if (!resp2.ok || data2.status !== 'ok') {
        console.log('[avoidStairs] Pass 2 failed - no stair-free route');
        setErrorMessage('No staircase-free route found between these points. Try a different destination, or disable "Avoid Staircases".');
        setRoutePolyline(null);
        setSteps(null);
        return;
      }

      const retryStairs = extractStairLocations(data2 as ValhallaSuccessResponse);
      console.log('[avoidStairs] Pass 2 still has stairs:', retryStairs);
      if (retryStairs.length > 0) {
        console.log('[avoidStairs] Pass 2 route still uses stairs - giving up');
        setErrorMessage('No staircase-free route found between these points. Try a different destination, or disable "Avoid Staircases".');
        setRoutePolyline(null);
        setSteps(null);
        return;
      }

      console.log('[avoidStairs] Pass 2 success - stair-free route found');
      applyRouteData(data2 as ValhallaSuccessResponse);

    } catch (error) {
      console.error(error);
      setErrorMessage('Failed to connect to routing service');
    } finally {
      setIsLoading(false);
    }
  };

  const clearRoute = () => {
    setStartPoint(null);
    setEndPoint(null);
    setRoutePolyline(null);
    setErrorMessage(null);
    setSteps(null);
    setSearched(false);
    setFrom('');
    setTo('');
    setFullRouteData(null);
    setRouteSummary(null);
  };

  const sharedProps = {
    startPoint,
    endPoint,
    isLoading,
    errorMessage,
    routePolyline,
    clearRoute
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
      <Sidebar
        {...sharedProps}
        from={from}
        to={to}
        setFrom={setFrom}
        setTo={setTo}
        handleSearch={handleSearch}
        steps={steps}
        searched={searched}
        routeSummary={routeSummary}
      />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Controlpanel {...sharedProps} />

        <MapContainer
          center={[40.4421676, -79.9959]}
          zoom={13}
          scrollWheelZoom={true}
          style={{ flex: 1, width: '100%' }}
        >
          <InvalidateSize trigger={[showElevation, routePolyline]} />
          <TileLayer
            key={activeBasemap}
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapClickHandler onLocationSelect={handleLocationSelect} />
          <RouteMarkers startPoint={startPoint} endPoint={endPoint} />
          <RouteLayer encodedPolyline={routePolyline} />
          <ElevationMarker encodedPolyline={routePolyline} fraction={hoveredFraction} />
        </MapContainer>

        {showElevation && 
        <ElevationProfile
        routeData={fullRouteData}
        onHover={setHoveredFraction}
       />}

      </div>

      <RightSidebar
        onResetBasemap={() => setTileKey(k => k + 1)}
        showElevation={showElevation}
        onToggleElevation={setShowElevation}
        avoidStaircases={avoidStaircases}
        incline={incline}
        onApply={handleApplySettings}
      />
    </div>
  );
}