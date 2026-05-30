"use client";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/detention/PageHeader";
import { MetricTipLabel } from "@/components/detention/DetentionMetricTip";
import { MitigationFieldHeatmap } from "@/components/detention/MitigationFieldHeatmap";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { DETENTION_METRIC_TIPS } from "@/lib/detentionMetricTips";
import { formatCount, joinStringList, str, toBool } from "@/lib/format";

function mitigationCard(mode: string, bundle: DetentionDashboardBundle) {
  const crossInstability = bundle.crossPromptComparisons.filter(
    (r) => toBool(r.cross_prompt_instability_flag) && str(r.comparison_mode) === mode,
  ).length;

  if (mode === "baseline") {
    const flagged = bundle.flagged;
    const identity = flagged.filter((r) => toBool(r.identity_leakage_flag)).length;
    const unsupported = flagged.filter((r) => toBool(r.unsupported_risk_inference_flag)).length;
    const avgDanger =
      flagged.length > 0
        ? flagged.reduce((s, r) => s + (Number(r.dangerousness_level_delta) || 0), 0) / flagged.length
        : null;
    return {
      mode,
      nSignals: flagged.length,
      avgDanger,
      identity,
      unsupported,
      crossInstability,
      note: "Strict synthetic audit signals (baseline prompt mode)",
    };
  }

  return {
    mode,
    nSignals: crossInstability,
    avgDanger: null,
    identity: 0,
    unsupported: 0,
    crossInstability,
    note: "Cross-prompt instability vs baseline (not strict fairness audit)",
  };
}

export function DetentionMitigationPage({ bundle }: { bundle: DetentionDashboardBundle }) {
  const modes = ["baseline", "fairness_aware", "demographic_blind"];
  const cards = modes.map((m) => mitigationCard(m, bundle));
  const hasData = bundle.crossPromptComparisons.length > 0 || bundle.mitigation.length > 0 || bundle.flagged.length > 0;

  return (
    <div className="tab-panel">
      <PageHeader
        title="Mitigation Comparison"
        subtitle="Compare prompt strategies cautiously — reduced audit signals do not prove the system is safe."
        note={DETENTION_METRIC_TIPS.mitigation}
      />

      {hasData ? (
        <>
          <div className="mitigation-cards-grid">
            {cards.map((c) => (
              <Card key={c.mode} title={c.mode.replace(/_/g, " ")}>
                <p className="muted section-intro">{c.note}</p>
                <dl className="mini-dl">
                  <div><dt>{c.mode === "baseline" ? "Strict audit signals" : "Instability flags"}</dt><dd>{formatCount(c.nSignals)}</dd></div>
                  <div><dt>Avg dangerousness shift</dt><dd>{c.avgDanger !== null ? c.avgDanger.toFixed(2) : "—"}</dd></div>
                  <div><dt>Identity leakage flags</dt><dd>{c.identity}</dd></div>
                  <div><dt>Unsupported inference flags</dt><dd>{c.unsupported}</dd></div>
                  <div><dt>Cross-prompt instability</dt><dd>{c.crossInstability}</dd></div>
                </dl>
              </Card>
            ))}
          </div>

          {bundle.crossPromptComparisons.length ? (
            <>
            <MitigationFieldHeatmap bundle={bundle} />
            <section className="section-card">
              <h3>
                <MetricTipLabel tipKey="cross_prompt">Cross-prompt comparisons</MetricTipLabel>
              </h3>
              <p className="muted">{bundle.crossPromptComparisons.length} comparison rows · {bundle.crossPromptComparisons.filter((r) => toBool(r.cross_prompt_instability_flag)).length} possible instability flags</p>
              <div className="findings-grid">
                {bundle.crossPromptComparisons.slice(0, 6).map((r, i) => (
                  <Card key={i} title={`${str(r.case_id)} · ${str(r.comparison_mode)}`}>
                    <p className="muted">Fields changed: {joinStringList(r.fields_changed_list ?? r.fields_changed) || str(r.n_fields_changed)}</p>
                    <p>{str(r.review_note).slice(0, 160)}</p>
                  </Card>
                ))}
              </div>
            </section>
            </>
          ) : null}
        </>
      ) : (
        <EmptyState
          title="Mitigation data not available"
          description="Cross-prompt comparison data is not available yet. Run multi-prompt analysis/export to enable mitigation comparison. Basic case review is still available."
          command="python -m benchassist.vercel_export --auto --use-case detention --run-dir results/gemini/detention_full --data-status gemini_full"
        />
      )}
    </div>
  );
}
