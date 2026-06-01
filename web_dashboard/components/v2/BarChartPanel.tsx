"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface BarChartDatum {
  name: string;
  value: number;
  fill?: string;
}

interface BarChartPanelProps {
  data: BarChartDatum[];
  title?: string;
  yLabel?: string;
  height?: number;
  formatValue?: (v: number) => string;
}

const DEFAULT_FILL = "#6366f1";

export function BarChartPanel({
  data,
  title,
  yLabel,
  height = 300,
  formatValue,
}: BarChartPanelProps) {
  if (!data.length) {
    return (
      <div className="v2-bar-chart-panel v2-bar-chart-panel--empty">
        {title && <h3 className="v2-bar-chart-panel__title">{title}</h3>}
        <p className="v2-bar-chart-panel__empty-message">No data to display</p>
      </div>
    );
  }

  const formatter = formatValue ?? ((v: number) => String(v));

  return (
    <div className="v2-bar-chart-panel">
      {title && <h3 className="v2-bar-chart-panel__title">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#d1d5db" }}
          />
          <YAxis
            label={
              yLabel
                ? {
                    value: yLabel,
                    angle: -90,
                    position: "insideLeft",
                    style: { fontSize: 12, fill: "#6b7280" },
                  }
                : undefined
            }
            tick={{ fontSize: 12, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#d1d5db" }}
            tickFormatter={formatter}
          />
          <Tooltip
            formatter={(value: number) => [formatter(value), "Value"]}
            contentStyle={{
              fontSize: 13,
              borderRadius: 6,
              border: "1px solid #e5e7eb",
            }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={60}>
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.fill ?? DEFAULT_FILL} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
