import { useMapEvents } from 'react-leaflet';

interface MapClickHandlerProps {
  onLocationSelect: (lat: number, lon: number) => void;
}

export default function MapClickHandler({ onLocationSelect }: MapClickHandlerProps) {
  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    }
  });

  return null;
}