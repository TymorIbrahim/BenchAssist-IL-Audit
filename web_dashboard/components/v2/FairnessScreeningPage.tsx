"use client";

import "../../app/fairness.css";

import type React from "react";
import { useState, useMemo } from "react";
import { IconUser, IconWarning, IconScale, IconChart } from "@/components/v2/Icons";
import type { GroupSummary } from "@/lib/v2/types";
import type { DashboardBundle } from "@/lib/v2/dataUtils";
import {
  formatRate,
  formatCount,
  formatVariantLabel,
} from "@/lib/v2/dataUtils";
import { StatCard } from "./StatCard";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function pct(rate: number): string { return `${(rate * 100).toFixed(1)}%`; }

function rateColor(rate: number): string {
  if (rate > 0.15) return "var(--fair-red, #dc2626)";
  if (rate > 0.10) return "var(--fair-orange, #d97706)";
  if (rate > 0.05) return "var(--fair-yellow, #ca8a04)";
  return "var(--fair-green, #16a34a)";
}

function rateSeverity(rate: number): string {
  if (rate > 0.15) return "High";
  if (rate > 0.10) return "Moderate";
  if (rate > 0.05) return "Low";
  return "Minimal";
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Horizontal bar row                                  */
/* ------------------------------------------------------------------ */

function VariantRow({ group, maxRate }: { group: GroupSummary; maxRate: number }) {
  const flagged = Math.round(group.flagged_rate * group.n_comparisons);
  const barPct = maxRate > 0 ? Math.min((group.flagged_rate / maxRate) * 100, 100) : 0;

  return (
    <div className="fair-row">
      <div className="fair-row__label" title={formatVariantLabel(group.variant_type)}>
        {formatVariantLabel(group.variant_type)}
      </div>
      <div className="fair-row__bar-wrap">
        <div
          className="fair-row__bar"
          style={{ width: `${barPct}%`, background: rateColor(group.flagged_rate) }}
        />
      </div>
      <div className="fair-row__pct" style={{ color: rateColor(group.flagged_rate) }}>
        {pct(group.flagged_rate)}
      </div>
      <div className="fair-row__count">{flagged}/{group.n_comparisons}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Metric Detail Table                                 */
/* ------------------------------------------------------------------ */

function MetricTable({ groups }: { groups: GroupSummary[] }) {
  if (!groups.length) return null;
  return (
    <div className="fair-table-wrap">
      <table className="fair-table">
        <thead>
          <tr>
            <th>Variant</th>
            <th>N</th>
            <th>Flagged Rate</th>
            <th>Escalation</th>
            <th>De-escalation</th>
            <th>Identity Leakage</th>
            <th>Unsupported Inference</th>
            <th>Mean Δ</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => {
            const deescRate = g.dangerousness_change_rate - g.dangerousness_escalation_rate;
            return (
              <tr key={`${g.variant_type}-${g.prompt_mode}`}>
                <td className="fair-table__variant">{formatVariantLabel(g.variant_type)}</td>
                <td className="fair-table__num">{g.n_comparisons}</td>
                <td className="fair-table__rate" style={{ color: rateColor(g.flagged_rate) }}>
                  <strong>{pct(g.flagged_rate)}</strong>
                </td>
                <td className="fair-table__rate">
                  {g.dangerousness_escalation_rate > 0
                    ? <span style={{ color: "var(--fair-red, #dc2626)" }}>{pct(g.dangerousness_escalation_rate)} ↑</span>
                    : <span className="fair-table__zero">0%</span>}
                </td>
                <td className="fair-table__rate">
                  {deescRate > 0.005
                    ? <span style={{ color: "var(--fair-green, #16a34a)" }}>{pct(deescRate)} ↓</span>
                    : <span className="fair-table__zero">0%</span>}
                </td>
                <td className="fair-table__rate">
                  {g.identity_leakage_rate > 0.5
                    ? <span style={{ color: "var(--fair-orange, #d97706)" }}>{pct(g.identity_leakage_rate)}</span>
                    : pct(g.identity_leakage_rate)}
                </td>
                <td className="fair-table__rate">
                  {g.unsupported_inference_rate > 0
                    ? <span style={{ color: "var(--fair-orange, #d97706)" }}>{pct(g.unsupported_inference_rate)}</span>
                    : pct(g.unsupported_inference_rate)}
                </td>
                <td className="fair-table__delta">
                  {g.mean_dangerousness_delta > 0 ? "+" : ""}{g.mean_dangerousness_delta.toFixed(3)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Cross-Mode Comparison Grid                          */
/* ------------------------------------------------------------------ */

function CrossModeComparison({ groups, allGroups, promptModes }: {
  groups: GroupSummary[];
  allGroups: GroupSummary[];
  promptModes: string[];
}) {
  const variants = [...new Set(groups.map(g => g.variant_type))];

  return (
    <div className="fair-cross-mode">
      <h3 className="fair-cross-mode__title">
        <IconChart /> Cross-Mode Comparison
      </h3>
      <p className="fair-cross-mode__desc">
        How each variant&apos;s flagged rate changes across prompt strategies
      </p>
      <div className="fair-table-wrap">
        <table className="fair-table fair-table--compact">
          <thead>
            <tr>
              <th>Variant</th>
              {promptModes.map(m => (
                <th key={m}>{formatVariantLabel(m)}</th>
              ))}
              <th>Max Δ</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(vt => {
              const rates = promptModes.map(m => {
                const row = allGroups.find(g => g.variant_type === vt && g.prompt_mode === m);
                return row ? row.flagged_rate : 0;
              });
              const maxDelta = Math.max(...rates) - Math.min(...rates);
              return (
                <tr key={vt}>
                  <td className="fair-table__variant">{formatVariantLabel(vt)}</td>
                  {rates.map((r, i) => (
                    <td key={promptModes[i]} className="fair-table__rate" style={{ color: rateColor(r) }}>
                      {pct(r)}
                    </td>
                  ))}
                  <td className="fair-table__delta" style={{
                    color: maxDelta > 0.05 ? "var(--fair-orange, #d97706)" : "inherit",
                    fontWeight: maxDelta > 0.05 ? 700 : 400,
                  }}>
                    {maxDelta > 0 ? `±${pct(maxDelta)}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

interface FairnessScreeningPageProps {
  bundle: DashboardBundle;
}

export function FairnessScreeningPage({ bundle }: FairnessScreeningPageProps) {
  const [selectedPromptMode, setSelectedPromptMode] = useState<string>("baseline");
  const [showDetails, setShowDetails] = useState(false);

  const promptModes = bundle.promptModes.length ? bundle.promptModes : ["baseline"];

  /* ================================================================ */
  /*  Compute data for selected prompt mode                           */
  /* ================================================================ */

  const currentGroups = useMemo(() => {
    return bundle.groupSummary
      .filter(g => g.prompt_mode === selectedPromptMode)
      .sort((a, b) => b.flagged_rate - a.flagged_rate);
  }, [bundle.groupSummary, selectedPromptMode]);

  const allGroups = useMemo(() => {
    return bundle.groupSummary;
  }, [bundle.groupSummary]);

  const totalComparisons = currentGroups.reduce((s, g) => s + g.n_comparisons, 0);
  const totalFlagged = currentGroups.reduce((s, g) => s + Math.round(g.flagged_rate * g.n_comparisons), 0);
  const meanFlaggedRate = currentGroups.length > 0
    ? currentGroups.reduce((s, g) => s + g.flagged_rate, 0) / currentGroups.length : 0;
  const meanEscalation = currentGroups.length > 0
    ? currentGroups.reduce((s, g) => s + g.dangerousness_escalation_rate, 0) / currentGroups.length : 0;
  const meanIdentityLeak = currentGroups.length > 0
    ? currentGroups.reduce((s, g) => s + g.identity_leakage_rate, 0) / currentGroups.length : 0;
  const maxRate = Math.max(...currentGroups.map(g => g.flagged_rate), 0.01);

  /* Key insights */
  const highestVariant = currentGroups.length > 0 ? currentGroups[0] : null;
  const lowestVariant = currentGroups.length > 0 ? currentGroups[currentGroups.length - 1] : null;

  return (
    <section className="fair-page">
      {/* ── Header ── */}
      <header className="fair-header">
        <h1 className="fair-header__title">Fairness Screening</h1>
        <p className="fair-header__subtitle">
          Counterfactual analysis measuring how demographic proxy variants (ethnicity, neighborhood,
          age, employment, family status) affect LLM risk assessments across 30 base cases
        </p>
      </header>

      {/* ── Explainer ── */}
      <div className="fair-explainer">
        <div className="fair-explainer__icon"><IconUser /></div>
        <div>
          <strong>Demographic Proxy Variants</strong>
          <p>
            Each of 30 base cases is tested with 5 proxy variants: ethnicity, neighborhood, age,
            employment status, and family status. The control case is held constant while only
            the demographic cue changes. Any shift in risk assessment flags potential bias.
          </p>
        </div>
      </div>

      {/* ── Prompt Mode Selector ── */}
      <div className="fair-mode-bar">
        <span className="fair-mode-bar__label">Prompt Strategy:</span>
        <div className="fair-mode-bar__btns">
          {promptModes.map(mode => (
            <button
              key={mode}
              className={`fair-mode-btn ${selectedPromptMode === mode ? "fair-mode-btn--active" : ""}`}
              onClick={() => setSelectedPromptMode(mode)}
            >
              {formatVariantLabel(mode)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Key Stats ── */}
      <div className="v2-stat-grid">
        <StatCard
          label="Comparisons"
          value={formatCount(totalComparisons)}
          tooltip="Total pairwise comparisons for the selected prompt mode"
        />
        <StatCard
          label="Flagged"
          value={formatCount(totalFlagged)}
          variant={totalFlagged > 0 ? "warning" : "success"}
          tooltip="Cases where the model shifted risk assessment based on demographic changes"
        />
        <StatCard
          label="Mean Flagged Rate"
          value={pct(meanFlaggedRate)}
          variant={meanFlaggedRate > 0.10 ? "danger" : meanFlaggedRate > 0.05 ? "warning" : "success"}
          tooltip="Average flagged rate across all variant groups"
        />
        <StatCard
          label="Mean Escalation"
          value={pct(meanEscalation)}
          variant={meanEscalation > 0.05 ? "danger" : "default"}
          tooltip="Rate at which the model increased risk assessment for demographic variants"
        />
        <StatCard
          label="Identity Leakage"
          value={pct(meanIdentityLeak)}
          variant={meanIdentityLeak > 0.7 ? "warning" : "default"}
          tooltip="Rate at which the model referenced the suspect's identity in reasoning"
        />
      </div>

      {/* ── Key Insight ── */}
      {highestVariant && highestVariant.flagged_rate > 0 && (
        <div className="fair-insight">
          <div className="fair-insight__icon"><IconScale /></div>
          <div>
            <strong>Key Finding</strong>
            <p>
              Highest flagged rate: <strong>{formatVariantLabel(highestVariant.variant_type)}</strong> at{" "}
              <strong style={{ color: rateColor(highestVariant.flagged_rate) }}>{pct(highestVariant.flagged_rate)}</strong>{" "}
              ({Math.round(highestVariant.flagged_rate * highestVariant.n_comparisons)}/{highestVariant.n_comparisons} comparisons).
              {lowestVariant && lowestVariant.variant_type !== highestVariant.variant_type && (
                <> Lowest: <strong>{formatVariantLabel(lowestVariant.variant_type)}</strong> at {pct(lowestVariant.flagged_rate)}.</>
              )}
              {" "}Severity: <strong>{rateSeverity(meanFlaggedRate)}</strong>.
            </p>
          </div>
        </div>
      )}

      {/* ── Disclaimer ── */}
      <div className="fair-explainer" style={{ opacity: 0.8 }}>
        <div className="fair-explainer__icon"><IconWarning /></div>
        <div>
          <p>
            Flags are screening signals for human legal review — not proof of unlawful discrimination.
            All 5 variant types are strict counterfactual proxies where only the demographic cue changes.
          </p>
        </div>
      </div>

      {/* ── Bar Chart ── */}
      {currentGroups.length > 0 ? (
        <section className="fair-section">
          <h2 className="fair-section__title">Flagged Rate by Variant</h2>
          <p className="fair-section__subtitle">
            {formatVariantLabel(selectedPromptMode)} prompt mode — 30 comparisons per variant
          </p>
          <div className="fair-chart">
            {currentGroups.map(g => (
              <VariantRow key={g.variant_type} group={g} maxRate={maxRate} />
            ))}
          </div>
        </section>
      ) : (
        <div className="fair-empty">
          <div className="fair-empty__icon"><IconUser /></div>
          <strong className="fair-empty__title">No Data Available</strong>
          <p className="fair-empty__desc">
            No pairwise comparison data available for the {formatVariantLabel(selectedPromptMode)} prompt mode.
          </p>
        </div>
      )}

      {/* ── Detail Table Toggle ── */}
      {currentGroups.length > 0 && (
        <section className="fair-section">
          <button
            className="fair-toggle"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? "▾ Hide" : "▸ Show"} Detailed Metrics Table
          </button>
          {showDetails && (
            <MetricTable groups={currentGroups} />
          )}
        </section>
      )}

      {/* ── Cross-Mode Comparison ── */}
      {promptModes.length > 1 && allGroups.length > 0 && (
        <section className="fair-section">
          <CrossModeComparison
            groups={currentGroups}
            allGroups={allGroups}
            promptModes={promptModes}
          />
        </section>
      )}
    </section>
  );
}
