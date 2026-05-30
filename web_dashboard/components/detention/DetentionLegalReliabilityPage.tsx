"use client";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/detention/PageHeader";
import { MetricTipLabel } from "@/components/detention/DetentionMetricTip";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { formatCount, formatRate, str, toBool } from "@/lib/format";

const RELIABILITY_GROUPS = [
  { key: "reasonable_suspicion", label: "Reasonable suspicion" },
  { key: "dangerousness", label: "Dangerousness" },
  { key: "obstruction", label: "Obstruction" },
  { key: "alternatives", label: "Alternatives to detention" },
  { key: "safeguards", label: "Procedural safeguards" },
  { key: "duration", label: "Recommended duration" },
];

function countByGroup(bundle: DetentionDashboardBundle, groupKey: string): number {
  return bundle.flagged.filter((r) => {
    if (groupKey === "alternatives") return toBool(r.less_restrictive_alternatives_considered_omission);
    if (groupKey === "safeguards") return toBool(r.procedural_safeguards_mentioned_omission);
    if (groupKey === "duration") return Number(r.recommended_duration_days_delta) !== 0;
    if (groupKey === "dangerousness") return Number(r.dangerousness_level_delta) !== 0;
    if (groupKey === "obstruction") return Number(r.obstruction_risk_level_delta) !== 0;
    if (groupKey === "reasonable_suspicion") return Number(r.reasonable_suspicion_assessment_delta) !== 0;
    return false;
  }).length;
}

export function DetentionLegalReliabilityPage({
  bundle,
  isMock,
}: {
  bundle: DetentionDashboardBundle;
  isMock: boolean;
}) {
  const unsupported = bundle.flagged.filter((r) => toBool(r.unsupported_risk_inference_flag)).length;
  const identity = bundle.flagged.filter((r) => toBool(r.identity_leakage_flag)).length;

  const statisticalRows = (bundle.statisticalTests.length ? bundle.statisticalTests : bundle.statisticalEffects).map((r) => {
    const flaggedRate = Number(r.flagged_rate);
    if (!flaggedRate && bundle.groupSummary.length) {
      const gs = bundle.groupSummary.find((g) => str(g.variant_type) === str(r.variant_type));
      if (gs && Number(gs.flagged_rate)) {
        return { ...r, flagged_rate: gs.flagged_rate, effect_size: gs.flagged_rate };
      }
    }
    return r;
  });

  return (
    <div className="tab-panel">
      <PageHeader
        title="Legal Reliability"
        subtitle="Grounding, hallucination risk, and statistical uncertainty — separate from strict fairness audit signals."
        note={isMock ? "Mock data — statistical tables illustrate methodology only, not research findings." : undefined}
      />

      <div className="metric-grid">
        <StatCardSimple label="Unsupported inferences" value={unsupported} tip="unsupported_inference" />
        <StatCardSimple label="Identity leakage flags" value={identity} tip="identity_leakage" />
        <StatCardSimple label="Hallucination rows" value={0} tip="audit_signal" />
        <StatCardSimple label="Statistical tests" value={bundle.statisticalTests.length || bundle.statisticalEffects.length} tip="audit_signal" />
      </div>

      <section className="section-card">
        <h3>Issues by legal field</h3>
        <div className="findings-grid">
          {RELIABILITY_GROUPS.map((g) => (
            <Card key={g.key} title={g.label}>
              <p className="stat-large">{formatCount(countByGroup(bundle, g.key))}</p>
              <p className="muted">Comparison(s) with possible concern — requires human review.</p>
            </Card>
          ))}
        </div>
      </section>

      {unsupported > 0 ? (
        <section className="section-card">
          <h3>Unsupported risk inferences</h3>
          <p>{unsupported} comparison(s) flagged. Review whether risk assessments are grounded in case facts.</p>
        </section>
      ) : null}

      {bundle.hallucinationPer.length ? (
        <section className="section-card">
          <h3>Grounding review</h3>
          <div className="findings-grid">
            {bundle.hallucinationPer.slice(0, 8).map((h, i) => (
              <Card key={i} title={str(h.case_id) || `Output ${i + 1}`}>
                <p>
                  Legal hallucination risk: <strong>{str(h.legal_hallucination_risk) || "—"}</strong>
                  {Number(h.unsupported_claim_count) > 0 ? ` · ${h.unsupported_claim_count} unsupported claim(s)` : ""}
                  {toBool(h.high_hallucination_risk) ? " · High risk" : ""}
                </p>
                {Number(h.invalid_citation_count) > 0 ? (
                  <p className="muted">Invalid citations: {str(h.invalid_citation_count)}</p>
                ) : null}
              </Card>
            ))}
          </div>
        </section>
      ) : (
        <EmptyState
          title="No detention hallucination audit"
          description="Grounded hallucination checks are not exported for the detention synthetic audit in this dashboard. Use Legal Reliability for unsupported-inference flags from strict pairwise comparisons, and Real Cases for qualitative grounding review."
          command="python -m benchassist.vercel_export --auto --use-case detention --run-dir results/gemini/detention_full --data-status gemini_full"
        />
      )}

      {bundle.statisticalEffects.length || bundle.statisticalTests.length ? (
        <section className="section-card">
          <h3>Statistical confidence</h3>
          <p className="muted">
            Exploratory screening with uncertainty bounds. Real cases excluded from strict-rate statistics.
            Results are not corrected for multiple comparisons and should not be read as confirmatory hypothesis tests.
          </p>
          <div className="callout callout-info statistical-caveat">
            <p>
              <strong>Interpretation caveat:</strong> effect sizes and confidence intervals are screening aids only.
              A small p-value or narrow CI does not establish unlawful discrimination or model unreliability without legal review.
            </p>
          </div>
          <div className="stat-table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>Variant</th><th>Metric</th><th>Effect</th><th>CI</th></tr>
              </thead>
              <tbody>
                {statisticalRows.slice(0, 20).map((r, i) => (
                  <tr key={i}>
                    <td>{str(r.variant_type)}</td>
                    <td>{str(r.metric_name || r.metric || r.outcome)}</td>
                    <td>
                      {r.flagged_rate != null && Number(r.flagged_rate) <= 1
                        ? formatRate(r.flagged_rate)
                        : str(r.effect_size || r.mean_delta || r.flagged_rate)}
                    </td>
                    <td>{str(r.ci_lower)} – {str(r.ci_upper)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <EmptyState
          title="No statistical effects exported"
          description="Statistical group effects are optional. Export after full Gemini run for confidence intervals."
          command="python -m benchassist.vercel_export --auto --use-case detention --run-dir results/gemini/detention_full --data-status gemini_full"
        />
      )}
    </div>
  );
}

function StatCardSimple({ label, value, tip }: { label: string; value: number; tip: keyof typeof import("@/lib/detentionMetricTips").DETENTION_METRIC_TIPS }) {
  return (
    <div className="stat-card-simple">
      <span className="stat-card-label">
        <MetricTipLabel tipKey={tip}>{label}</MetricTipLabel>
      </span>
      <span className="stat-card-value">{formatCount(value)}</span>
    </div>
  );
}
