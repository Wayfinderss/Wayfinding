//install leaflet, react-leaflet, @types/leaflet.
//run npm install react react-dom leaflet react-leaflet

import { useState, useEffect } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
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

interface ValhallaLocation {
  type?: 'break';
  lat: number;
  lon: number;
  original_index?: number;
}

interface ValhallaManeuver {
  type: number;
  instruction: string;
  verbal_succinct_transition_instruction?: string;
  verbal_pre_transition_instruction?: string;
  verbal_post_transition_instruction?: string;
  street_names?: string[];
  bearing_before?: number;
  bearing_after?: number;
  time?: number;
  length?: number;
  cost?: number;
  begin_shape_index?: number;
  end_shape_index?: number;
  rough?: boolean;
  travel_mode?: string;
  travel_type?: string;
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
  summary?: {
    length?: number;
    time?: number;
  };
}

interface ValhallaSuccessResponse {
  status: 'ok';
  trip: ValhallaTrip;
}

interface ValhallaErrorResponse {
  status: 'no_route';
  error_code: number;
  error_message: string;
  failure_reason?: string;
  logged_attempt_id?: number | null;
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
  const [steps, setSteps] = useState<typeof PLACEHOLDER_STEPS | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = () => {
    if (!from.trim() || !to.trim()) return;
    setSteps(PLACEHOLDER_STEPS);
    setSearched(true);
  };

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
      setStartPoint({ lat, lon });
      setEndPoint(null);
      setRoutePolyline(null);
      setErrorMessage(null);
    }
  };

  const fetchRoute = async (start: Location, end: Location) => {
    setIsLoading(true);
    setErrorMessage(null);

    console.log('Fetching route from', start, 'to', end);

    try {
      const response = await fetch('/valhalla/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locations: [
            { lat: start.lat, lon: start.lon },
            { lat: end.lat, lon: end.lon }
          ],
          costing: 'pedestrian',
          directions_options: { units: 'miles' },
          elevation_interval: 10,
          user_id: null
        })
      });

      const rawText = await response.text();
      console.log('Raw response:', rawText);

      let data: ValhallaRouteResponse;
      try {
        data = JSON.parse(rawText) as ValhallaRouteResponse;
      } catch (parseError) {
        console.error('Failed to parse response as JSON:', parseError);
        console.log('RAW RESPONSE:', rawText);
        setErrorMessage('Routing service returned invalid JSON');
        setRoutePolyline(null);
        return;
      }

      setFullRouteData(data);

      if (!response.ok || data.status !== 'ok') {
        if ('error_code' in data) {
          if (data.error_code === 442) {
            setErrorMessage('No route found - these locations are not connected by sidewalks');
          } else if (data.error_code === 171) {
            setErrorMessage('No sidewalks found near one or both locations');
          } else {
            setErrorMessage(data.error_message || 'Routing error');
          }
        } else {
          setErrorMessage(`Routing error: HTTP ${response.status}`);
        }
        setRoutePolyline(null);
        return;
      }

      const encodedShape = data.trip?.legs?.[0]?.shape;

      if (typeof encodedShape !== 'string' || encodedShape.length === 0) {
        setErrorMessage('Invalid response from routing engine');
        setRoutePolyline(null);
        return;
      }

      setRoutePolyline(encodedShape);
    } catch (error) {
      console.error('Error fetching route:', error);
      setErrorMessage('Failed to connect to routing service');
      setRoutePolyline(null);
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

  const sharedProps = { startPoint, endPoint, isLoading, errorMessage, routePolyline, clearRoute };

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
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onLocationSelect={handleLocationSelect} />
          <RouteMarkers startPoint={startPoint} endPoint={endPoint} />
          <RouteLayer encodedPolyline={routePolyline} />
        </MapContainer>

        <ElevationProfile routeData={fullRouteData} />
      </div>
    </div>
  );
}