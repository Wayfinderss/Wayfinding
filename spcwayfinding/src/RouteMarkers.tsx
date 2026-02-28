import { Marker } from 'react-leaflet';
import L from 'leaflet';

interface Location {
  lat: number;
  lon: number;
}

interface RouteMarkersProps {
  startPoint: Location | null;
  endPoint: Location | null;
}

// Custom marker icons
const startIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const endIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

export default function RouteMarkers({ startPoint, endPoint }: RouteMarkersProps) {
  return (
    <>
      {startPoint && (
        <Marker position={[startPoint.lat, startPoint.lon]} icon={startIcon} />
      )}
      {endPoint && (
        <Marker position={[endPoint.lat, endPoint.lon]} icon={endIcon} />
      )}
    </>
  );
}