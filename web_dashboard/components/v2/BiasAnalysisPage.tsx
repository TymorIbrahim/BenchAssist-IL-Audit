"use client";

import { useEffect, useState } from "react";
import type { DashboardTab } from "@/lib/v2/types";



// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

interface VariantTypeRow {
  variant_label: string;
  n_comparisons: number;
  n_flagged: number;
  flag_rate: number;
  escalation_count: number;
  escalation_rate: number;
  deescalation_count: number;
  deescalation_rate: number;
  recommendation_change_count: number;
  recommendation_change_rate: number;
  mean_risk_delta: number;
}

interface PromptRow {
  n_comparisons: number;
  n_flagged: number;
  flag_rate: number;
  escalation_count: number;
  escalation_rate: number;
  recommendation_change_count: number;
  recommendation_change_rate: number;
  reduction_vs_baseline: number;
}

interface SeverityRow {
  n_comparisons: number;
  n_flagged: number;
  flag_rate: number;
  escalation_count: number;
  escalation_rate: number;
  case_ids?: string[];
}

interface ConfidenceRow {
  variant_label: string;
  n: number;
  mean_delta: number;
  dropped_count: number;
  increased_count: number;
  unchanged_count: number;
}

interface AsymmetryRow {
  variant_label: string;
  n_escalations: number;
  n_deescalations: number;
  n_rec_more_punitive: number;
  n_rec_less_punitive: number;
  net_risk_delta: number;
  direction: string;
}

interface BiasAnalysis {
  variant_type_analysis: Record<string, VariantTypeRow>;
  prompt_effectiveness: Record<string, PromptRow>;
  severity_analysis: Record<string, SeverityRow>;
  offense_analysis: Record<string, SeverityRow>;
  confidence_analysis: {
    n_pairs_with_confidence: number;
    mean_control_confidence: number | null;
    mean_variant_confidence: number | null;
    mean_confidence_delta: number | null;
    confidence_dropped_count: number;
    confidence_increased_count: number;
    confidence_unchanged_count: number;
    by_variant_type: Record<string, ConfidenceRow>;
  };
  asymmetry_analysis: Record<string, AsymmetryRow>;
  cross_tab_variant_mode: Record<string, Record<string, { n: number; flagged: number; flag_rate: number }>>;
  totals: { n_comparisons: number; n_flagged: number; overall_flag_rate: number };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(val: number): string {
  return (val * 100).toFixed(1) + "%";
}

function barWidth(rate: number, max: number): string {
  if (!max) return "0%";
  return ((rate / max) * 100).toFixed(1) + "%";
}

function directionBadge(dir: string): JSX.Element {
  const colors: Record<string, { bg: string; fg: string }> = {
    "consistently more punitive": { bg: "hsl(0 75% 92%)", fg: "hsl(0 70% 40%)" },
    "consistently more lenient": { bg: "hsl(140 50% 90%)", fg: "hsl(140 50% 30%)" },
    "mixed / no clear direction": { bg: "hsl(45 80% 90%)", fg: "hsl(35 70% 35%)" },
    "no changes detected": { bg: "hsl(220 15% 94%)", fg: "hsl(220 10% 55%)" },
  };
  const c = colors[dir] ?? colors["no changes detected"];
  return (
    <span style={{
      display: "inline-block", padding: "0.2rem 0.6rem", borderRadius: "999px",
      fontSize: "0.75rem", fontWeight: 650, background: c.bg, color: c.fg,
    }}>
      {dir}
    </span>
  );
}

const PROMPT_LABELS: Record<string, string> = {
  baseline: "Baseline",
  fairness_aware: "Fairness-Aware",
  demographic_blind: "Demographic-Blind",
};

const SEV_ORDER = ["Low", "Low-Medium", "Medium", "Medium-High", "High"];

// ---------------------------------------------------------------------------
// Insight callout
// ---------------------------------------------------------------------------

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

function InsightCallout({ children }: { children: React.ReactNode }) {
  return (
    <div style={CALLOUT_STYLE}>
      <span style={{ fontSize: "1.1rem", lineHeight: 1.4, flexShrink: 0 }} aria-hidden>💡</span>
      <span style={{ color: "hsl(220 30% 25%)" }}>{children}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface BiasAnalysisPageProps {
  onNavigate?: (tab: DashboardTab) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BiasAnalysisPage({ onNavigate }: BiasAnalysisPageProps) {
  const [data, setData] = useState<BiasAnalysis | null>(null);

  useEffect(() => {
    fetch("/data/detention_bias_analysis.json")
      .then((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data) {
    return (
      <div className="v2-loading">
        <div className="v2-loading__spinner" />
        <p className="v2-loading__text">Loading bias analysis…</p>
      </div>
    );
  }

  const vtypes = Object.entries(data.variant_type_analysis);
  const maxFlagRate = Math.max(...vtypes.map(([, v]) => v.flag_rate), 0.01);
  const modes = Object.entries(data.prompt_effectiveness);
  const severities = Object.entries(data.severity_analysis)
    .sort((a, b) => {
      const ai = SEV_ORDER.indexOf(a[0]);
      const bi = SEV_ORDER.indexOf(b[0]);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
  const maxSevRate = Math.max(...severities.map(([, v]) => v.flag_rate), 0.01);
  const offenses = Object.entries(data.offense_analysis)
    .sort((a, b) => b[1].flag_rate - a[1].flag_rate);
  const maxOffRate = Math.max(...offenses.map(([, v]) => v.flag_rate), 0.01);
  const conf = data.confidence_analysis;
  const asymmetry = Object.entries(data.asymmetry_analysis);
  const crossTab = data.cross_tab_variant_mode;
  const modeKeys = modes.map(([k]) => k).sort();

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "var(--v2-fs-2xl, 1.5rem)", fontWeight: 750, margin: "0 0 0.3rem", color: "var(--v2-text)" }}>
          Bias Analysis
        </h2>
        <p style={{ fontSize: "var(--v2-fs-sm, 0.85rem)", color: "var(--v2-text-muted)", margin: 0, maxWidth: "72ch" }}>
          Deep-dive into bias patterns across demographic groups, prompt strategies, offense types, and model confidence.
          All analyses are based on {data.totals.n_comparisons} pairwise comparisons ({data.totals.n_flagged} flagged, {pct(data.totals.overall_flag_rate)} overall flag rate).
        </p>
      </div>

      {/* ================================================================ */}
      {/* ANALYSIS 1: Flag rates by demographic group                      */}
      {/* ================================================================ */}
      <section className="section-card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "var(--v2-fs-lg, 1.1rem)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ① Bias by Demographic Group
        </h3>
        <p className="muted" style={{ fontSize: "var(--v2-fs-sm)", marginBottom: "1rem" }}>
          Which demographic proxy triggers the most output changes?
        </p>

        {/* Insight callout */}
        {(() => {
          const sorted = [...vtypes].sort((a, b) => b[1].flag_rate - a[1].flag_rate);
          const highest = sorted[0];
          const lowest = sorted[sorted.length - 1];
          if (!highest || !lowest) return null;
          return (
            <InsightCallout>
              <strong>{highest[1].variant_label}</strong> has the highest flag rate at{" "}
              <strong>{pct(highest[1].flag_rate)}</strong>, with{" "}
              {highest[1].escalation_count} risk escalation{highest[1].escalation_count !== 1 ? "s" : ""} and{" "}
              {highest[1].deescalation_count} de-escalation{highest[1].deescalation_count !== 1 ? "s" : ""}.{" "}
              <strong>{lowest[1].variant_label}</strong> shows the least bias at{" "}
              <strong>{pct(lowest[1].flag_rate)}</strong>.
            </InsightCallout>
          );
        })()}

        {/* Bar chart */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginBottom: "1.25rem" }}>
          {vtypes
            .sort((a, b) => b[1].flag_rate - a[1].flag_rate)
            .map(([key, v]) => (
              <div key={key} style={{ display: "grid", gridTemplateColumns: "180px 1fr 60px", alignItems: "center", gap: "0.75rem" }}>
                <span style={{ textAlign: "right", fontWeight: 600, fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-secondary)" }}>
                  {v.variant_label}
                </span>
                <div style={{ height: 14, background: "hsl(220 15% 94%)", borderRadius: 7, overflow: "hidden" }}>
                  <div style={{
                    width: barWidth(v.flag_rate, maxFlagRate),
                    height: "100%",
                    borderRadius: 7,
                    background: v.flag_rate > 0.2 ? "hsl(0 65% 55%)" : v.flag_rate > 0.15 ? "hsl(35 75% 50%)" : "hsl(220 55% 55%)",
                    transition: "width 0.5s ease",
                  }} />
                </div>
                <span style={{ fontWeight: 700, fontSize: "var(--v2-fs-sm)", fontVariantNumeric: "tabular-nums" }}>
                  {pct(v.flag_rate)}
                </span>
              </div>
            ))}
        </div>

        {/* Detail table */}
        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Demographic Proxy</th>
                <th>Comparisons</th>
                <th>Flagged</th>
                <th>Flag Rate</th>
                <th>Risk ↑</th>
                <th>Risk ↓</th>
                <th>Rec. Changed</th>
                <th>Avg Risk Δ</th>
              </tr>
            </thead>
            <tbody>
              {vtypes
                .sort((a, b) => b[1].flag_rate - a[1].flag_rate)
                .map(([key, v]) => (
                  <tr key={key}>
                    <td className="v2-output-table__field">{v.variant_label}</td>
                    <td>{v.n_comparisons}</td>
                    <td style={{ fontWeight: 700 }}>{v.n_flagged}</td>
                    <td style={{ fontWeight: 700, color: v.flag_rate > 0.2 ? "var(--v2-danger, #dc2626)" : undefined }}>{pct(v.flag_rate)}</td>
                    <td>{v.escalation_count} ({pct(v.escalation_rate)})</td>
                    <td>{v.deescalation_count} ({pct(v.deescalation_rate)})</td>
                    <td>{v.recommendation_change_count} ({pct(v.recommendation_change_rate)})</td>
                    <td style={{ fontFamily: "monospace" }}>{v.mean_risk_delta > 0 ? "+" : ""}{v.mean_risk_delta.toFixed(3)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* ANALYSIS 2: Prompt effectiveness                                 */}
      {/* ================================================================ */}
      <section className="section-card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ② Does Prompt Mitigation Reduce Bias?
        </h3>
        <p className="muted" style={{ fontSize: "var(--v2-fs-sm)", marginBottom: "1rem" }}>
          Comparing flag rates across prompt strategies. A negative reduction means the prompt <em>increased</em> bias.
        </p>

        {/* Insight callout */}
        {(() => {
          const baseline = data.prompt_effectiveness["baseline"];
          const fairness = data.prompt_effectiveness["fairness_aware"];
          const blind = data.prompt_effectiveness["demographic_blind"];
          if (!baseline) return null;
          const parts: string[] = [];
          if (fairness) {
            parts.push(
              `The fairness-aware prompt reduced bias flags by ${pct(Math.abs(fairness.reduction_vs_baseline))} compared to baseline (from ${pct(baseline.flag_rate)} to ${pct(fairness.flag_rate)}).`
            );
          }
          if (blind) {
            parts.push(
              `Demographic-blind showed ${blind.reduction_vs_baseline > 0 ? "a" : "only a"} ${pct(Math.abs(blind.reduction_vs_baseline))} ${blind.reduction_vs_baseline >= 0 ? "reduction" : "increase"}.`
            );
          }
          if (!parts.length) return null;
          return <InsightCallout>{parts.join(" ")}</InsightCallout>;
        })()}

        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Prompt Mode</th>
                <th>Comparisons</th>
                <th>Flagged</th>
                <th>Flag Rate</th>
                <th>Risk ↑</th>
                <th>Rec. Changed</th>
                <th>Reduction vs Baseline</th>
              </tr>
            </thead>
            <tbody>
              {modes.map(([mode, v]) => (
                <tr key={mode} className={mode === "baseline" ? "v2-output-table__row--changed" : ""}>
                  <td className="v2-output-table__field">{PROMPT_LABELS[mode] ?? mode}</td>
                  <td>{v.n_comparisons}</td>
                  <td style={{ fontWeight: 700 }}>{v.n_flagged}</td>
                  <td style={{ fontWeight: 700 }}>{pct(v.flag_rate)}</td>
                  <td>{v.escalation_count} ({pct(v.escalation_rate)})</td>
                  <td>{v.recommendation_change_count} ({pct(v.recommendation_change_rate)})</td>
                  <td>
                    {mode === "baseline" ? (
                      <span style={{ color: "var(--v2-text-muted)" }}>— (reference)</span>
                    ) : (
                      <span style={{
                        fontWeight: 700,
                        color: v.reduction_vs_baseline > 0 ? "hsl(140 50% 35%)" : v.reduction_vs_baseline < 0 ? "var(--v2-danger)" : undefined,
                      }}>
                        {v.reduction_vs_baseline > 0 ? "↓ " : v.reduction_vs_baseline < 0 ? "↑ " : ""}{pct(Math.abs(v.reduction_vs_baseline))}
                        {v.reduction_vs_baseline > 0 ? " fewer flags" : v.reduction_vs_baseline < 0 ? " more flags" : " (same)"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Cross-tab heatmap */}
        <h4 style={{ fontSize: "var(--v2-fs-base)", fontWeight: 650, margin: "1.25rem 0 0.5rem" }}>
          Flag Rate: Variant Type × Prompt Mode
        </h4>
        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Variant</th>
                {modeKeys.map((m) => <th key={m}>{PROMPT_LABELS[m] ?? m}</th>)}
              </tr>
            </thead>
            <tbody>
              {Object.entries(crossTab).map(([vtype, modes]) => (
                <tr key={vtype}>
                  <td className="v2-output-table__field">{vtype.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</td>
                  {modeKeys.map((m) => {
                    const cell = modes[m];
                    if (!cell) return <td key={m}>—</td>;
                    const rate = cell.flag_rate;
                    const bg = rate > 0.25 ? "hsl(0 75% 92%)" : rate > 0.15 ? "hsl(45 80% 92%)" : rate > 0 ? "hsl(140 40% 92%)" : undefined;
                    return (
                      <td
                        key={m}
                        style={{
                          background: bg,
                          fontWeight: rate > 0.2 ? 700 : 500,
                          fontVariantNumeric: "tabular-nums",
                          cursor: onNavigate ? "pointer" : undefined,
                        }}
                        title={onNavigate ? "Click to explore these cases" : undefined}
                        onClick={onNavigate ? () => onNavigate("case-explorer") : undefined}
                      >
                        {pct(rate)} <span style={{ fontSize: "0.7rem", color: "var(--v2-text-muted)" }}>({cell.flagged}/{cell.n})</span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* ANALYSIS 3: Bias × severity                                      */}
      {/* ================================================================ */}
      <section className="section-card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ③ Bias by Offense Severity
        </h3>
        <p className="muted" style={{ fontSize: "var(--v2-fs-sm)", marginBottom: "1rem" }}>
          Are ambiguous, medium-severity cases more susceptible to demographic bias?
        </p>

        {/* Insight callout */}
        {(() => {
          const sorted = [...severities].sort((a, b) => b[1].flag_rate - a[1].flag_rate);
          const highest = sorted[0];
          const secondHighest = sorted.length > 1 ? sorted.find(([, v]) => v.flag_rate < highest[1].flag_rate) : null;
          if (!highest) return null;
          let text = `${highest[0]} severity cases are most susceptible to bias at ${pct(highest[1].flag_rate)} flag rate`;
          if (secondHighest && secondHighest[1].flag_rate > 0) {
            const ratio = (highest[1].flag_rate / secondHighest[1].flag_rate).toFixed(1);
            text += ` — ${ratio}× higher than ${secondHighest[0]} cases at ${pct(secondHighest[1].flag_rate)}`;
          }
          text += ".";
          return <InsightCallout>{text}</InsightCallout>;
        })()}

        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginBottom: "1.25rem" }}>
          {severities.map(([sev, v]) => (
            <div key={sev} style={{ display: "grid", gridTemplateColumns: "140px 1fr 60px", alignItems: "center", gap: "0.75rem" }}>
              <span style={{ textAlign: "right", fontWeight: 600, fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-secondary)" }}>
                {sev}
              </span>
              <div style={{ height: 14, background: "hsl(220 15% 94%)", borderRadius: 7, overflow: "hidden" }}>
                <div style={{
                  width: barWidth(v.flag_rate, maxSevRate),
                  height: "100%", borderRadius: 7,
                  background: v.flag_rate > 0.25 ? "hsl(0 65% 55%)" : v.flag_rate > 0.15 ? "hsl(35 75% 50%)" : "hsl(220 55% 55%)",
                  transition: "width 0.5s ease",
                }} />
              </div>
              <span style={{ fontWeight: 700, fontSize: "var(--v2-fs-sm)", fontVariantNumeric: "tabular-nums" }}>
                {pct(v.flag_rate)}
              </span>
            </div>
          ))}
        </div>

        <h4 style={{ fontSize: "var(--v2-fs-base)", fontWeight: 650, margin: "1rem 0 0.5rem" }}>
          By Specific Offense Type
        </h4>
        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Offense Type</th>
                <th>Comparisons</th>
                <th>Flagged</th>
                <th>Flag Rate</th>
                <th style={{ width: "30%" }}>Visual</th>
              </tr>
            </thead>
            <tbody>
              {offenses.map(([off, v]) => (
                <tr key={off} className={v.flag_rate > 0.25 ? "v2-output-table__row--changed" : ""}>
                  <td className="v2-output-table__field" style={{ whiteSpace: "normal", maxWidth: 250 }}>{off}</td>
                  <td>{v.n_comparisons}</td>
                  <td style={{ fontWeight: 700 }}>{v.n_flagged}</td>
                  <td style={{ fontWeight: 700 }}>{pct(v.flag_rate)}</td>
                  <td>
                    <div style={{ height: 10, background: "hsl(220 15% 94%)", borderRadius: 5, overflow: "hidden" }}>
                      <div style={{
                        width: barWidth(v.flag_rate, maxOffRate),
                        height: "100%", borderRadius: 5,
                        background: v.flag_rate > 0.25 ? "hsl(0 65% 55%)" : "hsl(220 55% 55%)",
                        transition: "width 0.5s ease",
                      }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* ANALYSIS 4: Confidence                                           */}
      {/* ================================================================ */}
      <section className="section-card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ④ Confidence Analysis
        </h3>
        <p className="muted" style={{ fontSize: "var(--v2-fs-sm)", marginBottom: "1rem" }}>
          Does the model become less confident when demographic cues change? A confidence drop may indicate the model &quot;notices&quot; the shift.
        </p>

        {/* Insight callout */}
        {(() => {
          const delta = conf.mean_confidence_delta;
          if (delta === null) return null;
          const absDelta = Math.abs(delta).toFixed(4);
          const isNearlyConstant = Math.abs(delta) < 0.05;
          return (
            <InsightCallout>
              {isNearlyConstant
                ? `Confidence is nearly constant (mean Δ = ${delta > 0 ? "+" : ""}${absDelta}). The model does not meaningfully adjust its confidence when demographic cues change.`
                : `The model shows a ${delta < 0 ? "decrease" : "increase"} in confidence (mean Δ = ${delta > 0 ? "+" : ""}${absDelta}) when demographic cues are altered, suggesting sensitivity to demographic information.`}
            </InsightCallout>
          );
        })()}

        {/* Summary stat cards */}
        <div className="v2-stat-grid" style={{ marginBottom: "1rem" }}>
          <div className="v2-stat-card">
            <span className="v2-stat-card__label">Mean Control Confidence</span>
            <span className="v2-stat-card__value">{conf.mean_control_confidence?.toFixed(3) ?? "N/A"}</span>
          </div>
          <div className="v2-stat-card">
            <span className="v2-stat-card__label">Mean Variant Confidence</span>
            <span className="v2-stat-card__value">{conf.mean_variant_confidence?.toFixed(3) ?? "N/A"}</span>
          </div>
          <div className={`v2-stat-card${(conf.mean_confidence_delta ?? 0) < -0.01 ? " v2-stat-card--warning" : ""}`}>
            <span className="v2-stat-card__label">Mean Δ (variant − control)</span>
            <span className="v2-stat-card__value">
              {conf.mean_confidence_delta !== null ? (conf.mean_confidence_delta > 0 ? "+" : "") + conf.mean_confidence_delta.toFixed(4) : "N/A"}
            </span>
          </div>
          <div className="v2-stat-card">
            <span className="v2-stat-card__label">Dropped / Same / Increased</span>
            <span className="v2-stat-card__value" style={{ fontSize: "var(--v2-fs-lg)" }}>
              {conf.confidence_dropped_count} / {conf.confidence_unchanged_count} / {conf.confidence_increased_count}
            </span>
          </div>
        </div>

        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Variant Type</th>
                <th>Pairs</th>
                <th>Mean Δ</th>
                <th>Dropped</th>
                <th>Unchanged</th>
                <th>Increased</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(conf.by_variant_type).map(([key, v]) => (
                <tr key={key} className={v.mean_delta < -0.01 ? "v2-output-table__row--changed" : ""}>
                  <td className="v2-output-table__field">{v.variant_label}</td>
                  <td>{v.n}</td>
                  <td style={{
                    fontWeight: 700, fontFamily: "monospace",
                    color: v.mean_delta < -0.01 ? "var(--v2-danger)" : v.mean_delta > 0.01 ? "hsl(140 50% 35%)" : undefined,
                  }}>
                    {v.mean_delta > 0 ? "+" : ""}{v.mean_delta.toFixed(4)}
                  </td>
                  <td>{v.dropped_count}</td>
                  <td>{v.unchanged_count}</td>
                  <td>{v.increased_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* ANALYSIS 5: Asymmetry                                            */}
      {/* ================================================================ */}
      <section className="section-card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "var(--v2-fs-lg)", fontWeight: 700, margin: "0 0 0.35rem" }}>
          ⑤ Directional Asymmetry
        </h3>
        <p className="muted" style={{ fontSize: "var(--v2-fs-sm)", marginBottom: "1rem" }}>
          When the model changes its output, is it consistently more punitive toward one demographic group — or does it shift randomly?
        </p>

        {/* Insight callout */}
        {(() => {
          const punitive = asymmetry.filter(([, v]) => v.direction === "consistently more punitive");
          if (!punitive.length) {
            const mixed = asymmetry.filter(([, v]) => v.direction === "mixed / no clear direction");
            if (mixed.length) {
              return (
                <InsightCallout>
                  No variant shows a consistently punitive direction. {mixed.length} variant{mixed.length !== 1 ? "s show" : " shows"} mixed directionality, suggesting no systematic bias in risk adjustment direction.
                </InsightCallout>
              );
            }
            return null;
          }
          const parts = punitive.map(([, v]) => {
            return `${v.variant_label} shows consistent directional bias: ${v.n_escalations} escalation${v.n_escalations !== 1 ? "s" : ""} vs ${v.n_deescalations} de-escalation${v.n_deescalations !== 1 ? "s" : ""} (net risk delta: ${v.net_risk_delta > 0 ? "+" : ""}${v.net_risk_delta})`;
          });
          return (
            <InsightCallout>
              <span dangerouslySetInnerHTML={{ __html: parts.map(p => `<strong>${p.split(" shows")[0]}</strong> shows${p.split(" shows")[1]}`).join(". ") + ". This suggests the model systematically increases risk assessments for these demographic groups." }} />
            </InsightCallout>
          );
        })()}

        <div className="v2-output-table-wrap">
          <table className="v2-output-table">
            <thead>
              <tr>
                <th>Variant Type</th>
                <th>Risk ↑</th>
                <th>Risk ↓</th>
                <th>Rec. More Punitive</th>
                <th>Rec. Less Punitive</th>
                <th>Net Risk Δ</th>
                <th>Direction</th>
              </tr>
            </thead>
            <tbody>
              {asymmetry.map(([key, v]) => (
                <tr key={key}>
                  <td className="v2-output-table__field">{v.variant_label}</td>
                  <td style={{ fontWeight: v.n_escalations > 0 ? 700 : 400, color: v.n_escalations > 0 ? "var(--v2-danger)" : undefined }}>
                    {v.n_escalations}
                  </td>
                  <td style={{ fontWeight: v.n_deescalations > 0 ? 700 : 400, color: v.n_deescalations > 0 ? "hsl(140 50% 35%)" : undefined }}>
                    {v.n_deescalations}
                  </td>
                  <td>{v.n_rec_more_punitive}</td>
                  <td>{v.n_rec_less_punitive}</td>
                  <td style={{ fontFamily: "monospace", fontWeight: 700 }}>
                    {v.net_risk_delta > 0 ? "+" : ""}{v.net_risk_delta}
                  </td>
                  <td>{directionBadge(v.direction)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
