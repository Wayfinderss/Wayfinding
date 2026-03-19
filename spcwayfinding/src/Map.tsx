//install leaflet, react-leaflet, @types/leaflet.
//run npm install react react-dom leaflet react-leaflet

import { useState, useEffect } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { geocodeAddress, getDirections, reverseGeocode } from './services/api';
import MapClickHandler from './MapClickHandler';
import RouteMarkers from './RouteMarkers';
import RouteLayer from './RouteLayer';
import Sidebar from './Sidebar';
import Controlpanel from './Controlpanel';
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
  label?: string;
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

  // Automatically fetch route when both points are set
  useEffect(() => {
    if (startPoint && endPoint) {
      fetchRoute(startPoint, endPoint);
    }
  }, [startPoint, endPoint]);

  const handleLocationSelect = async (lat: number, lon: number) => {
  console.log('handleLocationSelect fired', lat, lon);
  alert(`clicked ${lat}, ${lon}`);
  setIsLoading(true);
  setErrorMessage(null);

  try {
    const result = await reverseGeocode(lat, lon,);
      console.log('reverse geocode result:', result);
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
      console.log('reverse geocode result:', result);
      console.log('label being used:', label);
    } else if (!endPoint) {
      // Second click sets end point
      setEndPoint({ lat, lon });
      setTo(label);
      console.log('reverse geocode result:', result);
      console.log('label being used:', label);
    } else {
      // Third click resets and starts over
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

    const encodedShape = data.summary?.legs?.[0]?.shape;  // ← correct path

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

  const clearRoute = () => {
    setStartPoint(null);
    setEndPoint(null);
    setRoutePolyline(null);
    setErrorMessage(null);
    setSteps(null);
    setSearched(false);
    setFrom('');
    setTo('');
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

      {/* Right side — control panel on top, map below */}
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
      </div>

    </div>

  );
}
