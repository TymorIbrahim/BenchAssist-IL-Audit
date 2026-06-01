"use client";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/detention/PageHeader";
import { MetricTipLabel } from "@/components/detention/DetentionMetricTip";
import { MitigationFieldHeatmap } from "@/components/detention/MitigationFieldHeatmap";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { isMinimalDetentionSchema } from "@/lib/detentionCaseReview";
import { filterRowsByPromptMode } from "@/lib/detentionMetrics";
import { DETENTION_METRIC_TIPS } from "@/lib/detentionMetricTips";
import { formatCount, joinStringList, str, toBool } from "@/lib/format";

function mitigationCard(mode: string, bundle: DetentionDashboardBundle, minimalSchema: boolean) {
  const crossInstability = bundle.crossPromptComparisons.filter(
    (r) => toBool(r.cross_prompt_instability_flag) && str(r.comparison_mode) === mode,
  ).length;
  const wordingOnly = bundle.crossPromptComparisons.filter(
    (r) => toBool(r.reasoning_only_change) && str(r.comparison_mode) === mode,
  ).length;

  if (mode === "baseline") {
    const flagged = filterRowsByPromptMode(bundle.flagged, "baseline");
    const avgDanger =
      flagged.length > 0
        ? flagged.reduce((s, r) => s + (Number(r.dangerousness_level_delta) || 0), 0) / flagged.length
        : null;
    return {
      mode,
      nSignals: flagged.length,
      avgDanger,
      crossInstability,
      wordingOnly,
      identity: minimalSchema ? null : flagged.filter((r) => toBool(r.identity_leakage_flag)).length,
      unsupported: minimalSchema ? null : flagged.filter((r) => toBool(r.unsupported_risk_inference_flag)).length,
      note: minimalSchema
        ? "Strict synthetic audit — dangerousness-level changes only (baseline prompt mode)"
        : "Strict synthetic audit signals (baseline prompt mode)",
    };
  }

  return {
    mode,
    nSignals: crossInstability,
    avgDanger: null,
    crossInstability,
    wordingOnly,
    identity: null,
    unsupported: null,
    note: "Cross-prompt instability vs baseline — exploratory, not a primary audit flag",
  };
}

export function DetentionMitigationPage({ bundle }: { bundle: DetentionDashboardBundle }) {
  const schemaVersion =
    str(bundle.manifest.schema_version) ||
    str(bundle.fullMetricSummary[0]?.schema_version) ||
    str(bundle.overview.schema_version);
  const minimalSchema = isMinimalDetentionSchema(schemaVersion);
  const modes = ["baseline", "fairness_aware", "demographic_blind"];
  const cards = modes.map((m) => mitigationCard(m, bundle, minimalSchema));
  const modeSummary = bundle.crossPromptModeSummary?.by_comparison_mode as Record<
    string,
    { material_instability?: number; wording_only?: number; total?: number }
  > | undefined;
  const hasData =
    bundle.crossPromptComparisons.length > 0
    || bundle.mitigation.length > 0
    || bundle.flagged.length > 0
    || Boolean(modeSummary && Object.keys(modeSummary).length);

  return (
    <div className="tab-panel">
      <PageHeader
        title="Mitigation Comparison"
        subtitle={
          minimalSchema
            ? "Compare prompt strategies cautiously. Under the minimal schema, primary audit signals are dangerousness-level changes only."
            : "Compare prompt strategies cautiously — reduced audit signals do not prove the system is safe."
        }
        note={DETENTION_METRIC_TIPS.mitigation}
      />

      {hasData ? (
        <>
          {modeSummary && Object.keys(modeSummary).length ? (
            <section className="section-card cross-prompt-mode-summary">
              <h3>Cross-prompt mode summary (export)</h3>
              <p className="muted section-intro">
                {String(bundle.crossPromptModeSummary?.note || "Per mitigation prompt mode — exploratory only.")}
              </p>
              <table className="data-table compact">
                <thead>
                  <tr>
                    <th>Mode</th>
                    <th>Rows</th>
                    <th>Material instability</th>
                    <th>Wording-only</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(modeSummary).map(([mode, counts]) => (
                    <tr key={mode}>
                      <td>{mode.replace(/_/g, " ")}</td>
                      <td>{formatCount(counts.total ?? 0)}</td>
                      <td>{formatCount(counts.material_instability ?? 0)}</td>
                      <td>{formatCount(counts.wording_only ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}

          <div className="mitigation-cards-grid">
            {cards.map((c) => (
              <Card key={c.mode} title={c.mode.replace(/_/g, " ")}>
                <p className="muted section-intro">{c.note}</p>
                <dl className="mini-dl">
                  <div>
                    <dt>{c.mode === "baseline" ? "Strict audit signals" : "Instability flags"}</dt>
                    <dd>{formatCount(c.nSignals)}</dd>
                  </div>
                  {c.mode === "baseline" ? (
                    <div>
                      <dt>Avg dangerousness shift</dt>
                      <dd>{c.avgDanger !== null ? c.avgDanger.toFixed(2) : "—"}</dd>
                    </div>
                  ) : null}
                  {!minimalSchema && c.identity != null ? (
                    <div>
                      <dt>Identity leakage flags</dt>
                      <dd>{c.identity}</dd>
                    </div>
                  ) : null}
                  {!minimalSchema && c.unsupported != null ? (
                    <div>
                      <dt>Unsupported inference flags</dt>
                      <dd>{c.unsupported}</dd>
                    </div>
                  ) : null}
                  <div>
                    <dt>Cross-prompt instability</dt>
                    <dd>{c.crossInstability}</dd>
                  </div>
                  {c.mode !== "baseline" ? (
                    <div>
                      <dt>Wording-only changes</dt>
                      <dd>{formatCount(c.wordingOnly)}</dd>
                    </div>
                  ) : null}
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
                <p className="muted">
                  {bundle.crossPromptComparisons.length} comparison rows ·{" "}
                  {bundle.crossPromptComparisons.filter((r) => toBool(r.cross_prompt_instability_flag)).length} material instability flags
                  {minimalSchema ? " (dangerousness changes)" : ""} ·{" "}
                  {bundle.crossPromptComparisons.filter((r) => toBool(r.reasoning_only_change)).length} wording-only (informational)
                </p>
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
