"use client";

import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartBar } from "@/lib/filters";

export function BarChart({
  data,
  ariaLabel,
  onBarClick,
  activeKey,
  valueFormat = "percent",
  valueLabel = "Rate",
}: {
  data: ChartBar[];
  ariaLabel: string;
  onBarClick?: (bar: ChartBar) => void;
  activeKey?: string;
  valueFormat?: "percent" | "delta";
  valueLabel?: string;
}) {
  const formatValue = (v: number) => (valueFormat === "delta" ? v.toFixed(2) : `${v.toFixed(1)}%`);
  const yAxisTick = (v: number) => (valueFormat === "delta" ? v.toFixed(2) : `${v}%`);
  if (!data.length) {
    return <p className="empty-inline">No chart data available.</p>;
  }

  return (
    <div className="chart-wrap" role="img" aria-label={ariaLabel}>
      {onBarClick ? <p className="muted chart-hint">Click a bar to filter flagged cases by that group.</p> : null}
      <ResponsiveContainer width="100%" height={320}>
        <RechartsBarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 64 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} height={80} tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={yAxisTick} />
          <Tooltip formatter={(v: number) => [formatValue(v), valueLabel]} />
          <Bar
            dataKey="value"
            radius={[4, 4, 0, 0]}
            cursor={onBarClick ? "pointer" : "default"}
            onClick={(entry) => onBarClick?.(entry as unknown as ChartBar)}
          >
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={activeKey && (entry.rawKey === activeKey || entry.name === activeKey) ? "#1e40af" : "#2563eb"}
              />
            ))}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
      <p className="sr-only chart-alt">
        {data.map((d) => `${d.name}: ${formatValue(d.value)}`).join("; ")}
      </p>
    </div>
  );
}
