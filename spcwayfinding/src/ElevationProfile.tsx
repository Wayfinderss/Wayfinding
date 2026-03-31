import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import polyline from '@mapbox/polyline';

interface ElevationPoint {
  distance: number;      // Distance from start in miles
  elevation: number;     // Elevation in feet
  relativeElevation: number; // Elevation relative to start
}

interface ElevationProfileProps {
  routeData: any | null;  // Full Valhalla response
}

export default function ElevationProfile({ routeData }: ElevationProfileProps) {
  const [elevationData, setElevationData] = useState<ElevationPoint[]>([]);
  const [minElev, setMinElev] = useState(0);
  const [maxElev, setMaxElev] = useState(0);

  useEffect(() => {
    if (!routeData || !routeData.trip) {
      setElevationData([]);
      return;
    }

    try {
      const leg = routeData.trip.legs[0];
      
      // Check if we have the elevation array (Valhalla's format)
      if (leg.elevation && Array.isArray(leg.elevation) && leg.shape) {
        console.log('Found elevation array with', leg.elevation.length, 'points');
        
        // Decode the polyline to get coordinates
        const coordinates = polyline.decode(leg.shape, 6);
        const elevationArray = leg.elevation; // Array of elevation values in meters
        
        // Valhalla's elevation_interval tells us the sampling rate
        const elevationInterval = leg.elevation_interval || 10; // meters between samples
        
        // Convert elevations to feet
        const startElevationMeters = elevationArray[0];
        const startElevationFeet = startElevationMeters * 3.28084;
        
        // Calculate distance for each elevation point
        let cumulativeDistance = 0;
        const points: ElevationPoint[] = elevationArray.map((elevMeters: number, index: number) => {
          const elevationFeet = elevMeters * 3.28084;
          
          // Estimate distance based on elevation interval
          // Each elevation point is approximately elevationInterval meters apart
          if (index > 0) {
            cumulativeDistance += (elevationInterval * 0.000621371); // Convert meters to miles
          }
          
          return {
            distance: cumulativeDistance,
            elevation: Math.round(elevationFeet),
            relativeElevation: Math.round(elevationFeet - startElevationFeet)
          };
        });

        console.log('Processed elevation points:', points.length);
        console.log('First point:', points[0]);
        console.log('Last point:', points[points.length - 1]);

        setElevationData(points);
        
        // Calculate min/max for dynamic scaling
        const elevations = points.map(p => p.relativeElevation);
        setMinElev(Math.min(...elevations));
        setMaxElev(Math.max(...elevations));
        
      } else {
        console.warn('No elevation array in Valhalla response');
        console.log('Available leg properties:', Object.keys(leg));
        setElevationData([]);
      }
    } catch (error) {
      console.error('Error processing elevation data:', error);
      setElevationData([]);
    }
  }, [routeData]);

  if (elevationData.length === 0) {
    return null; // Don't show anything if no route
  }

  return (
    <div style={{
      height: '140px',
      width: '100%',
      background: 'rgba(255, 255, 255, 0.95)',
      borderTop: '1px solid #ddd',
      padding: '10px 20px 10px 10px',
      display: 'flex',
      flexDirection: 'column',
      gap: '5px'
    }}>
      {/* Title */}
      <div style={{
        fontSize: '11px',
        fontWeight: 600,
        color: '#555',
        letterSpacing: '1px',
        textTransform: 'uppercase',
        paddingLeft: '10px'
      }}>
        Elevation Profile
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={elevationData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2196F3" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#2196F3" stopOpacity={0.05}/>
            </linearGradient>
          </defs>
          
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
          
          <XAxis 
            dataKey="distance" 
            tick={{ fontSize: 11, fill: '#666' }}
            tickFormatter={(value) => `${value.toFixed(1)} mi`}
            stroke="#ccc"
          />
          
          <YAxis 
            tick={{ fontSize: 11, fill: '#666' }}
            tickFormatter={(value) => `${value >= 0 ? '+' : ''}${value} ft`}
            stroke="#ccc"
            width={50}
            domain={[minElev - 5, maxElev + 5]}
          />
          
          <Tooltip 
            contentStyle={{
              background: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '12px'
            }}
            formatter={(value: any) => {
              if (typeof value === 'number') {
                return `${value >= 0 ? '+' : ''}${value} ft`;
              }
              return value;
            }}
            labelFormatter={(value) => `Distance: ${Number(value).toFixed(2)} mi`}
          />
          
          <Area 
            type="monotone" 
            dataKey="relativeElevation" 
            stroke="#2196F3" 
            strokeWidth={2}
            fill="url(#elevationGradient)" 
            name="Elevation"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}