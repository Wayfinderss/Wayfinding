import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import polyline from '@mapbox/polyline';

interface ElevationMarkerProps {
  encodedPolyline: string | null;
  fraction: number | null;
}

export default function ElevationMarker({ encodedPolyline, fraction }: ElevationMarkerProps) {
  const map = useMap();
  const markerRef = useRef<L.CircleMarker | null>(null);
  const coordsRef = useRef<[number, number][]>([]);

  useEffect(() => {
    if (!encodedPolyline) {
      coordsRef.current = [];
      return;
    }
    coordsRef.current = polyline.decode(encodedPolyline, 6);
  }, [encodedPolyline]);

  useEffect(() => {
    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    if (fraction === null || coordsRef.current.length === 0) return;

    const latlng = interpolateRoute(coordsRef.current, fraction);

    markerRef.current = L.circleMarker(latlng, {
      radius: 8,
      color: '#ffffff',
      weight: 3,
      fillColor: '#2196F3',
      fillOpacity: 1,
      IndexOffset: 1000,
    }).addTo(map);

  }, [map, fraction]);

  useEffect(() => {
    return () => { markerRef.current?.remove(); };
  }, []);

  return null;
}

function interpolateRoute(coords: [number, number][], fraction: number): L.LatLngExpression {
  if (coords.length === 1) return coords[0];
  fraction = Math.max(0, Math.min(1, fraction));

  const dists: number[] = [0];
  for (let i = 1; i < coords.length; i++) {
    dists.push(dists[i - 1] + L.latLng(coords[i - 1]).distanceTo(L.latLng(coords[i])));
  }

  const target = fraction * dists[dists.length - 1];

  for (let i = 1; i < dists.length; i++) {
    if (dists[i] >= target) {
      const t = (target - dists[i - 1]) / (dists[i] - dists[i - 1]);
      const [lat1, lng1] = coords[i - 1];
      const [lat2, lng2] = coords[i];
      return [lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t];
    }
  }

  return coords[coords.length - 1];
}