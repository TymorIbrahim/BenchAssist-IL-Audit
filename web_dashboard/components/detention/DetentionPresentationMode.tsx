"use client";

import { ComparisonExample } from "@/components/detention/ExampleCard";
import { AuditMethodDiagram } from "@/components/detention/AuditMethodDiagram";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import type { DetentionTakeaway } from "@/lib/detentionTakeaways";
import { RESEARCH_QUESTION } from "@/lib/detentionStory";
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
  const topFindings = takeaways.slice(0, 3);
  const example = bundle.flagged[0];
  const realCaseOutputs = bundle.overview.n_real_case_review_outputs ?? bundle.realCaseExamples.length;

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
            <li>{formatCount(bundle.pairwise.length)} pairwise comparisons</li>
            <li>{formatCount(bundle.flagged.length)} audit signals flagged</li>
            <li>{formatCount(bundle.highPriorityCount)} high-priority review items</li>
            <li>{formatCount(realCaseOutputs)} real-case model outputs ({formatCount(bundle.realCaseExamples.length)} fulltext examples)</li>
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
            <li>{formatCount(new Set(bundle.pairwise.map((r) => String(r.case_id))).size)} base scenarios in variant matrix</li>
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
            <li>Real cases excluded from strict synthetic fairness rates.</li>
            <li>Deploy full-text dashboard only behind access control.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
