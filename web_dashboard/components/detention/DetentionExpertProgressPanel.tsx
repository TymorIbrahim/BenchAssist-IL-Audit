"use client";

import type { ReviewProgressSummary } from "@/lib/detentionReview";
import { formatCount } from "@/lib/format";

export function DetentionExpertProgressPanel({ progress }: { progress: ReviewProgressSummary }) {
  return (
    <section className="section-card expert-progress-panel">
      <h3>Expert review progress</h3>
      <p className="muted section-intro">
        Local browser review state — export JSON to share with the audit team.
      </p>
      <div className="metric-grid compact-metric-grid">
        <div><strong>{formatCount(progress.reviewed)}</strong> / {formatCount(progress.flaggedTotal)} flagged reviewed</div>
        <div>{formatCount(progress.possibleConcern)} possible concern</div>
        <div>{formatCount(progress.includeInReport)} for report</div>
        <div>{formatCount(progress.inPacket)} in packet</div>
      </div>
      {progress.closureMet ? (
        <p className="badge badge-success">Audit closure threshold met (≥{progress.closureMin} reviews)</p>
      ) : (
        <p className="muted">Closure requires ≥{progress.closureMin} expert-reviewed flagged cases ({progress.reviewed}/{progress.closureMin}).</p>
      )}
    </section>
  );
}
