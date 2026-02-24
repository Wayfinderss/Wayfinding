import { useState, useEffect } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import MapClickHandler from './MapClickHandler';
import RouteMarkers from './RouteMarkers';
import RouteLayer from './RouteLayer';
import 'leaflet/dist/leaflet.css';

interface Location {
  lat: number;
  lon: number;
}

export default function Map() {
  const [startPoint, setStartPoint] = useState<Location | null>(null);
  const [endPoint, setEndPoint] = useState<Location | null>(null);
  const [routePolyline, setRoutePolyline] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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
          directions_options: { units: 'miles' }
        })
      });

      const data = await response.json();
      
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
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Control Panel */}
      <div style={{ 
        padding: '15px', 
        backgroundColor: '#f5f5f5',
        borderBottom: '2px solid #ddd',
        display: 'flex',
        gap: '15px',
        alignItems: 'center',
        flexWrap: 'wrap'
      }}>
        {/* Instructions */}
        <div style={{ flex: 1, minWidth: '200px' }}>
          <strong>Instructions:</strong>
          {!startPoint && ' Click on the map to set start point (green marker)'}
          {startPoint && !endPoint && ' Click again to set end point (red marker)'}
          {startPoint && endPoint && ' Route displayed! Click to reset.'}
        </div>

        {/* Clear button */}
        {(startPoint || endPoint) && (
          <button 
            onClick={clearRoute}
            style={{ 
              padding: '10px 20px', 
              cursor: 'pointer',
              backgroundColor: '#f44336',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontWeight: 'bold'
            }}
          >
            Clear Route
          </button>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div style={{ 
            padding: '10px', 
            backgroundColor: '#fff3e0', 
            color: '#e65100',
            borderRadius: '4px',
            fontWeight: 'bold'
          }}>
            🔄 Finding route...
          </div>
        )}

        {/* Error message */}
        {errorMessage && (
          <div style={{ 
            padding: '10px', 
            backgroundColor: '#ffebee', 
            color: '#c62828',
            borderRadius: '4px',
            border: '1px solid #ef5350',
            flex: 1,
            minWidth: '300px'
          }}>
            ⚠️ {errorMessage}
          </div>
        )}

        {/* Success message */}
        {routePolyline && !errorMessage && (
          <div style={{ 
            padding: '10px', 
            backgroundColor: '#e8f5e9', 
            color: '#2e7d32',
            borderRadius: '4px',
            fontWeight: 'bold'
          }}>
            ✓ Route found!
          </div>
        )}
      </div>
      
      {/* Map */}
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
        
        {/* Click handler */}
        <MapClickHandler onLocationSelect={handleLocationSelect} />
        
        {/* Start/End markers */}
        <RouteMarkers startPoint={startPoint} endPoint={endPoint} />
        
        {/* Route line */}
        <RouteLayer encodedPolyline={routePolyline} />
      </MapContainer>
    </div>
  );
}