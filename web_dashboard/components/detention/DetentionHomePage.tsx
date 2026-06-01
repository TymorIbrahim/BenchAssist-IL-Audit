"use client";

import { useState } from "react";
import { PageHeader } from "@/components/detention/PageHeader";
import { ExampleCard, ComparisonExample } from "@/components/detention/ExampleCard";
import { DetentionExportMetadataPanel } from "@/components/detention/DetentionExportMetadataPanel";
import { DetentionReadinessPanel } from "@/components/detention/DetentionReadinessPanel";
import { StatCard } from "@/components/MetricCard";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { RESEARCH_PROCESS_STEPS, RESEARCH_QUESTION } from "@/lib/detentionStory";
import type { DetentionTab } from "@/lib/detentionNavigation";
import { detentionDataModeBadge, detentionHeadlineMetrics } from "@/lib/detentionMetrics";
import { formatCount } from "@/lib/format";

export function DetentionHomePage({
  bundle,
  onNavigate,
  onStartTour,
  onPresentationMode,
  onStartExpertReview,
}: {
  bundle: DetentionDashboardBundle;
  onNavigate: (tab: DetentionTab, opts?: { exampleId?: string }) => void;
  onStartTour: () => void;
  onPresentationMode: () => void;
  onStartExpertReview?: () => void;
}) {
  const [expandedWhy, setExpandedWhy] = useState(true);
  const { overview } = bundle;
  const headline = detentionHeadlineMetrics(bundle);

  return (
    <div className="tab-panel home-panel">
      <PageHeader
        title="BenchAssist-IL Detention Audit"
        subtitle="A Responsible AI audit of a toy, non-binding detention/remand decision-support assistant."
        note="This dashboard is for research and expert review. It does not provide legal advice or make detention decisions."
        badges={[
          { label: detentionDataModeBadge(bundle), variant: bundle.isMock ? "caution" : "info" },
          { label: "Synthetic fairness audit", variant: "neutral" },
          { label: "Minimal schema · dangerousness-only flagging", variant: "neutral" },
          { label: "Internal expert dashboard", variant: "neutral" },
        ]}
        actions={
          <>
            {onStartExpertReview && (bundle.caseReviewIndexCount > 0 || bundle.caseReviewRecords.length > 0) ? (
              <button type="button" className="btn btn-primary btn-sm" onClick={onStartExpertReview}>
                Start expert review
              </button>
            ) : null}
            <button type="button" className="btn btn-secondary btn-sm" onClick={onStartTour}>
              Start here — guided tour
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={onPresentationMode}>
              Presentation mode
            </button>
          </>
        }
      />

      <section className="section-card research-question-card">
        <h3>Research question</h3>
        <p className="research-question-text">{RESEARCH_QUESTION}</p>
      </section>

      <section className="section-card">
        <button
          type="button"
          className="expandable-section-header"
          onClick={() => setExpandedWhy((v) => !v)}
          aria-expanded={expandedWhy}
        >
          <h3>Why this matters</h3>
          <span className="expand-chevron">{expandedWhy ? "−" : "+"}</span>
        </button>
        {expandedWhy ? (
          <ul className="why-list">
            <li>Detention affects liberty before conviction — decisions must be legally justified and fact-based.</li>
            <li>Judges and prosecutors work under time pressure; AI assistants may influence framing of risk memos.</li>
            <li>Systems may reproduce or amplify identity, language, or narrative framing effects.</li>
            <li>This audit looks for audit signals that require human legal review — not final legal conclusions.</li>
          </ul>
        ) : (
          <p className="muted">Detention is high-stakes. AI risk memos may shift framing — expert review is required.</p>
        )}
      </section>

      <section className="section-card">
        <h3>Research process</h3>
        <div className="process-timeline">
          {RESEARCH_PROCESS_STEPS.map((step, i) => (
            <div key={step.id} className="process-timeline-step">
              <div className="process-timeline-marker">{i + 1}</div>
              <div className="process-timeline-content">
                <strong>{step.title}</strong>
                <p className="muted">{step.description}</p>
                {step.tab ? (
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => onNavigate(step.tab!)}>
                    Go to section →
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="section-card">
        <h3>Concrete examples</h3>
        <div className="examples-grid">
          <ExampleCard title="Synthetic base case" onSeeExample={() => onNavigate("methodology")}>
            <ul className="compact-list">
              <li>Suspected assault after a street fight</li>
              <li>Moderate evidence · prior record · no weapon</li>
              <li>Witness-contact risk · release conditions possible</li>
            </ul>
          </ExampleCard>
          <ExampleCard title="Variant (identity/language only)" onSeeExample={() => onNavigate("case-review")}>
            <p className="example-hebrew" dir="rtl" lang="he">
              החשוד מסר כי היה במקום אך הכחיש תקיפה...
            </p>
            <p className="muted">Same legal facts — only name, language, or presentation changes.</p>
          </ExampleCard>
          <ExampleCard title="Model output (minimal schema)" onSeeExample={() => onNavigate("audit-results")}>
            <dl className="mini-dl">
              <div><dt>Case summary</dt><dd>Short structured recap</dd></div>
              <div><dt>Dangerousness</dt><dd>medium</dd></div>
              <div><dt>Reasoning</dt><dd>Fact-based memo text</dd></div>
            </dl>
          </ExampleCard>
          <ExampleCard title="Neutral vs variant comparison" onSeeExample={() => onNavigate("case-review")}>
            <ComparisonExample />
          </ExampleCard>
        </div>
      </section>

      <section className="section-card">
        <h3>Audit method at a glance</h3>
        <p className="muted section-intro">Slim synthetic corpus, minimal schema outputs, dangerousness-only flagging.</p>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onNavigate("methodology")}>
          Full methodology →
        </button>
      </section>

      <div className="metric-grid">
        <StatCard
          label="Comparisons"
          value={formatCount(headline.pairwiseCount)}
          sub={headline.usesBaselineHeadline ? "Baseline prompt · strict synthetic audit" : "Synthetic strict audit"}
        />
        <StatCard
          label="Audit signals"
          value={formatCount(headline.flaggedCount)}
          sub={
            headline.usesBaselineHeadline
              ? `Baseline prompt · ${formatCount(headline.flaggedCountAllModes)} across all modes`
              : "Flagged for legal review"
          }
        />
        <StatCard label="High-priority queue" value={formatCount(bundle.highPriorityCount)} sub="Requires human review" />
        <StatCard label="Strict-excluded layer" value={formatCount(overview.n_strict_excluded_review_outputs ?? 0)} sub={`${formatCount(overview.n_address_proxy_review_outputs ?? overview.n_strict_excluded_review_outputs ?? 0)} address-proxy · excluded from strict rates`} />
      </div>

      <DetentionExportMetadataPanel bundle={bundle} />
      <DetentionReadinessPanel bundle={bundle} />
    </div>
  );
}
