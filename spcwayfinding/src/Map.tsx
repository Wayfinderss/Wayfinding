//install leaflet, react-leaflet, @types/leaflet.
//run npm install react react-dom leaflet react-leaflet

import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import MapClickHandler from './MapClickHandler';
import RouteMarkers from './RouteMarkers';
import RouteLayer from './RouteLayer';
import Sidebar from './Left-Sidebar';
import RightSidebar from './Right-Sidebar';
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

function InvalidateSize({ trigger }: { trigger: any }) {
  const map = useMap();
  useEffect(() => {
    setTimeout(() => map.invalidateSize(), 300);
  }, [trigger]);
  return null;
}

export default function Map() {
  const [startPoint, setStartPoint] = useState<Location | null>(null);
  const [endPoint, setEndPoint] = useState<Location | null>(null);
  const [routePolyline, setRoutePolyline] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [fullRouteData, setFullRouteData] = useState<any | null>(null); // NEW: Store full Valhalla response

  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [steps, setSteps] = useState<typeof PLACEHOLDER_STEPS | null>(null);
  const [searched, setSearched] = useState(false);

  const [activeBasemap, setTileKey] = useState(0); //forces a reset when basemap icon is clicked 
  const [showElevation, setShowElevation] = useState(false); //for elevation toggle 

  const handleSearch = () => {
    if (!from.trim() || !to.trim()) return;
    // TODO: geocode from/to strings and call fetchRoute with real coordinates
    setSteps(PLACEHOLDER_STEPS);
    setSearched(true);
  };

  // Automatically fetch route when both points are set
  useEffect(() => {
    if (startPoint && endPoint) {
      fetchRoute(startPoint, endPoint);
    }
  }, [startPoint, endPoint]);

  const handleLocationSelect = (lat: number, lon: number) => {
    if (!startPoint) {
      // First click sets start point
      setStartPoint({ lat, lon });
      setEndPoint(null);
      setRoutePolyline(null);
      setErrorMessage(null);
    } else if (!endPoint) {
      // Second click sets end point
      setEndPoint({ lat, lon });
    } else {
      // Third click resets and starts over
      setStartPoint({ lat, lon });
      setEndPoint(null);
      setRoutePolyline(null);
      setErrorMessage(null);
    }
  };

  const fetchRoute = async (start: Location, end: Location) => {
    setIsLoading(true);
    setErrorMessage(null);
    
    try {
      const response = await fetch('/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locations: [
            { lat: start.lat, lon: start.lon },
            { lat: end.lat, lon: end.lon }
          ],
          costing: 'pedestrian',
          directions_options: { units: 'miles' },
          shape_format: 'geojson',  // Request GeoJSON format with elevation
          elevation_interval: 10     // Elevation point every 10 meters
        })
      });

      const data = await response.json();

      // DEBUG: Log the full response to see what we got
      console.log('Full Valhalla response:', data);
      console.log('Shape type:', typeof data.trip?.legs?.[0]?.shape);
      console.log('Shape value:', data.trip?.legs?.[0]?.shape);

      // NEW: Store full response for elevation profile
      setFullRouteData(data);
      
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
      
      const encodedShape = data.trip?.legs?.[0]?.shape;
      
      if (!encodedShape) {
        setErrorMessage('Invalid response from routing engine');
        return;
      }
      
      setRoutePolyline(encodedShape);
      
    } catch (error) {
      console.error('Error fetching route:', error);
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
    setFullRouteData(null); // NEW: Clear elevation data
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

      {/* Right side — control panel on top, map in middle, elevation profile at bottom */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Controlpanel {...sharedProps} />

        <MapContainer
          center={[40.4421676, -79.9959]}
          zoom={13}
          scrollWheelZoom={true}
          style={{ flex: 1, width: '100%' }}
        >
          <InvalidateSize trigger={[showElevation, routePolyline]} /> {/* fixes delay in map reload */}
          <TileLayer
            key={activeBasemap}
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onLocationSelect={handleLocationSelect} />
          <RouteMarkers startPoint={startPoint} endPoint={endPoint} />
          <RouteLayer encodedPolyline={routePolyline} />
        </MapContainer>

        {/* NEW: Elevation Profile */}
        {/* <ElevationProfile routeData={fullRouteData} /> */}
        {showElevation && <ElevationProfile routeData={fullRouteData} />}
      </div>

      {/* Right side bar three icons (outside map column) */}
      <RightSidebar 
        onResetBasemap={() => setTileKey(k => k + 1)}
        showElevation={showElevation}
        onToggleElevation={setShowElevation}
      />

     
     </div>

  );
}