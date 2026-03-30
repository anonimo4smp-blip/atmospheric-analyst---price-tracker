import React from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts';
import { PriceHistoryPoint } from '../types';

interface PriceChartProps {
  targetPrice: number;
  history: PriceHistoryPoint[];
}

export function PriceChart({ targetPrice, history }: PriceChartProps) {
  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={history}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="100%">
              <stop offset="5%" stopColor="#0053dc" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#0053dc" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f4f7" />
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{fontSize: 10, fontWeight: 700, fill: '#596064'}}
            padding={{left: 10, right: 10}}
          />
          <YAxis hide domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{
              borderRadius: '12px',
              border: 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              fontSize: '12px',
              fontWeight: 700,
            }}
          />
          <ReferenceLine
            y={targetPrice}
            stroke="#0053dc"
            strokeDasharray="3 3"
            label={{
              position: 'right',
              value: `TARGET EUR ${targetPrice.toFixed(2)}`,
              fill: '#0053dc',
              fontSize: 8,
              fontWeight: 800,
            }}
          />
          <Area
            type="monotone"
            dataKey="price"
            stroke="#0053dc"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorPrice)"
            dot={{r: 4, fill: '#0053dc', strokeWidth: 0}}
            activeDot={{r: 6, strokeWidth: 0}}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
