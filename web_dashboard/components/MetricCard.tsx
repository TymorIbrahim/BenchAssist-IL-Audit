import { formatRate } from "@/lib/format";
import { metricNeedsReview } from "@/lib/derive";
import { StatusPill } from "./StatusPill";

export function MetricCard({
  label,
  value,
  meaning,
  caution,
  showReviewBadge = true,
}: {
  label: string;
  value: unknown;
  meaning: string;
  caution?: string;
  showReviewBadge?: boolean;
}) {
  const needsReview = showReviewBadge && metricNeedsReview(value);

  return (
    <div className="metric-card" aria-label={label}>
      <div className="metric-card-top">
        <div className="metric-label">{label}</div>
        {needsReview ? <StatusPill label="Needs review" variant="caution" /> : null}
      </div>
      <div className="metric-value">{formatRate(value)}</div>
      <p className="metric-meaning">{meaning}</p>
      {caution ? <p className="metric-caution">{caution}</p> : null}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: React.ReactNode;
}) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub ? <div className="stat-sub">{sub}</div> : null}
    </div>
  );
}
