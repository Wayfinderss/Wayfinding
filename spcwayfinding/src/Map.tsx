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

  const [activeBasemap, setTileKey] = useState(0);
  const [showElevation, setShowElevation] = useState(false);
  const [avoidStaircases, setAvoidStaircases] = useState(false);

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
          avoidStaircases
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
      fetchRoute(startPoint, endPoint, avoidStaircases);
    }
  }, [startPoint, endPoint]);

  useEffect(() => {
    if (startPoint && endPoint && routePolyline) {
      fetchRoute(startPoint, endPoint, avoidStaircases)
    }
  }, [avoidStaircases]);


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

  // Extract entry/exit coordinates of all stair maneuvers (type 40) from a route.
  const extractStairLocations = (data: ValhallaSuccessResponse): { lat: number; lon: number }[] => {
    const leg = data.trip?.legs?.[0];
    if (!leg) return [];
    const coords = decodePolyline(leg.shape);
    const excludes: { lat: number; lon: number }[] = [];
    for (const maneuver of leg.maneuvers) {
      if ((maneuver as any).type === 40) {
        const entry = coords[(maneuver as any).begin_shape_index];
        const exit  = coords[(maneuver as any).end_shape_index];
        if (entry) excludes.push({ lat: entry[0], lon: entry[1] });
        if (exit)  excludes.push({ lat: exit[0],  lon: exit[1]  });
      }
    }
    return excludes;
  };

  const callValhalla = async (
    start: Location,
    end: Location,
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
    setSearched(true);
  };

  const fetchRoute = async (start: Location, end: Location, avoidStairs: boolean = false) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // Pass 1: get the baseline route
      const { response: resp1, data: data1 } = await callValhalla(start, end);

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

      if (stairLocations.length === 0) {
        // No stairs in the route — use it as-is
        applyRouteData(data1 as ValhallaSuccessResponse);
        return;
      }

      // Pass 3: retry with stair nodes excluded
      const { response: resp2, data: data2 } = await callValhalla(start, end, stairLocations);

      if (!resp2.ok || data2.status !== 'ok') {
        setErrorMessage('No staircase-free route found between these points. Try a different destination, or disable "Avoid Staircases".');
        // Leave existing polyline visible
        return;
      }

      // Check if the retry still contains stairs
      const retryStairs = extractStairLocations(data2 as ValhallaSuccessResponse);
      if (retryStairs.length > 0) {
        setErrorMessage('No staircase-free route found between these points. Try a different destination, or disable "Avoid Staircases".');
        return;
      }

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
        </MapContainer>

        {showElevation && <ElevationProfile routeData={fullRouteData} />}
      </div>

      <RightSidebar
        onResetBasemap={() => setTileKey(k => k + 1)}
        showElevation={showElevation}
        onToggleElevation={setShowElevation}
        avoidStaircases={avoidStaircases}
        onToggleStaircases={setAvoidStaircases}
      />
    </div>
  );
}