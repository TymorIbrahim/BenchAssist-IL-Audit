"use client";

import { formatCount } from "@/lib/format";
import type { DetentionDashboardBundle } from "@/lib/detentionData";

export function DetentionReviewFunnel({ bundle }: { bundle: DetentionDashboardBundle }) {
  const { overview, manifest } = bundle;
  const synthetic = Number(overview.n_synthetic_counterfactual_rows ?? manifest.detention_synthetic_rows ?? 156);
  const strict = Number(overview.n_pairwise_comparisons ?? bundle.strictEligibleCount);
  const flagged = Number(overview.n_flagged_comparisons ?? bundle.flagged.length);
  const highPriority = bundle.highPriorityCount;
  const realCases = Number(overview.n_real_case_pilot_rows ?? manifest.detention_pilot_row_count ?? bundle.realCaseExamples.length);

  const syntheticSteps = [
    { label: "Total synthetic rows", value: synthetic, note: "Controlled scenarios" },
    { label: "Strict counterfactual comparisons", value: strict, note: "Same legal facts" },
    { label: "Audit signals", value: flagged, note: "Framing shifts detected" },
    { label: "Flagged for legal review", value: flagged, note: "Review queue" },
    { label: "High-priority queue", value: highPriority, note: "Requires human review first" },
  ];

  const realSteps = [
    { label: "Real public legal examples", value: realCases, note: "Israeli detention/remand corpus" },
    { label: "Expert full-text examples", value: bundle.realCaseExamples.length, note: "Internal review material" },
    { label: "Qualitative / legal review", value: "Yes", note: "Realism & reliability" },
    { label: "In strict fairness rates", value: "No", note: "Excluded by design" },
  ];

  return (
    <div className="review-funnel-wrap">
      <div className="review-funnel">
        <h3 className="funnel-title">Synthetic strict-fairness audit funnel</h3>
        <div className="funnel-track">
          {syntheticSteps.map((step, i) => (
            <div key={step.label} className="funnel-step">
              <div className="funnel-step-value">{typeof step.value === "number" ? formatCount(step.value) : step.value}</div>
              <div className="funnel-step-label">{step.label}</div>
              <div className="funnel-step-note">{step.note}</div>
              {i < syntheticSteps.length - 1 ? <span className="funnel-arrow" aria-hidden="true">→</span> : null}
            </div>
          ))}
        </div>
      </div>
      <div className="review-funnel review-funnel-real">
        <h3 className="funnel-title">Real-case layer (separate from strict rates)</h3>
        <div className="funnel-track funnel-track-compact">
          {realSteps.map((step, i) => (
            <div key={step.label} className="funnel-step funnel-step-real">
              <div className="funnel-step-value">{typeof step.value === "number" ? formatCount(step.value) : step.value}</div>
              <div className="funnel-step-label">{step.label}</div>
              <div className="funnel-step-note">{step.note}</div>
              {i < realSteps.length - 1 ? <span className="funnel-arrow" aria-hidden="true">→</span> : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
