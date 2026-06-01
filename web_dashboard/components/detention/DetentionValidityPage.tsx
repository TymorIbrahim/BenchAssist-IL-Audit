"use client";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/detention/PageHeader";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { isMinimalDetentionSchema, type CaseReviewFilters } from "@/lib/detentionCaseReview";
import { detentionHeadlineMetrics } from "@/lib/detentionMetrics";
import { formatCount, formatRate, str } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

function ValidityCategoryBadge({ category }: { category: string }) {
  const cls =
    category === "strict_counterfactual"
      ? "badge-success"
      : category === "invalid_or_changed_facts"
        ? "badge-concern"
        : category.includes("stress") || category.includes("intersectional")
          ? "badge-caution"
          : "badge-neutral";
  return <span className={`badge ${cls}`}>{category.replace(/_/g, " ")}</span>;
}

export function DetentionValidityPage({
  bundle,
  onOpenCaseReview,
}: {
  bundle: DetentionDashboardBundle;
  onOpenCaseReview?: (
    patch: Partial<CaseReviewFilters>,
    reviewId?: string | null,
    presetId?: string | null,
  ) => void;
}) {
  const validity = bundle.validityRows;
  const summary = bundle.validitySummary;
  const calibration = bundle.validityCalibration;
  const uncertainty = bundle.overviewUncertainty as { overview?: JsonRecord } | null;
  const headline = detentionHeadlineMetrics(bundle);
  const schemaVersion =
    str(bundle.manifest.schema_version) ||
    str(bundle.fullMetricSummary[0]?.schema_version) ||
    str(bundle.overview.schema_version);
  const minimalSchema = isMinimalDetentionSchema(schemaVersion);
  const addressProxyOutputs = Number(bundle.overview.n_address_proxy_review_outputs ?? 0);
  const strictExcluded = Number(bundle.overview.n_strict_excluded_review_outputs ?? 0);
  const addressProxyComparisons = bundle.addressProxyPairwise.length;
  const addressProxyFlagged = bundle.addressProxyPairwise.filter(
    (r) => r.detention_framing_bias_flag === true || r.detention_framing_bias_flag === "True",
  ).length;

  if (!validity.length) {
    return (
      <div className="tab-panel">
        <PageHeader title="Validity & exclusions" subtitle="Counterfactual fact-preservation screening for strict audit rates." />
        <EmptyState
          title="Validity audit not exported"
          description="Run detention data generation and vercel export to populate validity tables."
          command="python -m benchassist.detention_counterfactual_validity && python -m benchassist.vercel_export --auto --use-case detention"
        />
      </div>
    );
  }

  const excluded = validity.filter((r) => r.exclude_from_strict_bias_rates === true || r.exclude_from_strict_bias_rates === "True");
  const eligible = validity.filter((r) => !excluded.includes(r));

  return (
    <div className="tab-panel">
      <PageHeader
        title="Validity & exclusions"
        subtitle={
          minimalSchema
            ? "Heuristic fact-preservation audit for strict demographic rates. Address-proxy variants are reported in a separate bucket."
            : "Heuristic fact-preservation audit — separates strict-eligible pairs from stress tests and invalid comparisons."
        }
        note="Not proof of factual equivalence. Gold labels calibrate heuristics where available."
      />

      <div className="metric-grid">
        <Card title="Total variant rows">
          <p className="metric-value">{formatCount(validity.length)}</p>
        </Card>
        <Card title="Strict-eligible (heuristic)">
          <p className="metric-value">{formatCount(eligible.length)}</p>
        </Card>
        <Card title="Excluded from strict rates">
          <p className="metric-value">{formatCount(excluded.length)}</p>
        </Card>
        {minimalSchema ? (
          <Card title="Address-proxy bucket">
            <p className="metric-value">{formatCount(addressProxyOutputs || strictExcluded)}</p>
            <p className="muted">Separate from strict demographic flagged rates</p>
          </Card>
        ) : null}
        {uncertainty?.overview?.flagged_rate != null ? (
          <Card title="Flagged rate (95% CI)">
            <p className="metric-value">
              {formatRate(Number(uncertainty.overview.flagged_rate))}
              {" "}
              <span className="muted">
                [{formatRate(Number(uncertainty.overview.flagged_rate_ci_low))}–{formatRate(Number(uncertainty.overview.flagged_rate_ci_high))}]
              </span>
            </p>
            {minimalSchema ? <p className="muted">Dangerousness-level changes only</p> : null}
          </Card>
        ) : null}
      </div>

      {minimalSchema && (addressProxyComparisons > 0 || addressProxyOutputs > 0) ? (
        <section className="section-card">
          <h3>Address-proxy validity bucket</h3>
          <p className="muted section-intro">
            Address strings are proxy-cautious stress tests. They are excluded from strict demographic fairness rates and reviewed separately in Case Review (analysis bucket filter).
          </p>
          <div className="metric-grid metric-grid-compact">
            <Card title="Address-proxy comparisons">
              <p className="metric-value">{formatCount(addressProxyComparisons)}</p>
            </Card>
            <Card title="Address-proxy audit signals">
              <p className="metric-value">{formatCount(addressProxyFlagged)}</p>
              <p className="muted">Dangerousness Δ only</p>
            </Card>
            <Card title="Strict-excluded outputs">
              <p className="metric-value">{formatCount(strictExcluded)}</p>
            </Card>
          </div>
          {onOpenCaseReview ? (
            <div className="btn-row validity-queue-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => onOpenCaseReview({ analysisBucket: "address_proxy", flaggedOnly: true }, null, "address-proxy")}
              >
                Open address-proxy review queue
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => onOpenCaseReview({ flaggedOnly: true })}
              >
                Open all flagged comparisons
              </button>
            </div>
          ) : null}
        </section>
      ) : null}

      {summary.length ? (
        <section className="section-card">
          <h3>By validity category</h3>
          <div className="validity-summary-grid">
            {summary.map((row: JsonRecord) => (
              <div key={str(row.validity_category)} className="validity-summary-card">
                <ValidityCategoryBadge category={str(row.validity_category)} />
                <p>n={formatCount(Number(row.n_variants))} · preservation={Number(row.mean_fact_preservation_score).toFixed(2)}</p>
                <p className="muted">Direct eligible: {formatCount(Number(row.n_direct_eligible))}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {calibration && Number(calibration.n_gold_labels) > 0 ? (
        <section className="section-card">
          <h3>Gold-label calibration</h3>
          <p className="muted">
            {formatCount(Number(calibration.n_matched))} expert-labeled pairs matched · exclusion accuracy:{" "}
            {calibration.exclude_decision_accuracy != null ? formatRate(Number(calibration.exclude_decision_accuracy)) : "—"}
          </p>
        </section>
      ) : null}

      <section className="section-card">
        <h3>Review funnel</h3>
        <ol className="review-funnel-list">
          <li>All synthetic variant rows ({formatCount(validity.length)})</li>
          <li>Heuristic strict-eligible ({formatCount(eligible.length)})</li>
          <li>
            Flagged comparisons ({formatCount(headline.flaggedCount)} baseline · {formatCount(headline.flaggedCountAllModes)} all modes)
            {minimalSchema ? " — dangerousness-level changes only" : ""}
          </li>
          {minimalSchema && addressProxyOutputs ? (
            <li>Address-proxy outputs ({formatCount(addressProxyOutputs)}) — separate expert review bucket</li>
          ) : null}
          <li>Expert-reviewed locally (see Case Review progress)</li>
        </ol>
      </section>
    </div>
  );
}
