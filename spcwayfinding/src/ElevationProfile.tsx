import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { ElevationSample } from './Map';

interface ElevationProfileProps {
  elevationSamples: ElevationSample[] | null;
}

export default function ElevationProfile({ elevationSamples }: ElevationProfileProps) {
  const { minElev, maxElev, totalGain, totalLoss } = useMemo(() => {
    if (!elevationSamples || elevationSamples.length === 0) {
      return { minElev: 0, maxElev: 0, totalGain: 0, totalLoss: 0 };
    }

    let gain = 0;
    let loss = 0;
    for (let i = 1; i < elevationSamples.length; i++) {
      const delta = elevationSamples[i].relativeElevation - elevationSamples[i - 1].relativeElevation;
      if (delta > 0) gain += delta;
      else loss += Math.abs(delta);
    }

    const relatives = elevationSamples.map((p) => p.relativeElevation);
    return {
      minElev: Math.min(...relatives),
      maxElev: Math.max(...relatives),
      totalGain: Math.round(gain),
      totalLoss: Math.round(loss),
    };
  }, [elevationSamples]);

  if (!elevationSamples || elevationSamples.length === 0) return null;

  return (
    <div
      style={{
        height: '160px',
        width: '100%',
        background: 'rgba(255, 255, 255, 0.97)',
        borderTop: '1px solid #ddd',
        padding: '8px 20px 8px 10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        boxSizing: 'border-box',
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingLeft: '10px',
        }}
      >
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            color: '#555',
            letterSpacing: '1px',
            textTransform: 'uppercase',
          }}
        >
          Elevation Profile
        </span>
        <span style={{ fontSize: '11px', color: '#777' }}>
          <span style={{ color: '#43a047', marginRight: '10px' }}>
            ↑ {totalGain} ft gain
          </span>
          <span style={{ color: '#e53935' }}>↓ {totalLoss} ft loss</span>
        </span>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={elevationSamples}
          margin={{ top: 4, right: 10, left: 0, bottom: 4 }}
        >
          <defs>
            <linearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2196F3" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#2196F3" stopOpacity={0.05} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />

          <XAxis
            dataKey="distance"
            tick={{ fontSize: 10, fill: '#888' }}
            tickFormatter={(v) => `${Number(v).toFixed(1)} mi`}
            stroke="#ccc"
          />

          <YAxis
            tick={{ fontSize: 10, fill: '#888' }}
            tickFormatter={(v) => `${v >= 0 ? '+' : ''}${v} ft`}
            stroke="#ccc"
            width={54}
            domain={[minElev - 5, maxElev + 5]}
          />

          <Tooltip
            contentStyle={{
              background: 'rgba(255,255,255,0.95)',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '12px',
            }}
            formatter={(value: any) =>
              typeof value === 'number'
                ? [`${value >= 0 ? '+' : ''}${value} ft`, 'Elevation']
                : [value, 'Elevation']
            }
            labelFormatter={(v) => `Distance: ${Number(v).toFixed(2)} mi`}
          />

          <Area
            type="monotone"
            dataKey="relativeElevation"
            stroke="#2196F3"
            strokeWidth={2}
            fill="url(#elevationGradient)"
            name="Elevation"
            dot={false}
            activeDot={{ r: 3 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}