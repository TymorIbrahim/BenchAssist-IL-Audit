"use client";

import dynamic from "next/dynamic";
import type { ComponentProps } from "react";

const BarChartImpl = dynamic(
  () => import("@/components/BarChart").then((m) => m.BarChart),
  {
    ssr: false,
    loading: () => <p className="muted chart-loading">Loading chart…</p>,
  },
);

export function LazyBarChart(props: ComponentProps<typeof BarChartImpl>) {
  return <BarChartImpl {...props} />;
}
