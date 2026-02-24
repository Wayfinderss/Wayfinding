export interface Location {
  lat: number;
  lon: number;
}

export interface ValhallaLocation {
  lat: number;
  lon: number;
}

export interface ValhallaRequest {
  locations: ValhallaLocation[];
  costing: 'pedestrian' | 'bicycle' | 'auto';
  directions_options?: {
    units?: 'miles' | 'kilometers';
  };
}

export interface ValhallaManeuver {
  type: number;
  instruction: string;
  length: number;
  time: number;
}

export interface ValhallaLeg {
  shape: string;
  summary: {
    length: number;
    time: number;
  };
  maneuvers: ValhallaManeuver[];
}

export interface ValhallaResponse {
  trip: {
    legs: ValhallaLeg[];
    summary: {
      length: number;
      time: number;
    };
  };
}

export interface ValhallaError {
  error_code: number;
  error: string;
  status_code: number;
  status: string;
}
