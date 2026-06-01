"use client";

import type React from "react";
import { useMemo } from "react";
import { IconClipboard, IconScale, IconLock, IconDocument, IconWarning } from "@/components/v2/Icons";
import type { DashboardBundle } from "@/lib/v2/dataUtils";
import {
  computeHeadlineMetrics,
  formatRate,
  formatCount,
  formatPromptMode,
} from "@/lib/v2/dataUtils";
import { StatCard } from "./StatCard";
import { BarChartPanel } from "./BarChartPanel";
import { EmptyState } from "./EmptyState";

interface PromptMitigationPageProps {
  bundle: DashboardBundle;
}

const MODE_COLORS: Record<string, string> = {
  baseline: "#6366f1",
  fairness_aware: "#10b981",
  demographic_blind: "#f59e0b",
};

const MODE_DESCRIPTIONS: Record<string, string> = {
  baseline: "Standard legal analysis prompt with no fairness-related instructions.",
  fairness_aware: "Prompt includes explicit instructions to avoid reliance on demographic identity, proxy cues, or stereotypes.",
  demographic_blind: "Prompt instructs the model to ignore all demographic information and focus only on legally relevant facts.",
};

const MODE_ICONS: Record<string, React.ReactNode> = {
  baseline: <IconClipboard />,
  fairness_aware: <IconScale />,
  demographic_blind: <IconLock />,
};

function getModeColor(mode: string): string {
  return MODE_COLORS[mode] ?? "#8b5cf6";
}

export function PromptMitigationPage({ bundle }: PromptMitigationPageProps) {
  const metrics = computeHeadlineMetrics(bundle);
  const { perModeMetrics } = metrics;
  const modeEntries = Object.entries(perModeMetrics);

  /* ---- Cross-prompt mode summary ---- */
  const crossSummary = bundle.crossPromptModeSummary;
  const crossEntries = useMemo(() => {
    if (!crossSummary?.by_comparison_mode) return [];
    return Object.entries(crossSummary.by_comparison_mode);
  }, [crossSummary]);

  /* ---- Total instability counts ---- */
  const totalInstability = useMemo(() => {
    let material = 0;
    let wordingOnly = 0;
    let total = 0;
    for (const [, data] of crossEntries) {
      material += data.material_instability ?? 0;
      wordingOnly += data.wording_only ?? 0;
      total += data.total ?? 0;
    }
    return { material, wordingOnly, total };
  }, [crossEntries]);

  /* ---- Chart data: flagged rate by prompt mode ---- */
  const flaggedRateChartData = useMemo(
    () =>
      modeEntries.map(([mode, data]) => ({
        name: formatPromptMode(mode),
        value: +(data.flaggedRate * 100).toFixed(1),
        fill: getModeColor(mode),
      })),
    [modeEntries],
  );

  /* ---- Verdict computation ---- */
  const verdict = useMemo(() => {
    const baselineRate = perModeMetrics["baseline"]?.flaggedRate ?? 0;
    const otherModes = modeEntries.filter(([m]) => m !== "baseline");

    if (otherModes.length === 0) {
      return {
        type: "neutral" as const,
        icon: "—",
        text: "Only baseline prompt mode is available — no mitigation comparison possible.",
        cssClass: "callout callout-info",
      };
    }

    const allLower = otherModes.every(([, data]) => data.flaggedRate < baselineRate - 0.001);
    const allHigher = otherModes.every(([, data]) => data.flaggedRate > baselineRate + 0.001);
    const allEqual = otherModes.every(([, data]) => Math.abs(data.flaggedRate - baselineRate) < 0.005);

    if (allEqual) {
      return {
        type: "neutral" as const,
        icon: "—",
        text: "Mitigation prompts did not meaningfully change flagged rates compared to baseline.",
        cssClass: "callout callout-info",
      };
    }
    if (allLower) {
      return {
        type: "positive" as const,
        icon: "✓",
        text: "Mitigation prompts reduced flagged rates compared to baseline. Fairness-aware and demographic-blind strategies appear to reduce differential treatment.",
        cssClass: "v2-callout v2-callout--success",
      };
    }
    if (allHigher) {
      return {
        type: "negative" as const,
        icon: <IconWarning />,
        text: "Mitigation prompts increased flagged rates compared to baseline — the mitigation strategies may have introduced overcorrection or new instabilities. Further investigation recommended.",
        cssClass: "v2-callout v2-callout--danger",
      };
    }
    return {
      type: "mixed" as const,
      icon: "◑",
      text: "Mixed results: some mitigation strategies reduced flagged rates while others increased them. Neither approach consistently outperformed baseline.",
      cssClass: "v2-callout v2-callout--warning",
    };
  }, [perModeMetrics, modeEntries]);

  if (modeEntries.length === 0) {
    return (
      <section className="v2-mitigation-page">
        <header className="v2-mitigation-page__header">
          <h1 className="v2-mitigation-page__title">Prompt Mitigation Comparison</h1>
        </header>
        <EmptyState
          title="No prompt mode data"
          message="Per-prompt-mode metrics are not available. Ensure the audit was run with multiple prompt modes."
        />
      </section>
    );
  }

  return (
    <section className="v2-mitigation-page v2-fade-in">
      {/* Header */}
      <header className="v2-mitigation-page__header">
        <h1 className="v2-mitigation-page__title">Prompt Mitigation Comparison</h1>
        <p className="v2-mitigation-page__subtitle">
          Comparing how different prompting strategies affect bias screening results
        </p>
      </header>

      {/* Verdict Callout — prominent at the top */}
      <div className={verdict.cssClass}>
        <span className="v2-callout__icon" aria-hidden="true">{verdict.icon}</span>
        <div>
          <strong>Verdict: </strong>
          {verdict.text}
        </div>
      </div>

      {/* Prompt Mode Explanations */}
      <div className="v2-mitigation-page__section">
        <h2 className="v2-mitigation-page__section-title">Prompt Strategies Tested</h2>
        <p className="v2-mitigation-page__section-subtitle">
          Each case was assessed under three different prompt strategies to test whether mitigation instructions reduce bias signals
        </p>
        <div className="v2-mitigation-page__mode-cards">
          {modeEntries.map(([mode, data]) => (
            <article
              key={mode}
              className="v2-mitigation-page__mode-card"
              style={{ borderTopColor: getModeColor(mode) }}
            >
              <h3 className="v2-mitigation-page__mode-card-title">
                {MODE_ICONS[mode] ?? <IconDocument />} {formatPromptMode(mode)}
              </h3>
              <p className="muted" style={{ marginBottom: "0.75rem", lineHeight: 1.5 }}>
                {MODE_DESCRIPTIONS[mode] ?? ""}
              </p>
              <dl className="v2-mitigation-page__mode-card-metrics">
                <div className="v2-mitigation-page__mode-card-metric">
                  <dt>Comparisons</dt>
                  <dd>{formatCount(data.comparisons)}</dd>
                </div>
                <div className="v2-mitigation-page__mode-card-metric">
                  <dt>Flagged</dt>
                  <dd>{formatCount(data.flagged)}</dd>
                </div>
              </dl>
              <div className="v2-mitigation-page__mode-card-rate">
                {formatRate(data.flaggedRate)}
              </div>
              <p className="v2-mitigation-page__note">flagged rate</p>
            </article>
          ))}
        </div>
      </div>

      {/* Flagged Rate Chart */}
      <div className="v2-mitigation-page__section">
        <BarChartPanel
          data={flaggedRateChartData}
          title="Flagged Rate by Prompt Mode (%)"
          yLabel="%"
          formatValue={(v) => v.toFixed(1) + "%"}
        />
      </div>

      {/* Cross-Prompt Instability Section */}
      <div className="v2-mitigation-page__instability-section">
        <h2 className="v2-mitigation-page__section-title">Cross-Prompt Instability</h2>
        <p className="v2-mitigation-page__section-subtitle">
          When different prompt modes produce different dangerousness assessments for the same variant, it signals model instability
        </p>

        <div className="stat-grid">
          <StatCard
            label="Total Cross-Prompt Comparisons"
            value={formatCount(
              bundle.overview.n_cross_prompt_comparisons ?? totalInstability.total,
            )}
            tooltip="Total cross-prompt comparisons between prompt modes"
          />
          <StatCard
            label="Material Instability"
            value={formatCount(
              bundle.overview.n_cross_prompt_material_instability_flags ?? totalInstability.material,
            )}
            variant={totalInstability.material > 0 ? "warning" : "default"}
            tooltip="Dangerousness level changed between prompt modes — substantive difference"
          />
          <StatCard
            label="Wording-Only Changes"
            value={formatCount(
              bundle.overview.n_cross_prompt_wording_only_changes ?? totalInstability.wordingOnly,
            )}
            tooltip="Only reasoning text changed, no material outcome difference"
          />
        </div>
      </div>

      {/* Cross-prompt mode summary cards */}
      {crossSummary && crossEntries.length > 0 && (
        <div className="v2-mitigation-page__cross-summary">
          <h2 className="v2-mitigation-page__section-title">Per-Mode Instability Breakdown</h2>
          {crossSummary.note && (
            <p className="v2-mitigation-page__note">{crossSummary.note}</p>
          )}
          <div className="v2-mitigation-page__cross-cards">
            {crossEntries.map(([mode, data]) => (
              <article key={mode} className="v2-mitigation-page__cross-card">
                <h3 className="v2-mitigation-page__cross-card-title">
                  vs {formatPromptMode(mode)}
                </h3>
                <dl className="v2-mitigation-page__cross-card-metrics">
                  <div className="v2-mitigation-page__cross-card-metric">
                    <dt>Material Instability</dt>
                    <dd>{formatCount(data.material_instability)}</dd>
                  </div>
                  <div className="v2-mitigation-page__cross-card-metric">
                    <dt>Wording-Only</dt>
                    <dd>{formatCount(data.wording_only)}</dd>
                  </div>
                  <div className="v2-mitigation-page__cross-card-metric">
                    <dt>Total</dt>
                    <dd>{formatCount(data.total)}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
