"use client";

import "@/app/overview.css";

import React, { useMemo } from "react";
import {
  IconClipboard,
  IconCycle,
  IconRobot,
  IconScale,
  IconWarning,
  IconSearch,
  IconChart,
  IconUser,
  IconFlag,
  IconMapPin,
} from "@/components/v2/Icons";
import type { DashboardTab } from "@/lib/v2/types";
import type { DashboardBundle } from "@/lib/v2/dataUtils";
import {
  computeHeadlineMetrics,
  formatRate,
  formatCount,
  formatVariantLabel,
} from "@/lib/v2/dataUtils";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface OverviewPageProps {
  bundle: DashboardBundle;
  onNavigate: (tab: DashboardTab) => void;
}

/* ------------------------------------------------------------------ */
/*  Audit Process Timeline                                             */
/* ------------------------------------------------------------------ */

const PROCESS_STEPS: { icon: React.ReactNode; title: string; detail: string; dynamicTitle?: boolean }[] = [
  {
    icon: <IconClipboard />,
    title: "30 Base Cases",
    dynamicTitle: true,
    detail: "Synthetic pretrial detention scenarios across Hebrew and English, covering a range of criminal offense types and case circumstances",
  },
  {
    icon: <IconCycle />,
    title: "6 Counterfactual Variants",
    detail: "Each case modified with 1 control + 5 proxy variants: ethnicity, neighborhood, age, employment status, and family status",
  },
  {
    icon: <IconRobot />,
    title: "3 Prompt Modes × 180 Cases",
    detail: "Every case assessed under Baseline, Fairness-Aware, and Demographic-Blind prompt strategies — 540 total LLM outputs",
  },
  {
    icon: <IconScale />,
    title: "450 Pairwise Comparisons",
    detail: "Each variant's risk assessment and recommendation compared against its control — flagging any shifts on identical legal facts",
  },
  {
    icon: <IconSearch />,
    title: "Expert Review",
    detail: "Flagged cases surfaced for human legal review with side-by-side comparison, diff highlights, and cross-prompt instability analysis",
  },
];

/* ------------------------------------------------------------------ */
/*  Nav Items                                                          */
/* ------------------------------------------------------------------ */

const NAV_ITEMS: { tab: DashboardTab; label: string; desc: string; icon: React.ReactNode }[] = [
  { tab: "fairness", label: "Fairness Screening", desc: "Three-tier demographic, address, and combined bias analysis", icon: <IconScale /> },
  { tab: "mitigation", label: "Prompt Mitigation", desc: "Compare prompt strategies and their effect on model behavior", icon: <IconChart /> },
  { tab: "case-explorer", label: "Case Explorer", desc: "Side-by-side case review with diff highlighting and prompt viewer", icon: <IconSearch /> },
  { tab: "run-metadata", label: "Run Metadata", desc: "Technical details: model, schema, config, and run statistics", icon: <IconClipboard /> },
];

/* ------------------------------------------------------------------ */
/*  Mini bar component                                                 */
/* ------------------------------------------------------------------ */

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="overview-minibar">
      <div className="overview-minibar__fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function OverviewPage({ bundle, onNavigate }: OverviewPageProps) {
  const metrics = computeHeadlineMetrics(bundle);

  /* ── Per-variant flagging rates for chart ── */
  const variantBars = useMemo(() => {
    const baselineRows = bundle.groupSummary.filter(
      (g) => g.prompt_mode === "baseline" && !g.variant_type.startsWith("address_"),
    );
    return baselineRows
      .map((g) => ({
        label: formatVariantLabel(g.variant_type),
        rate: g.flagged_rate,
        comparisons: g.n_comparisons,
        flagged: Math.round(g.flagged_rate * g.n_comparisons),
      }))
      .sort((a, b) => b.rate - a.rate);
  }, [bundle.groupSummary]);

  const maxRate = Math.max(...variantBars.map((b) => b.rate), 0.01);

  /* ── Real flagged examples ── */
  const featuredExamples = useMemo(() => {
    const flaggedIdx = (bundle.caseReviewIndex || []).filter(
      (r) => r.is_flagged && r.prompt_mode === "baseline" && r.analysis_bucket === "strict_demographic",
    );
    return flaggedIdx.slice(0, 3);
  }, [bundle.caseReviewIndex]);

  /* ── Prompt mode cards ── */
  const promptModes = useMemo(() => {
    const modes = [
      { key: "baseline", label: "Baseline", desc: "Neutral legal prompt — no demographic instructions" },
      { key: "fairness_aware", label: "Fairness-Aware", desc: "Explicit identity cue evaluation and equal treatment" },
      { key: "demographic_blind", label: "Demographic-Blind", desc: "Strong identity blindness — treat as if redacted" },
    ];
    return modes.map(({ key, label, desc }) => {
      const rows = bundle.groupSummary.filter((g) => g.prompt_mode === key && !g.variant_type.startsWith("address_"));
      const comparisons = rows.reduce((s, r) => s + r.n_comparisons, 0);
      const flagged = rows.reduce((s, r) => s + Math.round(r.flagged_rate * r.n_comparisons), 0);
      const rate = comparisons > 0 ? flagged / comparisons : 0;
      return { key, label, desc, comparisons, flagged, rate };
    });
  }, [bundle.groupSummary]);

  /* ── Cross-prompt instability count ── */
  const crossPromptInstability = bundle.overview.n_cross_prompt_material_instability_flags ?? 0;

  /* ── Screening rate ── */
  const flaggedComparisons = bundle.overview.n_flagged_comparisons_baseline ?? bundle.overview.n_flagged_comparisons ?? 0;
  const totalComparisons = bundle.overview.n_pairwise_comparisons_baseline ?? bundle.overview.n_pairwise_comparisons ?? 1;
  const screeningPct = totalComparisons > 0 ? ((flaggedComparisons / totalComparisons) * 100).toFixed(1) : "0.0";

  return (
    <section className="overview-page">
      {/* ── Hero ── */}
      <header className="overview-hero">
        <div className="overview-hero__text">
          <h1 className="overview-hero__title">BenchAssist-IL Pretrial Detention Audit</h1>
          <p className="overview-hero__subtitle">
            Systematic fairness screening of LLM-generated risk assessments for Israeli
            pretrial detention hearings — 30 cases × 6 variants × 3 prompt modes
          </p>
        </div>
        <div className="overview-hero__screening-ring">
          <svg viewBox="0 0 120 120" className="overview-hero__ring-svg">
            <circle cx="60" cy="60" r="52" className="overview-hero__ring-bg" />
            <circle
              cx="60" cy="60" r="52"
              className="overview-hero__ring-fill"
              strokeDasharray={`${Number(screeningPct) * 3.267} 326.7`}
              strokeDashoffset="0"
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div className="overview-hero__ring-label">
            <span className="overview-hero__ring-value">{screeningPct}%</span>
            <span className="overview-hero__ring-text">Screening Rate</span>
          </div>
        </div>
      </header>

      {/* ── Disclaimer ── */}
      <div className="overview-disclaimer">
        <IconWarning />
        <p>
          Flags are screening signals for human legal review — not proof of unlawful discrimination.
          Audit fields (tone, hallucination, police framing, defense consideration) are post-processed, not self-reported.
        </p>
      </div>

      {/* ── Stats Grid ── */}
      <div className="overview-stats">
        <div className="overview-stat">
          <span className="overview-stat__value">{formatCount(bundle.baseCaseIds.length)}</span>
          <span className="overview-stat__label">Base Cases</span>
        </div>
        <div className="overview-stat">
          <span className="overview-stat__value">{formatCount(metrics.totalVariants)}</span>
          <span className="overview-stat__label">Total Outputs</span>
        </div>
        <div className="overview-stat">
          <span className="overview-stat__value">{formatCount(metrics.totalComparisons)}</span>
          <span className="overview-stat__label">Pairwise Comparisons</span>
        </div>
        <div className="overview-stat">
          <span className="overview-stat__value overview-stat__value--warn">{formatCount(metrics.baselineFlagged)}</span>
          <span className="overview-stat__label">Flagged (Baseline)</span>
        </div>
        <div className="overview-stat">
          <span className="overview-stat__value overview-stat__value--info">{formatCount(crossPromptInstability)}</span>
          <span className="overview-stat__label">Cross-Prompt Instability</span>
        </div>
        <div className="overview-stat">
          <span className="overview-stat__value">{formatRate(metrics.parseSuccessRate)}</span>
          <span className="overview-stat__label">Parse Success</span>
        </div>
      </div>

      {/* ── Audit Process Timeline ── */}
      <section className="overview-section">
        <h2 className="overview-section__title">How the Audit Works</h2>
        <p className="overview-section__subtitle">
          A five-stage pipeline designed to detect demographic bias in LLM-generated detention risk assessments
        </p>
        <div className="overview-timeline">
          {PROCESS_STEPS.map((step, i) => (
            <div key={step.title} className="overview-timeline__step">
              <div className="overview-timeline__marker">
                <span className="overview-timeline__num">{i + 1}</span>
              </div>
              {i < PROCESS_STEPS.length - 1 && <div className="overview-timeline__connector" />}
              <div className="overview-timeline__content">
                <div className="overview-timeline__icon">{step.icon}</div>
                <h3 className="overview-timeline__title">{step.title}</h3>
                <p className="overview-timeline__detail">{step.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Per-Variant Flagging Chart ── */}
      <section className="overview-section">
        <h2 className="overview-section__title">Flagging Rate by Variant</h2>
        <p className="overview-section__subtitle">
          Baseline prompt mode — strict demographic comparisons only
        </p>
        <div className="overview-chart">
          {variantBars.map((bar) => (
            <div key={bar.label} className="overview-chart__row">
              <span className="overview-chart__label">{bar.label}</span>
              <div className="overview-chart__bar-wrap">
                <MiniBar
                  value={bar.rate}
                  max={maxRate}
                  color={bar.rate > 0 ? "var(--v2-accent-warning)" : "var(--v2-border)"}
                />
              </div>
              <span className="overview-chart__value">{(bar.rate * 100).toFixed(0)}%</span>
              <span className="overview-chart__count">{bar.flagged}/{bar.comparisons}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Featured Flagged Examples ── */}
      {featuredExamples.length > 0 && (
        <section className="overview-section">
          <h2 className="overview-section__title">Featured Flagged Cases</h2>
          <p className="overview-section__subtitle">
            Real examples where the model shifted dangerousness assessment based on non-legal identity changes
          </p>
          <div className="overview-examples">
            {featuredExamples.map((ex) => (
              <button
                type="button"
                key={ex.review_record_id}
                className="overview-example"
                onClick={() => onNavigate("case-explorer")}
              >
                <div className="overview-example__header">
                  <span className="overview-example__case-id">{ex.base_case_id}</span>
                  <span className="overview-example__title">{ex.base_case_title}</span>
                </div>
                <div className="overview-example__variant">
                  <IconUser /> {formatVariantLabel(ex.variant_type)}
                </div>
                {ex.issue_types?.[0] && (
                  <div className="overview-example__flag">
                    <IconFlag /> {ex.issue_types[0]}
                  </div>
                )}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ── Prompt Mode Comparison ── */}
      <section className="overview-section">
        <h2 className="overview-section__title">Prompt Strategy Comparison</h2>
        <p className="overview-section__subtitle">
          How different prompting approaches affect model bias — demographic comparisons only
        </p>
        <div className="overview-modes">
          {promptModes.map((m) => (
            <div
              key={m.key}
              className={`overview-mode ${m.key === "baseline" ? "overview-mode--primary" : ""}`}
            >
              <h3 className="overview-mode__title">{m.label}</h3>
              <p className="overview-mode__desc">{m.desc}</p>
              <div className="overview-mode__metrics">
                <div className="overview-mode__metric">
                  <span className="overview-mode__metric-value">{formatCount(m.comparisons)}</span>
                  <span className="overview-mode__metric-label">Comparisons</span>
                </div>
                <div className="overview-mode__metric">
                  <span className="overview-mode__metric-value overview-mode__metric-value--flag">{formatCount(m.flagged)}</span>
                  <span className="overview-mode__metric-label">Flagged</span>
                </div>
                <div className="overview-mode__metric">
                  <span className="overview-mode__metric-value">{formatRate(m.rate)}</span>
                  <span className="overview-mode__metric-label">Flag Rate</span>
                </div>
              </div>
              <MiniBar value={m.rate} max={Math.max(...promptModes.map((p) => p.rate), 0.01)} color="var(--v2-accent-warning)" />
            </div>
          ))}
        </div>
      </section>

      {/* ── Navigation ── */}
      <nav className="overview-nav" aria-label="Dashboard sections">
        <h2 className="overview-section__title">Explore the Audit</h2>
        <div className="overview-nav__grid">
          {NAV_ITEMS.map(({ tab, label, desc, icon }) => (
            <button
              key={tab}
              type="button"
              className="overview-nav__card"
              onClick={() => onNavigate(tab)}
            >
              <span className="overview-nav__icon">{icon}</span>
              <span className="overview-nav__label">{label}</span>
              <span className="overview-nav__desc">{desc}</span>
            </button>
          ))}
        </div>
      </nav>
    </section>
  );
}
