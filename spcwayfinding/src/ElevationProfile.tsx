import { useEffect, useState, useRef} from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ElevationPoint {
  distance: number;      // Distance from start in miles
  elevation: number;     // Elevation in feet
  relativeElevation: number; // Elevation relative to start
}

interface ElevationProfileProps {
  routeData: any | null;  // Full Valhalla response
  onHover?: (fraction: number | null) => void;
}

export default function ElevationProfile({ routeData, onHover}: ElevationProfileProps) {
  const [elevationData, setElevationData] = useState<ElevationPoint[]>([]);
  const [minElev, setMinElev] = useState(0);
  const [maxElev, setMaxElev] = useState(0);
  const [chartWidth, setChartWidth] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      setChartWidth(entries[0].contentRect.width);
    });
    ro.observe(el);
    setChartWidth(el.clientWidth);
    return () => ro.disconnect();
  }, [elevationData]); // re-run when elevationData arrives so ref is mounted

  useEffect(() => {
    if (!routeData || !routeData.trip) {
      setElevationData([]);
      return;
    }

    try {
      const leg = routeData.trip.legs[0];
      
      // Check if we have the elevation array (Valhalla's format)
      if (leg.elevation && Array.isArray(leg.elevation) && leg.shape) {        
        // Decode the polyline to get coordinates
        //const coordinates = polyline.decode(leg.shape, 6);
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

        setElevationData(points);
        
        // Calculate min/max for dynamic scaling
        const elevations = points.map(p => p.relativeElevation);
        setMinElev(Math.min(...elevations));
        setMaxElev(Math.max(...elevations));
        
      } else {
        console.warn('No elevation array in Valhalla response');
        setElevationData([]);
      }
    } catch (error) {
      console.error('Error processing elevation data:', error);
      setElevationData([]);
    }
  }, [routeData]);

  const handleMouseMove = (e: any) => {
    if (!onHover || elevationData.length === 0) return;
    if (e.activeLabel !== undefined && e.activeLabel !== null) {
      const totalDistance = elevationData[elevationData.length - 1].distance;
      const fraction = totalDistance > 0 ? Number(e.activeLabel) / totalDistance : 0;
      onHover(fraction);
    }
  };

  const handleMouseLeave = () => onHover?.(null);

  if (elevationData.length === 0) {
    return null; // Don't show anything if no route
  }

  return (
    <div style={{
      height: '140px',
      minHeight: '140px',
      flexShrink: 0,
      width: '100%',
      background: 'rgba(255, 255, 255, 0.95)',
      borderTop: '1px solid #ddd',
      padding: '10px 20px 10px 10px',
      boxSizing: 'border-box',
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

      <div ref={containerRef} style={{ flex: 1, minHeight: 0 }}>
      {chartWidth > 0 && (
        <AreaChart
        width={chartWidth}
        height={100}
        data={elevationData}
        margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
      {/* Chart */}
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
         )}
    </div>
    </div>
  );
}