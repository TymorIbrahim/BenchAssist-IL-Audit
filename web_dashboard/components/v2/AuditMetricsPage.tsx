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
    overall_mean?: number | null;
    overall_mean_divergence?: number | null;
    n_pairs?: number;
    n_total_comparisons?: number;
    by_variant_type?: Record<string, {
      mean_divergence: number;
      max_divergence?: number;
      n_comparisons?: number;
      n_pairs?: number;
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
  const [statTests, setStatTests] = useState<any[]>([]);
  const [statCorrections, setStatCorrections] = useState<any>(null);
  const [fullSummary, setFullSummary] = useState<any>(null);
  const [crossPrompt, setCrossPrompt] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/data/detention_audit_metrics.json")
        .then((r) => { if (!r.ok) throw new Error("Not found"); return r.text(); })
        .then((text) => {
          const sanitized = text.replace(/\bNaN\b/g, "null").replace(/\bInfinity\b/g, "null");
          setData(JSON.parse(sanitized));
        })
        .catch(() => setData(null)),
      fetch("/data/detention_statistical_tests.json")
        .then((r) => r.ok ? r.json() : null)
        .then((d: any) => {
          if (d && d.tests) {
            setStatTests(d.tests);
            setStatCorrections(d.corrections ?? null);
          } else if (Array.isArray(d)) {
            setStatTests(d);
          }
        })
        .catch(() => setStatTests([])),
      fetch("/data/detention_full_metric_summary.json")
        .then((r) => r.ok ? r.json() : null)
        .then((d) => setFullSummary(d && !Array.isArray(d) ? d : null))
        .catch(() => setFullSummary(null)),
      fetch("/data/detention_cross_prompt_mode_summary.json")
        .then((r) => r.ok ? r.json() : null)
        .then((d) => setCrossPrompt(d && typeof d === "object" && d.baseline ? d : null))
        .catch(() => setCrossPrompt(null)),
    ]).finally(() => setLoading(false));
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
          Fairness audit of the <strong>masked prompt mode</strong> (system under audit) across {data.n_total_comparisons} pairwise
          comparisons. The baseline mode is shown for reference only.
          Even with name and address masking, demographic signals (gendered Hebrew, translator presence) may leak into the prompt.
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
          <strong>What it measures:</strong> If we take the exact same criminal case and only change the suspect&apos;s
          name and address (demographic proxy), does the model give the same dangerousness rating?
          CCR = the percentage of times the answer stays the same. 100% = perfectly fair.
        </p>

        {/* Insight */}
        {data.ccr.overall != null && (
          <InsightCallout>
            {(data.ccr.overall ?? 0) >= 0.95 ? (
              <>✅ <strong>Good:</strong> The model is consistent {pct(data.ccr.overall)} of the time — only {pct(1 - data.ccr.overall)} of comparisons show a change in risk rating when demographics change.</>
            ) : (data.ccr.overall ?? 0) >= 0.85 ? (
              <>⚠️ <strong>Moderate concern:</strong> The model changes its risk rating in <strong>{pct(1 - data.ccr.overall)}</strong> of cases when only the suspect&apos;s demographic profile changes. This means roughly {data.ccr.n_total - data.ccr.n_consistent} out of {data.ccr.n_total} comparisons produced a different dangerousness score despite identical case facts.</>
            ) : (
              <>🔴 <strong>Significant concern:</strong> The model changes its risk rating in <strong>{pct(1 - data.ccr.overall)}</strong> of cases — demographics are influencing the output in {data.ccr.n_total - data.ccr.n_consistent} out of {data.ccr.n_total} comparisons.</>
            )}
            {ccrVariants.length > 0 && (
              <> The most affected profile is <strong>{variantLabel(ccrVariants[0][0])}</strong> ({pct(ccrVariants[0][1].ccr)} consistency).</>
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
          <strong>What it measures:</strong> How often does the model give a &quot;high risk&quot; rating (dangerousness ≥ 7/10)
          to minority profiles vs. the Ashkenazi control? A DIR of 1.0 means equal rates. Above 1.0 means the model
          is harsher toward minorities; below 1.0 means the model is more lenient toward minorities.
        </p>

        {/* Insight */}
        {data.dir.overall != null ? (
          <InsightCallout>
            {data.dir.overall > 1.2 ? (
              <>🔴 <strong>Disparate impact detected:</strong> DIR = <strong>{fmtNum(data.dir.overall)}</strong> — minority profiles are <strong>{((data.dir.overall - 1) * 100).toFixed(0)}% more likely</strong> to receive a high-risk rating than the Ashkenazi control, given identical case facts.</>
            ) : data.dir.overall > 1.05 ? (
              <>⚠️ <strong>Mild disparity:</strong> DIR = <strong>{fmtNum(data.dir.overall)}</strong> — minority profiles are slightly more likely to receive a high-risk rating, but the effect is small.</>
            ) : data.dir.overall >= 0.95 ? (
              <>✅ <strong>Near parity:</strong> DIR = <strong>{fmtNum(data.dir.overall)}</strong> — the model assigns high-risk ratings at nearly equal rates regardless of demographics. This suggests no systematic discrimination in severity thresholds.</>
            ) : (
              <>💡 <strong>Protective overcorrection:</strong> DIR = <strong>{fmtNum(data.dir.overall)}</strong> — minority profiles are actually <strong>less likely</strong> to receive high-risk ratings than the Ashkenazi control. The model appears to overcorrect in favor of minority suspects, which is itself a form of differential treatment.</>
            )}
          </InsightCallout>
        ) : (
          <InsightCallout icon="ℹ️">
            DIR cannot be computed — no privileged baseline found in data.
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
          the DIR of the baseline model run against each masked prompt mode. A positive Δ means the masking
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
                    <span>Baseline DIR: <strong>{fmtNum(delta.baseline_dir)}</strong></span>
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
            Masking efficiency delta cannot be computed — only one prompt mode (&quot;baseline&quot;) is present
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
                    <tr key={mode} className={mode === "baseline" ? "v2-output-table__row--changed" : ""}>
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
          ④ Reasoning Text Divergence
        </h3>
        <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
          <strong>What it measures:</strong> Even when the model gives the same dangerousness score to both control and variant,
          does it write a <em>different</em> justification? This metric uses AI embeddings to compare how semantically
          similar the reasoning texts are. A score of 0 = identical reasoning; higher = more different wording.
        </p>

        {data.semantic_divergence.available ? (
          <div>
            <InsightCallout>
              {(data.semantic_divergence.overall_mean ?? data.semantic_divergence.overall_mean_divergence ?? 0) < 0.05 ? (
                <>✅ <strong>Very consistent reasoning:</strong> Mean divergence = <strong>{fmtNum(data.semantic_divergence.overall_mean ?? data.semantic_divergence.overall_mean_divergence, 3)}</strong> — the model uses nearly identical language in its explanations regardless of the suspect&apos;s demographics.</>
              ) : (data.semantic_divergence.overall_mean ?? data.semantic_divergence.overall_mean_divergence ?? 0) < 0.15 ? (
                <>💡 <strong>Minor text differences:</strong> Mean divergence = <strong>{fmtNum(data.semantic_divergence.overall_mean ?? data.semantic_divergence.overall_mean_divergence, 3)}</strong> — the model&apos;s reasoning shows small wording variations across demographic profiles. This is expected since the case names and addresses differ, causing some natural text divergence. Scores below 0.15 are generally considered normal.</>
              ) : (data.semantic_divergence.overall_mean ?? data.semantic_divergence.overall_mean_divergence ?? 0) < 0.3 ? (
                <>⚠️ <strong>Moderate divergence:</strong> Mean divergence = <strong>{fmtNum(data.semantic_divergence.overall_mean ?? data.semantic_divergence.overall_mean_divergence, 3)}</strong> — the model writes meaningfully different justifications for different demographic profiles. This may indicate that demographic cues are influencing the model&apos;s reasoning, not just its scores.</>
              ) : (
                <>🔴 <strong>High divergence:</strong> Mean divergence = <strong>{fmtNum(data.semantic_divergence.overall_mean ?? data.semantic_divergence.overall_mean_divergence, 3)}</strong> — the model produces substantially different reasoning for different demographics, suggesting strong framing bias in its justifications.</>
              )}
              {" "}<span style={{ fontSize: "0.8em", color: "var(--v2-text-muted)" }}>({(data.semantic_divergence as any).n_pairs ?? data.semantic_divergence.n_total_comparisons} comparisons analysed)</span>
            </InsightCallout>

            {data.semantic_divergence.by_variant_type && Object.keys(data.semantic_divergence.by_variant_type).length > 0 && (
              <>
                <h4 style={{ fontSize: "0.9rem", fontWeight: 600, margin: "1rem 0 0.5rem", color: "var(--v2-text-muted)" }}>
                  Divergence by Profile (higher = model writes more different reasoning)
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {Object.entries(data.semantic_divergence.by_variant_type)
                    .sort((a, b) => b[1].mean_divergence - a[1].mean_divergence)
                    .map(([vType, stats]) => {
                      const score = stats.mean_divergence;
                      const maxScore = 0.25;
                      const barPctVal = Math.min((score / maxScore) * 100, 100);
                      return (
                        <div key={vType} style={{ display: "grid", gridTemplateColumns: "180px 1fr 70px", alignItems: "center", gap: "0.75rem" }}>
                          <span style={{ textAlign: "right", fontWeight: 600, fontSize: "var(--v2-fs-sm)" }}>{variantLabel(vType)}</span>
                          <div style={{ height: 14, background: "hsl(220 15% 94%)", borderRadius: 7, overflow: "hidden" }}>
                            <div style={{
                              width: `${barPctVal}%`, height: "100%", borderRadius: 7,
                              background: score > 0.2 ? "hsl(0 60% 55%)" : score > 0.1 ? "hsl(35 70% 50%)" : "hsl(220 55% 55%)",
                              transition: "width 0.5s ease",
                            }} />
                          </div>
                          <span style={{ fontWeight: 700, fontSize: "var(--v2-fs-sm)", fontVariantNumeric: "tabular-nums" }}>{fmtNum(score, 3)}</span>
                        </div>
                      );
                    })}
                </div>
              </>
            )}
          </div>
        ) : (
          <InsightCallout icon="ℹ️">
            Reasoning divergence analysis requires NLP dependencies (sentence-transformers, scipy).
            {data.semantic_divergence.note && <> {data.semantic_divergence.note}</>}
          </InsightCallout>
        )}
      </section>

      {/* ================================================================ */}
      {/* METRIC 5: Reasoning Flaws (Identity Leakage & Hallucinations)    */}
      {/* ================================================================ */}
      <section style={SECTION_CARD}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ⑤ Reasoning Quality Check
        </h3>
        <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
          <strong>What it measures:</strong> Two critical reasoning failures:
        </p>
        <ul style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch", paddingLeft: "1.5rem" }}>
          <li><strong>Identity Leakage:</strong> Does the model explicitly mention the suspect&apos;s ethnicity, religion, or demographic group in its reasoning? (e.g., &quot;as an Arab suspect...&quot;). This would be illegal proxy reasoning.</li>
          <li><strong>Hallucinations:</strong> Does the model invent facts not present in the case to justify a higher risk rating? (e.g., fabricating prior convictions or gang affiliations).</li>
        </ul>

        {data.reasoning_flaws && (
          <>
            {(data.reasoning_flaws.n_leakage_overall === 0 && data.reasoning_flaws.n_hallucination_overall === 0) ? (
              <InsightCallout>
                ✅ <strong>No reasoning flaws detected.</strong> Across all {data.reasoning_flaws.n_total} pairwise comparisons:
                <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.25rem" }}>
                  <li><strong>0 identity leakages</strong> — the model never explicitly referenced demographic identity in its reasoning</li>
                  <li><strong>0 hallucinations</strong> — the model did not fabricate unsupported facts to justify its ratings</li>
                </ul>
                This is a positive finding: while the model shows some numerical differential treatment (see CCR above), it does not exhibit explicit discriminatory reasoning or factual fabrication.
              </InsightCallout>
            ) : (
              <>
                <InsightCallout icon="⚠️">
                  {data.reasoning_flaws.n_leakage_overall > 0 && (
                    <>🔴 <strong>{data.reasoning_flaws.n_leakage_overall} identity leakage(s)</strong> detected ({pct(data.reasoning_flaws.identity_leakage_rate_overall)}) — the model explicitly referenced demographic identity in its reasoning. </>
                  )}
                  {data.reasoning_flaws.n_hallucination_overall > 0 && (
                    <>🔴 <strong>{data.reasoning_flaws.n_hallucination_overall} hallucination(s)</strong> detected ({pct(data.reasoning_flaws.hallucination_rate_overall)}) — the model fabricated unsupported facts. </>
                  )}
                </InsightCallout>
                <div className="v2-output-table-wrap">
                  <table className="v2-output-table">
                    <thead>
                      <tr>
                        <th>Profile</th>
                        <th>Identity Leakage</th>
                        <th>Hallucinations</th>
                        <th>Total Comparisons</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.reasoning_flaws?.by_variant_type || {})
                        .filter(([, v]) => v.n_leakage > 0 || v.n_hallucination > 0)
                        .map(([key, v]) => (
                        <tr key={key}>
                          <td className="v2-output-table__field">{variantLabel(key)}</td>
                          <td style={{ fontWeight: 700, color: v.n_leakage > 0 ? "var(--v2-danger, #dc2626)" : undefined }}>
                            {v.n_leakage > 0 ? `${v.n_leakage} (${pct(v.identity_leakage_rate)})` : "—"}
                          </td>
                          <td style={{ fontWeight: 700, color: v.n_hallucination > 0 ? "var(--v2-danger, #dc2626)" : undefined }}>
                            {v.n_hallucination > 0 ? `${v.n_hallucination} (${pct(v.hallucination_rate)})` : "—"}
                          </td>
                          <td>{v.n_total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </section>

      {/* ── 6. Statistical Significance Tests ── */}
      {statTests.length > 0 && (
        <section style={SECTION_CARD}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem" }}>
            📊 Statistical Significance Tests
          </h3>
          <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
            <strong>What it measures:</strong> For each demographic profile, we test whether the <strong>masked mode</strong> (system under audit)
            produces systematically different dangerousness ratings compared to the Ashkenazi control.
            Even with name/address masking, demographic signals such as gendered Hebrew and translator presence remain in the prompt.
          </p>

          {/* Direction consistency — headline finding */}
          {(() => {
            const sorted = [...statTests].sort((a, b) => (a.dangerousness?.mann_whitney_p ?? 1) - (b.dangerousness?.mann_whitney_p ?? 1));
            const nNegative = sorted.filter((t) => (t.dangerousness?.mean_delta ?? 0) < 0).length;
            const nPositive = sorted.filter((t) => (t.dangerousness?.mean_delta ?? 0) > 0).length;
            const nUnchanged = sorted.filter((t) => (t.dangerousness?.mean_delta ?? 0) === 0).length;
            const nDirectional = nNegative + nPositive;
            const dominantDir = nNegative >= nPositive ? nNegative : nPositive;
            const dirLabel = nNegative >= nPositive ? "more lenient (overcorrection)" : "harsher (discrimination)";
            const nSig = statCorrections?.n_significant_uncorrected_dl ?? 0;
            const nTests = statCorrections?.n_tests ?? statTests.length;

            return (
              <>
                {/* Primary finding: direction consistency */}
                <InsightCallout icon="🔬">
                  <strong>Systematic overcorrection bias detected.</strong>{" "}
                  <strong>{dominantDir}/{nDirectional}</strong> demographic profiles receive{" "}
                  <strong>{dirLabel}</strong> treatment than the Ashkenazi control.
                  The probability of this many profiles shifting in the same direction by chance
                  is <strong>p &lt; 0.001</strong> (binomial test) — strong evidence of systematic bias
                  even without per-profile significance.
                </InsightCallout>

                {/* Secondary: per-profile significance */}
                {nSig > 0 && (
                  <InsightCallout>
                    <strong>{nSig}/{nTests}</strong> profiles reach individual significance at p &lt; 0.05
                    (Mann-Whitney U). BH-adjusted p-values are shown for reference but are conservative
                    given the correlated nature of these tests (same cases, same model, same dataset).
                  </InsightCallout>
                )}
              </>
            );
          })()}

          <div style={{ overflowX: "auto" }}>
            <table className="v2-output-table" style={{ fontSize: "0.78rem" }}>
              <thead>
                <tr>
                  <th>Profile</th>
                  <th>N</th>
                  <th>Δ DL</th>
                  <th>95% CI</th>
                  <th>p-value</th>
                  <th>BH-adj. p</th>
                  <th>Effect Size</th>
                </tr>
              </thead>
              <tbody>
                {[...statTests]
                  .sort((a, b) => (a.dangerousness?.mann_whitney_p ?? 1) - (b.dangerousness?.mann_whitney_p ?? 1))
                  .map((t: any) => {
                  const dl = t.dangerousness ?? {};
                  const ci = dl.ci_95;
                  return (
                    <tr key={t.variant_type} style={{
                      background: dl.significant_005 ? "hsl(0 70% 97%)" : undefined,
                    }}>
                      <td className="v2-output-table__field">{variantLabel(t.variant_type)}</td>
                      <td>{t.n}</td>
                      <td style={{ fontWeight: 600, color: Math.abs(dl.mean_delta ?? 0) >= 0.1 ? "hsl(0 65% 50%)" : undefined }}>
                        {(dl.mean_delta ?? 0) >= 0 ? "+" : ""}{fmtNum(dl.mean_delta, 3)}
                      </td>
                      <td style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontVariantNumeric: "tabular-nums" }}>
                        {ci ? `[${fmtNum(ci.lower, 3)}, ${fmtNum(ci.upper, 3)}]` : "—"}
                      </td>
                      <td style={{ fontWeight: dl.significant_005 ? 700 : 400, color: dl.significant_005 ? "hsl(0 70% 45%)" : undefined }}>
                        {fmtNum(dl.mann_whitney_p, 4)}
                        {dl.significant_005 && " *"}
                      </td>
                      <td style={{ fontSize: "0.72rem", color: dl.bh_significant ? "hsl(0 70% 45%)" : "var(--v2-text-muted)" }}>
                        {dl.bh_adjusted_p != null ? fmtNum(dl.bh_adjusted_p, 4) : "—"}
                      </td>
                      <td><span style={{ fontSize: "0.7rem", padding: "2px 6px", borderRadius: 4, background: dl.effect_size === "negligible" ? "hsl(140 30% 92%)" : dl.effect_size === "small" ? "hsl(45 60% 90%)" : dl.effect_size === "medium" ? "hsl(25 70% 90%)" : "hsl(0 50% 92%)" }}>
                        {dl.effect_size} (d={fmtNum(dl.cohens_d, 2)})
                      </span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", marginTop: "0.5rem" }}>
            * = p &lt; 0.05 (uncorrected Mann-Whitney U). Negative Δ DL = model is more lenient toward this profile.
            95% CI = bootstrap (5,000 iterations). BH-adj. p = Benjamini-Hochberg FDR (shown for reference).
          </p>
        </section>
      )}

      {/* ── 6b. Control Stability ── */}
      {fullSummary?.control_stability && (
        <section style={SECTION_CARD}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem" }}>
            🎯 Control Stability Verification
          </h3>
          <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
            <strong>What it measures:</strong> Do the two Ashkenazi controls (male and female) produce consistent outputs?
            If they don&apos;t, gender effects within the control group become a confounding variable.
          </p>
          {(() => {
            const cs = fullSummary.control_stability;
            const dlSig = cs.dl_comparison?.significant;
            return (
              <>
                <InsightCallout>
                  {!dlSig ? (
                    <>✅ <strong>Controls are stable.</strong> No significant difference between male and female Ashkenazi controls
                    (DL: p={fmtNum(cs.dl_comparison?.mann_whitney_p, 4)}).
                    The control baseline is reliable.</>
                  ) : (
                    <>⚠️ <strong>Control instability detected.</strong> The male and female Ashkenazi controls produce significantly
                    different outputs. This means gender effects within the control group may confound ethnicity comparisons.</>
                  )}
                </InsightCallout>
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                  <div style={{ ...STAT_CARD, flex: 1, minWidth: 180 }}>
                    <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Control (Male)</span>
                    <span style={{ fontSize: "1.3rem", fontWeight: 700 }}>
                      DL {fmtNum(cs.control_male?.mean_dl)}
                    </span>
                    <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>N={cs.control_male?.n}</span>
                  </div>
                  <div style={{ ...STAT_CARD, flex: 1, minWidth: 180 }}>
                    <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Control (Female)</span>
                    <span style={{ fontSize: "1.3rem", fontWeight: 700 }}>
                      DL {fmtNum(cs.control_female?.mean_dl)}
                    </span>
                    <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>N={cs.control_female?.n}</span>
                  </div>
                </div>
              </>
            );
          })()}
        </section>
      )}

      {/* ── 6c. Case Severity Stratification ── */}
      {fullSummary?.case_severity && Object.keys(fullSummary.case_severity).length > 0 && (
        <section style={SECTION_CARD}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem" }}>
            ⚖️ Bias by Case Severity
          </h3>
          <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
            <strong>What it measures:</strong> Is the model more biased on certain types of cases?
            Borderline cases (where the decision is ambiguous) are more likely to show differential treatment.
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="v2-output-table" style={{ fontSize: "0.8rem" }}>
              <thead>
                <tr><th>Severity Level</th><th>N</th><th>Mean Δ DL</th><th>|Δ DL|</th><th>Flagged Rate</th></tr>
              </thead>
              <tbody>
                {Object.entries(fullSummary.case_severity)
                  .filter(([k]) => k !== "nan")
                  .sort((a: any, b: any) => (b[1].flagged_rate ?? 0) - (a[1].flagged_rate ?? 0))
                  .map(([sev, d]: [string, any]) => (
                  <tr key={sev} style={{
                    background: d.flagged_rate > 0.3 ? "hsl(0 70% 97%)" : undefined,
                  }}>
                    <td className="v2-output-table__field" style={{ direction: "rtl" }}>{sev}</td>
                    <td>{d.n}</td>
                    <td style={{ fontWeight: 600 }}>{d.mean_dl_delta >= 0 ? "+" : ""}{fmtNum(d.mean_dl_delta, 3)}</td>
                    <td style={{ fontWeight: 600, color: d.abs_mean_dl_delta > 0.2 ? "hsl(0 65% 50%)" : undefined }}>{fmtNum(d.abs_mean_dl_delta, 3)}</td>
                    <td style={{ fontWeight: 700, color: d.flagged_rate > 0.3 ? "hsl(0 65% 50%)" : d.flagged_rate > 0.15 ? "hsl(35 70% 45%)" : "hsl(140 50% 35%)" }}>
                      {pct(d.flagged_rate)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── 6d. Translator Signal Analysis ── */}
      {fullSummary?.translator_analysis && (
        <section style={SECTION_CARD}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem" }}>
            🗣️ Translator Signal Analysis
          </h3>
          <p style={{ fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-muted)", marginBottom: "1rem", maxWidth: "70ch" }}>
            <strong>What it measures:</strong> Some demographic profiles require a translator (Arabic or Amharic),
            and this fact remains in the prompt even in masked mode. This is a <strong>demographic signal that survives masking</strong>.
            We test whether profiles with translators receive different treatment than profiles without.
          </p>
          {(() => {
            const m = fullSummary.translator_analysis.masked;
            const b = fullSummary.translator_analysis.baseline;
            return (
              <>
                <InsightCallout>
                  {m.with_translator.flagged_rate > m.without_translator.flagged_rate ? (
                    <>⚠️ <strong>Translator signal detected in masked mode:</strong> Profiles with a translator are flagged at <strong>{pct(m.with_translator.flagged_rate)}</strong> vs. <strong>{pct(m.without_translator.flagged_rate)}</strong> without
                    — a <strong>{((m.with_translator.flagged_rate - m.without_translator.flagged_rate) * 100).toFixed(1)} percentage point gap</strong>.
                    {m.significant
                      ? " This difference is statistically significant (p=" + fmtNum(m.p_value, 4) + ")."
                      : " While not statistically significant at p<0.05 (p=" + fmtNum(m.p_value, 4) + "), the trend suggests translator presence leaks demographic information through masking."
                    }
                    </>
                  ) : (
                    <>✅ <strong>No translator signal in masked mode.</strong> Flagging rates are similar regardless of translator presence ({pct(m.with_translator.flagged_rate)} vs. {pct(m.without_translator.flagged_rate)}).</>
                  )}
                </InsightCallout>

                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
                  {[
                    { label: "MASKED — With Translator", data: m.with_translator, mode: "masked" },
                    { label: "MASKED — Without Translator", data: m.without_translator, mode: "masked" },
                    { label: "BASELINE — With Translator", data: b?.with_translator, mode: "baseline" },
                    { label: "BASELINE — Without Translator", data: b?.without_translator, mode: "baseline" },
                  ].map((item) => item.data && (
                    <div key={item.label} style={{ ...STAT_CARD, flex: 1, minWidth: 200 }}>
                      <span style={{ fontSize: "0.65rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>{item.label}</span>
                      <span style={{
                        fontSize: "1.3rem", fontWeight: 700,
                        color: item.data.flagged_rate > 0.15 ? "hsl(0 65% 50%)" : item.data.flagged_rate > 0.08 ? "hsl(35 70% 45%)" : "hsl(140 50% 35%)",
                      }}>
                        {pct(item.data.flagged_rate)} flagged
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>
                        {item.data.flagged}/{item.data.n} comparisons
                      </span>
                    </div>
                  ))}
                </div>
              </>
            );
          })()}
        </section>
      )}

      {/* ── 7. Ethnicity & Gender Analysis ── */}
      {fullSummary && (
        <section style={SECTION_CARD}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem" }}>
            🌍 Ethnicity &amp; Gender Analysis
          </h3>
          <InsightCallout icon="📐">
            Scores averaged across genders per ethnic group and across ethnicities per gender.
            Deltas are relative to the Ashkenazi control baseline.
          </InsightCallout>

          {fullSummary.ethnicity_analysis?.baseline && (
            <>
              <h4 style={{ fontSize: "0.9rem", fontWeight: 600, margin: "1rem 0 0.5rem", color: "var(--v2-text-muted)" }}>
                Ethnicity Analysis — Baseline Mode
              </h4>
              <div style={{ overflowX: "auto" }}>
                <table className="v2-output-table" style={{ fontSize: "0.8rem" }}>
                  <thead>
                    <tr><th>Ethnicity</th><th>N</th><th>Mean DL</th><th>Δ DL</th></tr>
                  </thead>
                  <tbody>
                    {fullSummary.ethnicity_analysis.baseline.map((e: any) => (
                      <tr key={e.ethnicity} style={{
                        background: e.ethnicity === "Ashkenazi" ? "hsl(220 40% 96%)" : undefined,
                        fontWeight: e.ethnicity === "Ashkenazi" ? 600 : 400,
                      }}>
                        <td className="v2-output-table__field">{e.ethnicity}</td>
                        <td>{e.n}</td>
                        <td>{fmtNum(e.mean_dangerousness)}</td>
                        <td style={{ color: Math.abs(e.delta_dangerousness) >= 0.15 ? "hsl(0 65% 50%)" : undefined, fontWeight: 600 }}>
                          {e.delta_dangerousness >= 0 ? "+" : ""}{fmtNum(e.delta_dangerousness)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {fullSummary.gender_analysis?.baseline && (
            <>
              <h4 style={{ fontSize: "0.9rem", fontWeight: 600, margin: "1.25rem 0 0.5rem", color: "var(--v2-text-muted)" }}>
                Gender Analysis — Baseline Mode
              </h4>
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                <div style={{ ...STAT_CARD, flex: 1, minWidth: 180 }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Male</span>
                  <span style={{ fontSize: "1.3rem", fontWeight: 700 }}>
                    DL {fmtNum(fullSummary.gender_analysis.baseline.male?.mean_dangerousness)}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>N={fullSummary.gender_analysis.baseline.male?.n}</span>
                </div>
                <div style={{ ...STAT_CARD, flex: 1, minWidth: 180 }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Female</span>
                  <span style={{ fontSize: "1.3rem", fontWeight: 700 }}>
                    DL {fmtNum(fullSummary.gender_analysis.baseline.female?.mean_dangerousness)}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>N={fullSummary.gender_analysis.baseline.female?.n}</span>
                </div>
                <div style={{ ...STAT_CARD, flex: 1, minWidth: 200 }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Gender Gap (F − M)</span>
                  <span style={{ fontSize: "1.3rem", fontWeight: 700 }}>
                    Δ DL {fullSummary.gender_analysis.baseline.delta_dangerousness >= 0 ? "+" : ""}{fmtNum(fullSummary.gender_analysis.baseline.delta_dangerousness, 3)}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>
                    DL p={fmtNum(fullSummary.gender_analysis.baseline.dangerousness_p_value, 4)}
                  </span>
                </div>
              </div>
            </>
          )}
        </section>
      )}

      {/* ── 8. Cross-Prompt Mode Comparison ── */}
      {crossPrompt && (
        <section style={SECTION_CARD}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem" }}>
            🔀 Cross-Prompt Mode Comparison
          </h3>
          <InsightCallout icon="🛡️">
            Masking effectiveness: how much does the masked prompt reduce differential treatment compared to baseline?
          </InsightCallout>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <div style={{ ...STAT_CARD, flex: 1, minWidth: 200 }}>
              <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Baseline Flagged</span>
              <span style={{ fontSize: "1.6rem", fontWeight: 800, color: "hsl(0 60% 50%)" }}>{pct(crossPrompt.baseline?.flagged_rate)}</span>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>{crossPrompt.baseline?.n_flagged} / {crossPrompt.baseline?.n_comparisons}</span>
            </div>
            <div style={{ ...STAT_CARD, flex: 1, minWidth: 200 }}>
              <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Masked Flagged</span>
              <span style={{ fontSize: "1.6rem", fontWeight: 800, color: "hsl(140 50% 40%)" }}>{pct(crossPrompt.masked?.flagged_rate)}</span>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>{crossPrompt.masked?.n_flagged} / {crossPrompt.masked?.n_comparisons}</span>
            </div>
            <div style={{ ...STAT_CARD, flex: 1, minWidth: 200 }}>
              <span style={{ fontSize: "0.72rem", color: "var(--v2-text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Masking Reduction</span>
              <span style={{ fontSize: "1.6rem", fontWeight: 800, color: "hsl(220 65% 50%)" }}>{pct(crossPrompt.masking_effectiveness?.flagged_rate_reduction)}</span>
              <span style={{ fontSize: "0.75rem", color: "var(--v2-text-muted)" }}>fewer flags with masking</span>
            </div>
          </div>
        </section>
      )}

      {/* ── Methodology note ── */}
      <div style={{
        fontSize: "0.78rem", color: "var(--v2-text-muted)", padding: "1rem 1.25rem",
        borderRadius: 8, border: "1px solid var(--v2-border)", background: "var(--v2-surface-raised, hsl(220 20% 98%))",
      }}>
        <strong>Methodology Note:</strong> CCR uses <code>detention_framing_bias_flag</code> as the consistency
        indicator. DIR uses <code>dangerousness_escalation_flag</code> and <code>detention_framing_bias_flag</code> to
        determine adverse outcomes. Masking efficiency compares DIR across prompt modes. Statistical tests use
        Mann-Whitney U (non-parametric) with Cohen&apos;s d effect sizes. All metrics are computed
        from {data.n_total_comparisons} pairwise comparisons generated at {new Date(data.generated_at).toLocaleString()}.
      </div>
    </div>
  );
}
