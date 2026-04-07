//install leaflet, react-leaflet, @types/leaflet.
//run npm install react react-dom leaflet react-leaflet

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

// Placeholder step data
const PLACEHOLDER_STEPS = [
  { instruction: 'Head north on Forbes Ave toward Craig St', detail: '0.2 mi · 1 min' },
  { instruction: 'Turn right onto Craig St', detail: '0.1 mi · 1 min' },
  { instruction: 'Turn left onto Fifth Ave', detail: '1.3 mi · 4 min' },
  { instruction: 'Keep right to stay on Fifth Ave', detail: '0.6 mi · 2 min' },
  { instruction: 'Turn right onto Morewood Ave', detail: '0.3 mi · 1 min' },
  { instruction: 'Arrive at your destination on the right', detail: '—' },
];

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
  const [steps, setSteps] = useState<typeof PLACEHOLDER_STEPS | null>(null);
  const [searched, setSearched] = useState(false);

  const [activeBasemap, setTileKey] = useState(0);
  const [showElevation, setShowElevation] = useState(false);

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
        { lat: end.lat, lon: end.lon }
      );
    } else {
      setErrorMessage('No matching addresses found');
    }
  } catch (error) {
    setErrorMessage('Failed to geocode addresses');
  } finally {
    setIsLoading(false);
  }
};

  useEffect(() => {
    if (startPoint && endPoint) {
      fetchRoute(startPoint, endPoint);
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
      // First click sets start point
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

  const fetchRoute = async (start: Location, end: Location) => {
    setIsLoading(true);
    setErrorMessage(null);

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

      let data: ValhallaRouteResponse;

      try {
        data = JSON.parse(rawText) as ValhallaRouteResponse;
      } catch {
        setErrorMessage('Routing service returned invalid JSON');
        setRoutePolyline(null);
        return;
      }

      setFullRouteData(data);

      if (!response.ok || data.status !== 'ok') {
        setErrorMessage('Routing error');
        setRoutePolyline(null);
        return;
      }

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
          detail: m.length && m.length > 0
            ? `${distance} mi · ${minutes} min`
            : '—'
        };
      });

      setSteps(parsedSteps);
      setSearched(true);

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

        <ElevationProfile routeData={fullRouteData} />
      </div>
    </div>
  );
}