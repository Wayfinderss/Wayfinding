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

const API_BASE = "http://localhost:8000"; // Adjust if your backend is on a different port

export async function geocodeAddress(query: string): Promise<GeocodeResult[]> {
  const res = await fetch(`${API_BASE}/geocode/autocomplete?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error("Geocoding failed");
  const data = await res.json();
  return data.results;
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