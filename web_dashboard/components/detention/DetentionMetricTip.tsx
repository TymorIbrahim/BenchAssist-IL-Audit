"use client";

import { DETENTION_METRIC_TIPS } from "@/lib/detentionMetricTips";

export function DetentionMetricTip({ tipKey, label }: { tipKey: keyof typeof DETENTION_METRIC_TIPS; label?: string }) {
  const text = DETENTION_METRIC_TIPS[tipKey];
  return (
    <span className="metric-tip-inline">
      {label ?? null}
      <button type="button" className="info-tip-btn" title={text} aria-label={`Explain: ${tipKey.replace(/_/g, " ")}`}>
        ⓘ
      </button>
    </span>
  );
}

export function MetricTipLabel({ tipKey, children }: { tipKey: keyof typeof DETENTION_METRIC_TIPS; children: React.ReactNode }) {
  return (
    <span className="metric-tip-inline">
      {children}
      <DetentionMetricTip tipKey={tipKey} />
    </span>
  );
}
