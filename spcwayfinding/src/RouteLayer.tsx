import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import polyline from '@mapbox/polyline';

interface RouteLayerProps {
  encodedPolyline: string | null;
  color?: string;
  weight?: number;
}

// Store layer reference outside component to avoid cleanup timing issues
let currentRouteLine: L.Polyline | null = null;

export default function RouteLayer({ 
  encodedPolyline, 
  color = '#2196F3', 
  weight = 5 
}: RouteLayerProps) {
  const map = useMap();

  useEffect(() => {
    // Clear any existing route immediately
    if (currentRouteLine) {
      try {
        map.removeLayer(currentRouteLine);
      } catch (e) {
        // Layer might already be removed, ignore error
      }
      currentRouteLine = null;
    }

    // If no polyline provided, we're done (route was cleared)
    if (!encodedPolyline) {
      return;
    }

    // Small delay to ensure cleanup completes
    const timer = setTimeout(() => {
      map.invalidateSize();
      
      const coordinates = polyline.decode(encodedPolyline, 6);
      
      currentRouteLine = L.polyline(coordinates, {
        color,
        weight,
        opacity: 0.8,
        lineJoin: 'round',
        lineCap: 'round',
      }).addTo(map);

      map.fitBounds(currentRouteLine.getBounds(), { padding: [50, 50] });
    }, 100);

    // Cleanup function
    return () => {
      clearTimeout(timer);
      // Note: We don't remove the layer here because it causes timing issues
      // The layer is removed at the start of the next effect instead
    };
  }, [map, encodedPolyline, color, weight]);

  return null;
}
