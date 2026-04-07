export interface GeocodeResult {
  label: string;
  address: string;
  lat: number;
  lon: number;
}

export interface DirectionsRequest {
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
  costing?: string;
}
export interface ReverseGeocodeResult {
  label: string;
  address: string;
  lat: number;
  lon: number;
}
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function geocodeAddress(query: string): Promise<GeocodeResult[]> {
  const res = await fetch(`${API_BASE}/geocode/autocomplete?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error("Geocoding failed");
  const data = await res.json();
  return data.results ?? [];
}

export async function reverseGeocode(lat: number, lon: number): Promise<ReverseGeocodeResult | null> {
  const res = await fetch(
    `${API_BASE}/geocode/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`
  );
  if (!res.ok) throw new Error('Reverse geocoding failed');

  const data = await res.json();
  if (!data) return null;

  return {
    label: data.label || data.address || `${lat}, ${lon}`,
    address: data.address || data.label || `${lat}, ${lon}`,
    lat: data.lat ?? lat,
    lon: data.lon ?? lon,
  };
}

export async function getDirections(request: DirectionsRequest) {
  const res = await fetch(`${API_BASE}/valhalla/directions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error("Directions request failed");
  return await res.json();
}