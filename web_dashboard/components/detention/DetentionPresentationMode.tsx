"use client";

import { ComparisonExample } from "@/components/detention/ExampleCard";
import { AuditMethodDiagram } from "@/components/detention/AuditMethodDiagram";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import type { DetentionTakeaway } from "@/lib/detentionTakeaways";
import { RESEARCH_QUESTION } from "@/lib/detentionStory";
import { defaultAuditPromptMode, detentionHeadlineMetrics, filterRowsByPromptMode } from "@/lib/detentionMetrics";
import { useOverlayDismiss } from "@/lib/useOverlayDismiss";
import { formatCount } from "@/lib/format";

export function DetentionPresentationMode({
  bundle,
  takeaways,
  onClose,
  onOpenCase,
}: {
  bundle: DetentionDashboardBundle;
  takeaways: DetentionTakeaway[];
  onClose: () => void;
  onOpenCase: () => void;
}) {
  useOverlayDismiss(true, onClose);
  const topFindings = takeaways.slice(0, 3);
  const example = bundle.flagged.find((r) => String(r.prompt_mode || "baseline") === "baseline") ?? bundle.flagged[0];
  const addressProxyOutputs = bundle.overview.n_address_proxy_review_outputs ?? bundle.overview.n_strict_excluded_review_outputs ?? 0;
  const headline = detentionHeadlineMetrics(bundle);
  const baselineMode = defaultAuditPromptMode(bundle);
  const baselinePairwise = baselineMode ? filterRowsByPromptMode(bundle.pairwise, baselineMode) : bundle.pairwise;
  const baseScenarioCount = new Set(baselinePairwise.map((r) => String(r.case_id))).size;

  return (
    <div className="presentation-overlay" role="dialog" aria-label="Presentation mode">
      <header className="presentation-overlay-header">
        <h2>Presentation mode</h2>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>Exit presentation</button>
      </header>
      <div className="presentation-slides">
        <section className="presentation-slide">
          <h3>Research question</h3>
          <p className="presentation-lead">{RESEARCH_QUESTION}</p>
        </section>
        <section className="presentation-slide">
          <h3>Audit method</h3>
          <AuditMethodDiagram />
        </section>
        <section className="presentation-slide">
          <h3>Key metrics</h3>
          <ul className="presentation-stats">
            <li>{formatCount(headline.pairwiseCount)} baseline pairwise comparisons</li>
            <li>{formatCount(headline.flaggedCount)} baseline audit signals flagged</li>
            {headline.usesBaselineHeadline ? (
              <li>{formatCount(headline.flaggedCountAllModes)} flagged across all prompt modes</li>
            ) : null}
            <li>{formatCount(bundle.highPriorityCount)} high-priority review items</li>
            <li>{formatCount(addressProxyOutputs)} address-proxy outputs (strict-excluded bucket)</li>
          </ul>
        </section>
        <section className="presentation-slide">
          <h3>Top findings (audit signals)</h3>
          <ul className="compact-list">
            {topFindings.map((t) => (
              <li key={t.id}><strong>{t.headline}</strong> — {t.caution}</li>
            ))}
          </ul>
        </section>
        <section className="presentation-slide">
          <h3>Cross-prompt &amp; variant coverage</h3>
          <ul className="compact-list">
            <li>{formatCount(bundle.crossPromptComparisons.length)} cross-prompt comparison rows exported</li>
            <li>{formatCount(baseScenarioCount)} base scenarios in variant matrix</li>
            <li>{bundle.caseReviewSplit ? "Per-record review JSON (lazy load enabled)" : "Monolithic review export"}</li>
          </ul>
        </section>
        <section className="presentation-slide">
          <h3>Example comparison</h3>
          <ComparisonExample />
          {example ? (
            <button type="button" className="btn btn-secondary btn-sm" onClick={onOpenCase}>
              Open live case: {String(example.case_id)}
            </button>
          ) : null}
        </section>
        <section className="presentation-slide">
          <h3>Limitations & next steps</h3>
          <ul className="compact-list">
            <li>Metrics are audit signals — not proof of unlawful discrimination.</li>
            <li>Human legal expert review required.</li>
            <li>Address-proxy variants analyzed in a separate bucket from strict demographic rates.</li>
            <li>Deploy full-text dashboard only behind access control.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
