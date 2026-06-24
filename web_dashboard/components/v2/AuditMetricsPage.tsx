/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";
import { formatVariantLabel } from "@/lib/v2/dataUtils";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CCREntry {
  ccr: number | null;
  n_comparisons: number;
  n_consistent: number;
  n_changed: number;
}

interface DIREntry {
  dir: number | null;
  adverse_rate: number;
  n_total: number;
  n_adverse: number;
}

interface MaskingModeDetail {
  dir: number | null;
  p_marginalized: number | null;
  p_privileged: number | null;
  n_marginalized: number;
  n_privileged: number;
}

interface MaskingDelta {
  delta: number | null;
  baseline_dir: number | null;
  masked_dir: number | null;
  interpretation: string;
}

interface AuditMetricsData {
  generated_at: string;
  n_total_comparisons: number;
  ccr: {
    overall: number | null;
    n_total: number;
    n_consistent: number;
    by_variant_type: Record<string, CCREntry>;
    by_prompt_mode: Record<string, CCREntry>;
  };
  dir: {
    overall: number | null;
    p_marginalized: number | null;
    p_privileged: number | null;
    n_marginalized: number;
    n_privileged: number;
    by_variant_type: Record<string, DIREntry>;
  };
  masking_efficiency: {
    by_mode: Record<string, MaskingModeDetail>;
    deltas: Record<string, MaskingDelta>;
  };
  semantic_divergence: {
    available: boolean;
    note?: string;
    overall_mean_divergence?: number | null;
    n_total_comparisons?: number;
    by_variant_type?: Record<string, {
      mean_divergence: number;
      n_comparisons: number;
    }>;
  };
  reasoning_flaws: {
    identity_leakage_rate_overall: number | null;
    hallucination_rate_overall: number | null;
    n_total: number;
    n_leakage_overall: number;
    n_hallucination_overall: number;
    by_variant_type: Record<string, {
      identity_leakage_rate: number | null;
      hallucination_rate: number | null;
      n_total: number;
      n_leakage: number;
      n_hallucination: number;
    }>;
  };
  error?: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function pct(val: number | null | undefined): string {
  if (val == null || Number.isNaN(val)) return "—";
  return (val * 100).toFixed(1) + "%";
}

function fmtNum(val: number | null | undefined, decimals = 2): string {
  if (val == null || Number.isNaN(val)) return "—";
  return val.toFixed(decimals);
}

function barWidth(rate: number, max: number): string {
  if (!max) return "0%";
  return ((rate / max) * 100).toFixed(1) + "%";
}

function variantLabel(v: string): string {
  return formatVariantLabel(v);
}

function interpretationBadge(interp: string): JSX.Element {
  const styles: Record<string, { bg: string; fg: string; label: string }> = {
    effective_reduction: { bg: "hsl(140 50% 90%)", fg: "hsl(140 50% 30%)", label: "✓ Effective Reduction" },
    minimal_effect: { bg: "hsl(45 80% 90%)", fg: "hsl(35 70% 35%)", label: "⚠ Minimal Effect (Audit Washing?)" },
    increased_bias: { bg: "hsl(0 75% 92%)", fg: "hsl(0 70% 40%)", label: "✗ Increased Bias" },
    insufficient_data: { bg: "hsl(220 15% 94%)", fg: "hsl(220 10% 55%)", label: "— Insufficient Data" },
  };
  const s = styles[interp] ?? styles.insufficient_data;
  return (
    <span style={{
      display: "inline-block", padding: "0.25rem 0.75rem", borderRadius: "999px",
      fontSize: "0.78rem", fontWeight: 650, background: s.bg, color: s.fg,
    }}>
      {s.label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Insight callout                                                    */
/* ------------------------------------------------------------------ */

const CALLOUT_STYLE: React.CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  gap: "0.75rem",
  padding: "1rem 1.25rem",
  background: "hsl(220 50% 97%)",
  border: "1px solid hsl(220 40% 88%)",
  borderLeft: "4px solid hsl(220 65% 50%)",
  borderRadius: 8,
  fontSize: "0.85rem",
  lineHeight: 1.55,
  marginBottom: "1rem",
};

function InsightCallout({ icon, children }: { icon?: string; children: React.ReactNode }) {
  return (
    <div style={CALLOUT_STYLE}>
      <span style={{ fontSize: "1.1rem", lineHeight: 1.4, flexShrink: 0 }} aria-hidden>{icon ?? "💡"}</span>
      <span style={{ color: "hsl(220 30% 25%)" }}>{children}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Section card styles                                                */
/* ------------------------------------------------------------------ */

const SECTION_CARD: React.CSSProperties = {
  background: "var(--v2-surface, #fff)",
  border: "1px solid var(--v2-border, hsl(220 15% 90%))",
  borderRadius: 12,
  padding: "1.5rem",
  marginBottom: "1.5rem",
};

const STAT_CARD: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "0.25rem",
  padding: "1.25rem 1rem",
  borderRadius: 10,
  background: "var(--v2-surface-raised, hsl(220 20% 98%))",
  border: "1px solid var(--v2-border, hsl(220 15% 90%))",
  minWidth: 140,
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function AuditMetricsPage() {
  const [data, setData] = useState<AuditMetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/data/detention_audit_metrics.json")
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.text();
      })
      .then((text) => {
        const sanitized = text.replace(/\bNaN\b/g, "null").replace(/\bInfinity\b/g, "null");
        setData(JSON.parse(sanitized));
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="v2-loading">
        <div className="v2-loading__spinner" />
        <p className="v2-loading__text">Loading audit metrics…</p>
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div style={{ maxWidth: 800, padding: "2rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 750, marginBottom: "0.5rem" }}>Audit Metrics</h2>
        <InsightCallout icon="ℹ️">
          {data?.error
            ? data.error
            : "No audit metrics data available. Run the metrics computation script: python -m benchassist.dashboard_audit_metrics"}
        </InsightCallout>
      </div>
    );
  }

  const ccrVariants = Object.entries(data.ccr.by_variant_type)
    .sort((a, b) => (a[1].ccr ?? 0) - (b[1].ccr ?? 0));
  const maxCCR = Math.max(...ccrVariants.map(([, v]) => v.ccr ?? 0), 0.01);

  const dirVariants = Object.entries(data.dir.by_variant_type)
    .sort((a, b) => (b[1].adverse_rate ?? 0) - (a[1].adverse_rate ?? 0));
  const maxAdverseRate = Math.max(...dirVariants.map(([, v]) => v.adverse_rate), 0.01);

  const ccrModes = Object.entries(data.ccr.by_prompt_mode);
  const maskingDeltas = Object.entries(data.masking_efficiency.deltas);

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "var(--v2-fs-2xl, 1.5rem)", fontWeight: 750, margin: "0 0 0.3rem", color: "var(--v2-text)" }}>
          Audit Metrics
        </h2>
        <p style={{ fontSize: "var(--v2-fs-sm, 0.85rem)", color: "var(--v2-text-muted)", margin: 0, maxWidth: "72ch" }}>
          Quantitative fairness metrics measuring proxy discrimination across {data.n_total_comparisons} pairwise
          comparisons. These metrics are defined in the project's Audit Metrics Implementation Guide.
        </p>
      </div>

      {/* ── Hero Stat Cards ── */}
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        <div style={STAT_CARD}>
          <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            CCR (Overall)
          </span>
          <span style={{
            fontSize: "2rem", fontWeight: 800, fontVariantNumeric: "tabular-nums",
            color: (data.ccr.overall ?? 0) < 0.8 ? "hsl(0 65% 50%)" : (data.ccr.overall ?? 0) < 0.95 ? "hsl(35 75% 45%)" : "hsl(140 50% 35%)",
          }}>
            {pct(data.ccr.overall)}
          </span>
          <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)" }}>
            {data.ccr.n_consistent}/{data.ccr.n_total} consistent
          </span>
        </div>

        <div style={STAT_CARD}>
          <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            DIR (Overall)
          </span>
          <span style={{
            fontSize: "2rem", fontWeight: 800, fontVariantNumeric: "tabular-nums",
            color: data.dir.overall != null
              ? (Math.abs(data.dir.overall - 1) > 0.2 ? "hsl(0 65% 50%)" : Math.abs(data.dir.overall - 1) > 0.1 ? "hsl(35 75% 45%)" : "hsl(140 50% 35%)")
              : "var(--v2-text-muted)",
          }}>
            {data.dir.overall != null ? fmtNum(data.dir.overall) : "—"}
          </span>
          <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)" }}>
            {data.dir.overall != null ? "1.0 = parity" : "No privileged baseline in data"}
          </span>
        </div>

        <div style={STAT_CARD}>
          <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Comparisons
          </span>
          <span style={{ fontSize: "2rem", fontWeight: 800, fontVariantNumeric: "tabular-nums", color: "var(--v2-text)" }}>
            {data.n_total_comparisons.toLocaleString()}
          </span>
          <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)" }}>
            Pairwise comparisons analysed
          </span>
        </div>

        <div style={STAT_CARD}>
          <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Inconsistency Rate
          </span>
          <span style={{
            fontSize: "2rem", fontWeight: 800, fontVariantNumeric: "tabular-nums",
            color: (1 - (data.ccr.overall ?? 1)) > 0.1 ? "hsl(0 65% 50%)" : "hsl(140 50% 35%)",
          }}>
            {pct(data.ccr.overall != null ? 1 - data.ccr.overall : null)}
          </span>
          <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)" }}>
            Risk assessment changed
          </span>
        </div>
      </div>

      {/* ================================================================ */}
      {/* METRIC 1: Counterfactual Consistency Rate                        */}
      {/* ================================================================ */}
      <section style={SECTION_CARD}>
        <h3 style={{ fontSize: "var(--v2-fs-lg, 1.1rem)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ① Counterfactual Consistency Rate (CCR)
        </h3>
        <p style={{ fontSize: "var(--v2-fs-sm, 0.85rem)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
          Percentage of comparisons where the model's categorical risk assessment remains identical
          when a sensitive proxy variable (e.g., neighborhood or ethnic name) is changed.
          Higher is better — a CCR of 100% means zero demographic influence.
        </p>

        {/* Insight */}
        {data.ccr.overall != null && (
          <InsightCallout>
            Overall consistency is <strong>{pct(data.ccr.overall)}</strong> — the model changes
            its risk assessment in <strong>{pct(1 - data.ccr.overall)}</strong> of cases when only
            demographic proxy cues change.
            {ccrVariants.length > 0 && (
              <> The most sensitive variant is <strong>{variantLabel(ccrVariants[0][0])}</strong> at{" "}
              <strong>{pct(ccrVariants[0][1].ccr)}</strong> consistency.</>
            )}
          </InsightCallout>
        )}

        {/* Bar chart — CCR by variant type */}
        <h4 style={{ fontSize: "var(--v2-fs-base, 0.95rem)", fontWeight: 650, margin: "1rem 0 0.5rem" }}>
          CCR by Variant Type
        </h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginBottom: "1.25rem" }}>
          {ccrVariants.map(([key, v]) => (
            <div key={key} style={{ display: "grid", gridTemplateColumns: "180px 1fr 60px 100px", alignItems: "center", gap: "0.75rem" }}>
              <span style={{ textAlign: "right", fontWeight: 600, fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-secondary)" }}>
                {variantLabel(key)}
              </span>
              <div style={{ height: 14, background: "hsl(220 15% 94%)", borderRadius: 7, overflow: "hidden" }}>
                <div style={{
                  width: barWidth(v.ccr ?? 0, maxCCR),
                  height: "100%",
                  borderRadius: 7,
                  background: (v.ccr ?? 0) > 0.9 ? "hsl(140 50% 45%)" : (v.ccr ?? 0) > 0.7 ? "hsl(35 75% 50%)" : "hsl(0 65% 55%)",
                  transition: "width 0.5s ease",
                }} />
              </div>
              <span style={{ fontWeight: 700, fontSize: "var(--v2-fs-sm)", fontVariantNumeric: "tabular-nums" }}>
                {pct(v.ccr)}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>
                {v.n_consistent}/{v.n_comparisons}
              </span>
            </div>
          ))}
        </div>

        {/* By prompt mode table */}
        {ccrModes.length > 1 && (
          <>
            <h4 style={{ fontSize: "var(--v2-fs-base)", fontWeight: 650, margin: "1rem 0 0.5rem" }}>
              CCR by Prompt Mode
            </h4>
            <div className="v2-output-table-wrap">
              <table className="v2-output-table">
                <thead>
                  <tr>
                    <th>Prompt Mode</th>
                    <th>CCR</th>
                    <th>Comparisons</th>
                    <th>Consistent</th>
                    <th>Changed</th>
                  </tr>
                </thead>
                <tbody>
                  {ccrModes.map(([mode, v]) => (
                    <tr key={mode}>
                      <td className="v2-output-table__field">{variantLabel(mode)}</td>
                      <td style={{ fontWeight: 700 }}>{pct(v.ccr)}</td>
                      <td>{v.n_comparisons}</td>
                      <td>{v.n_consistent}</td>
                      <td style={{ color: v.n_changed > 0 ? "var(--v2-danger, #dc2626)" : undefined }}>{v.n_changed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      {/* ================================================================ */}
      {/* METRIC 2: Disparate Impact Ratio                                 */}
      {/* ================================================================ */}
      <section style={SECTION_CARD}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ② Disparate Impact Ratio (DIR)
        </h3>
        <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
          The ratio of adverse outcomes (dangerousness ≥ 7/10 or escalation) between marginalized proxy cohorts and the
          privileged baseline. A DIR of 1.0 indicates parity; values significantly above 1.0 indicate the model
          is systematically harsher toward the marginalized group.
        </p>

        {/* Insight */}
        {data.dir.overall != null ? (
          <InsightCallout>
            The overall Disparate Impact Ratio is <strong>{fmtNum(data.dir.overall)}</strong>.
            {data.dir.overall > 1.2
              ? " This indicates the model is systematically harsher toward marginalized proxy groups."
              : data.dir.overall > 1.0
              ? " The model shows a mild tendency toward harsher treatment of marginalized groups."
              : " The model shows no clear systematic bias in adverse outcome rates."}
          </InsightCallout>
        ) : (
          <InsightCallout icon="ℹ️">
            DIR cannot be computed as a ratio because the pairwise comparison data does not contain separate
            privileged/control rows. Instead, <strong>Adverse Rate</strong> per variant is shown below —
            this represents the rate at which the model flags or escalates risk for each variant type.
          </InsightCallout>
        )}

        {/* Adverse rate bar chart */}
        <h4 style={{ fontSize: "var(--v2-fs-base)", fontWeight: 650, margin: "1rem 0 0.5rem" }}>
          Adverse Outcome Rate by Variant Type
        </h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginBottom: "1.25rem" }}>
          {dirVariants.map(([key, v]) => (
            <div key={key} style={{ display: "grid", gridTemplateColumns: "180px 1fr 60px 100px", alignItems: "center", gap: "0.75rem" }}>
              <span style={{ textAlign: "right", fontWeight: 600, fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-secondary)" }}>
                {variantLabel(key)}
              </span>
              <div style={{ height: 14, background: "hsl(220 15% 94%)", borderRadius: 7, overflow: "hidden" }}>
                <div style={{
                  width: barWidth(v.adverse_rate, maxAdverseRate),
                  height: "100%",
                  borderRadius: 7,
                  background: v.adverse_rate > 0.5 ? "hsl(0 65% 55%)" : v.adverse_rate > 0.3 ? "hsl(35 75% 50%)" : "hsl(220 55% 55%)",
                  transition: "width 0.5s ease",
                }} />
              </div>
              <span style={{ fontWeight: 700, fontSize: "var(--v2-fs-sm)", fontVariantNumeric: "tabular-nums" }}>
                {pct(v.adverse_rate)}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>
                {v.n_adverse}/{v.n_total}
              </span>
            </div>
          ))}
        </div>

        {/* DIR detail table */}
        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Variant Type</th>
                <th>DIR</th>
                <th>Adverse Rate</th>
                <th>Adverse</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {dirVariants.map(([key, v]) => (
                <tr key={key} className={v.adverse_rate > 0.5 ? "v2-output-table__row--changed" : ""}>
                  <td className="v2-output-table__field">{variantLabel(key)}</td>
                  <td style={{
                    fontWeight: 700,
                    color: v.dir != null && v.dir > 1.2 ? "var(--v2-danger, #dc2626)" : undefined,
                  }}>
                    {v.dir != null ? fmtNum(v.dir) : "—"}
                  </td>
                  <td style={{ fontWeight: 700 }}>{pct(v.adverse_rate)}</td>
                  <td>{v.n_adverse}</td>
                  <td>{v.n_total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* METRIC 3: Masking Efficiency Delta                               */}
      {/* ================================================================ */}
      <section style={SECTION_CARD}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ③ Masking Efficiency Delta (Δ<sub>ME</sub>)
        </h3>
        <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
          Evaluates whether the "Instructional Masking" system prompt effectively reduces bias by comparing
          the DIR of the naive model run against each masked prompt mode. A positive Δ means the masking
          prompt reduced bias; near-zero suggests "audit washing".
        </p>

        {maskingDeltas.length > 0 ? (
          <>
            {maskingDeltas.map(([mode, delta]) => (
              <div key={mode} style={{
                display: "flex", alignItems: "center", gap: "1.5rem", padding: "1rem 1.25rem",
                borderRadius: 10, border: "1px solid var(--v2-border)", marginBottom: "0.75rem",
                background: "var(--v2-surface-raised, hsl(220 20% 98%))",
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: "var(--v2-fs-base)", marginBottom: "0.25rem" }}>
                    {variantLabel(mode)}
                  </div>
                  <div style={{ display: "flex", gap: "1.5rem", fontSize: "var(--v2-fs-sm)" }}>
                    <span>Naive DIR: <strong>{fmtNum(delta.baseline_dir)}</strong></span>
                    <span>→</span>
                    <span>Masked DIR: <strong>{fmtNum(delta.masked_dir)}</strong></span>
                    <span>→</span>
                    <span>
                      Δ: <strong style={{
                        color: (delta.delta ?? 0) > 0.05 ? "hsl(140 50% 35%)" : (delta.delta ?? 0) < -0.05 ? "hsl(0 65% 50%)" : "inherit",
                      }}>
                        {delta.delta != null ? (delta.delta > 0 ? "+" : "") + fmtNum(delta.delta) : "—"}
                      </strong>
                    </span>
                  </div>
                </div>
                <div>{interpretationBadge(delta.interpretation)}</div>
              </div>
            ))}
          </>
        ) : (
          <InsightCallout icon="ℹ️">
            Masking efficiency delta cannot be computed — only one prompt mode (&quot;naive&quot;) is present
            in the data. Run the pipeline with multiple prompt modes (masked) to
            enable this comparison.
          </InsightCallout>
        )}

        {/* Per-mode summary table */}
        {Object.keys(data.masking_efficiency.by_mode).length > 0 && (
          <>
            <h4 style={{ fontSize: "var(--v2-fs-base)", fontWeight: 650, margin: "1rem 0 0.5rem" }}>
              DIR by Prompt Mode
            </h4>
            <div className="v2-output-table-wrap">
              <table className="v2-output-table">
                <thead>
                  <tr>
                    <th>Prompt Mode</th>
                    <th>DIR</th>
                    <th>P(adverse | marginalized)</th>
                    <th>P(adverse | privileged)</th>
                    <th>N marginalized</th>
                    <th>N privileged</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.masking_efficiency.by_mode).map(([mode, v]) => (
                    <tr key={mode} className={mode === "naive" ? "v2-output-table__row--changed" : ""}>
                      <td className="v2-output-table__field">{variantLabel(mode)}</td>
                      <td style={{ fontWeight: 700 }}>{v.dir != null ? fmtNum(v.dir) : "—"}</td>
                      <td>{pct(v.p_marginalized)}</td>
                      <td>{pct(v.p_privileged)}</td>
                      <td>{v.n_marginalized}</td>
                      <td>{v.n_privileged}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      {/* ================================================================ */}
      {/* METRIC 4: Semantic Sentiment Divergence                          */}
      {/* ================================================================ */}
      <section style={SECTION_CARD}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ④ Semantic Sentiment Divergence
        </h3>
        <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
          Measures the qualitative difference in the LLM's text justification between control and variant cases.
          Detects if the model uses a harsher or more punitive semantic tone for marginalized proxies despite
          assigning identical categorical risk scores. Requires NLP dependencies (sentence-transformers, scipy).
        </p>

        {data.semantic_divergence.available ? (
          <div>
            <div style={STAT_CARD}>
              <span style={{ fontSize: "0.85rem", color: "var(--v2-text-muted)" }}>Overall Mean Divergence</span>
              <span style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--v2-info)" }}>
                {fmtNum(data.semantic_divergence.overall_mean_divergence, 4)}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>
                n = {data.semantic_divergence.n_total_comparisons} comparisons
              </span>
            </div>
            {data.semantic_divergence.by_variant_type && Object.keys(data.semantic_divergence.by_variant_type).length > 0 && (
              <div style={{ marginTop: "1rem" }}>
                <h4 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem" }}>By Variant Type</h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {Object.entries(data.semantic_divergence.by_variant_type).map(([vType, stats]) => (
                    <div key={vType} className="v2-badge v2-badge--neutral" style={{ padding: "0.5rem 0.75rem" }}>
                      {variantLabel(vType)}: <strong style={{ color: "var(--v2-info)", marginLeft: "0.25rem" }}>{fmtNum(stats.mean_divergence, 4)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: "0.75rem",
            padding: "2rem", borderRadius: 10, border: "2px dashed var(--v2-border)",
            background: "var(--v2-surface-raised, hsl(220 20% 98%))",
            textAlign: "center",
          }}>
            <span style={{ fontSize: "2rem" }}>🔬</span>
            <strong style={{ fontSize: "var(--v2-fs-base)" }}>NLP Pipeline Required</strong>
            <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", maxWidth: "50ch", margin: 0 }}>
              {data.semantic_divergence.note}
            </p>
            <div style={{
              padding: "0.5rem 1rem", borderRadius: 6, background: "hsl(220 15% 94%)",
              fontFamily: "monospace", fontSize: "0.78rem", color: "var(--v2-text-secondary)",
            }}>
              pip install sentence-transformers scipy
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)", maxWidth: "50ch", margin: 0 }}>
              This metric uses multilingual sentence embeddings to compare the semantic content of control vs.
              variant model reasoning, detecting subtle tonal or framing differences that categorical metrics miss.
            </p>
          </div>
        )}
      </section>

      {/* ================================================================ */}
      {/* METRIC 5: Reasoning Flaws (Identity Leakage & Hallucinations)    */}
      {/* ================================================================ */}
      <section style={SECTION_CARD}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ⑤ Reasoning Flaws
        </h3>
        <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
          Evaluates the frequency of two critical flaws in the model's reasoning: <strong>Illegal Proxy Reasoning</strong> (where the model explicitly references the demographic proxy as justification) and <strong>Hallucinations</strong> (where the model invents unsupported facts to justify higher risk).
        </p>

        {data.reasoning_flaws && (
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
            <div style={STAT_CARD}>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Identity Leakage
              </span>
              <span style={{
                fontSize: "2rem", fontWeight: 800, fontVariantNumeric: "tabular-nums",
                color: (data.reasoning_flaws.identity_leakage_rate_overall ?? 0) > 0.1 ? "hsl(0 65% 50%)" : "hsl(140 50% 35%)",
              }}>
                {pct(data.reasoning_flaws.identity_leakage_rate_overall)}
              </span>
              <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)" }}>
                {data.reasoning_flaws.n_leakage_overall} occurrences
              </span>
            </div>

            <div style={STAT_CARD}>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Hallucinations
              </span>
              <span style={{
                fontSize: "2rem", fontWeight: 800, fontVariantNumeric: "tabular-nums",
                color: (data.reasoning_flaws.hallucination_rate_overall ?? 0) > 0.05 ? "hsl(0 65% 50%)" : "hsl(140 50% 35%)",
              }}>
                {pct(data.reasoning_flaws.hallucination_rate_overall)}
              </span>
              <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)" }}>
                {data.reasoning_flaws.n_hallucination_overall} unsupported claims
              </span>
            </div>
          </div>
        )}

        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Variant Type</th>
                <th>Identity Leakage Rate</th>
                <th>Hallucination Rate</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.reasoning_flaws?.by_variant_type || {}).map(([key, v]) => (
                <tr key={key}>
                  <td className="v2-output-table__field">{variantLabel(key)}</td>
                  <td style={{
                    fontWeight: 700,
                    color: (v.identity_leakage_rate ?? 0) > 0.1 ? "var(--v2-danger, #dc2626)" : undefined,
                  }}>
                    {pct(v.identity_leakage_rate)} <span style={{ fontSize: "0.75rem", fontWeight: "normal", color: "var(--v2-text-muted)" }}>({v.n_leakage})</span>
                  </td>
                  <td style={{
                    fontWeight: 700,
                    color: (v.hallucination_rate ?? 0) > 0.05 ? "var(--v2-danger, #dc2626)" : undefined,
                  }}>
                    {pct(v.hallucination_rate)} <span style={{ fontSize: "0.75rem", fontWeight: "normal", color: "var(--v2-text-muted)" }}>({v.n_hallucination})</span>
                  </td>
                  <td>{v.n_total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Methodology note ── */}
      <div style={{
        fontSize: "0.78rem", color: "var(--v2-text-muted)", padding: "1rem 1.25rem",
        borderRadius: 8, border: "1px solid var(--v2-border)", background: "var(--v2-surface-raised, hsl(220 20% 98%))",
      }}>
        <strong>Methodology Note:</strong> CCR uses <code>detention_framing_bias_flag</code> as the consistency
        indicator. DIR uses <code>dangerousness_escalation_flag</code> and <code>detention_framing_bias_flag</code> to
        determine adverse outcomes. Masking efficiency compares DIR across prompt modes. All metrics are computed
        from {data.n_total_comparisons} pairwise comparisons generated at {new Date(data.generated_at).toLocaleString()}.
      </div>
    </div>
  );
}
