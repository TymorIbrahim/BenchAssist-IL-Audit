"use client";

import { Callout } from "@/components/Callout";
import type { CaseReviewRecord } from "@/lib/detentionCaseReview";
import { analysisBucketLabel } from "@/lib/detentionCaseReview";

export function ValidityContextPanel({ record }: { record: CaseReviewRecord }) {
  const ctx = record.validity_context;
  const excluded =
    ctx?.exclude_from_strict_bias_rates === true ||
    ctx?.exclude_from_strict_bias_rates === "true" ||
    record.use_for_strict_bias_rates === false;

  if (!ctx && !excluded) return null;

  const score = ctx?.fact_preservation_score;
  const scoreLabel =
    score === null || score === undefined ? "—" : typeof score === "number" ? score.toFixed(2) : String(score);

  return (
    <Callout title="Validity & strict-rate eligibility" variant={excluded ? "caution" : "info"}>
      <dl className="meta-dl meta-dl-stack">
        <div>
          <dt>Analysis bucket</dt>
          <dd>{analysisBucketLabel(record.analysis_bucket)}</dd>
        </div>
        <div>
          <dt>Fact preservation score</dt>
          <dd>{scoreLabel}</dd>
        </div>
        {ctx?.validity_category ? (
          <div>
            <dt>Validity category</dt>
            <dd>{String(ctx.validity_category).replace(/_/g, " ")}</dd>
          </div>
        ) : null}
        {excluded && ctx?.strict_exclusion_reason ? (
          <div>
            <dt>Why excluded from strict headline rates</dt>
            <dd>{ctx.strict_exclusion_reason}</dd>
          </div>
        ) : null}
        {ctx?.gold_label_applied ? (
          <div>
            <dt>Gold label</dt>
            <dd>Expert calibration label applied for this variant</dd>
          </div>
        ) : null}
      </dl>
    </Callout>
  );
}
