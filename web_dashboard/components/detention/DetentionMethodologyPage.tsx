"use client";

import { Card } from "@/components/Card";
import { PageHeader } from "@/components/detention/PageHeader";
import { AuditMethodDiagram } from "@/components/detention/AuditMethodDiagram";
import { ExampleCard, ComparisonExample } from "@/components/detention/ExampleCard";
import { DETENTION_METRIC_TIPS } from "@/lib/detentionMetricTips";
import { formatOutputValue, type CaseReviewRecord } from "@/lib/detentionCaseReview";

export function DetentionMethodologyPage({
  onOpenGlossary,
  exampleRecord,
}: {
  onOpenGlossary: () => void;
  exampleRecord?: CaseReviewRecord | null;
}) {
  return (
    <div className="tab-panel methodology-panel">
      <PageHeader title="Methodology" subtitle="How the audit works — synthetic strict fairness vs real-case legal review." />

      <AuditMethodDiagram />

      <div className="method-grid">
        <Card title="Synthetic vs real-case layers">
          <ul className="compact-list">
            <li><strong>Synthetic counterfactuals</strong> — strict fairness audit only.</li>
            <li><strong>Real public legal examples</strong> — qualitative review; excluded from strict rates.</li>
            <li><strong>Mock outputs</strong> — pipeline QA; not findings.</li>
          </ul>
        </Card>
        <Card title="What is a counterfactual?">
          <p>We hold legally relevant facts constant and change only identity, language, or narrative framing to test whether model outputs shift.</p>
        </Card>
        <Card title="Prompt modes">
          <ul className="compact-list">
            <li>Baseline — standard instruction</li>
            <li>Fairness-aware — explicit fairness guidance</li>
            <li>Demographic-blind — avoid demographic inference</li>
          </ul>
        </Card>
        <Card title="Output schema">
          <p>Structured memos: dangerousness, obstruction, reasonable suspicion, investigative necessity, recommended action, duration, alternatives, safeguards, credibility framing, reasoning, evidence needed, limitations.</p>
        </Card>
      </div>

      <section className="section-card">
        <h3>Example comparison</h3>
        {exampleRecord ? (
          <div className="method-example-live">
            <Card title={`${exampleRecord.base_case_id} · ${exampleRecord.variant_case.variant_label}`}>
              <p className="muted">{exampleRecord.review_guidance.plain_language_summary}</p>
              <dl className="meta-dl meta-dl-stack">
                <div><dt>Neutral dangerousness</dt><dd>{formatOutputValue(exampleRecord.neutral_output.dangerousness_level)}</dd></div>
                <div><dt>Variant dangerousness</dt><dd>{formatOutputValue(exampleRecord.variant_output.dangerousness_level)}</dd></div>
                <div><dt>Neutral action</dt><dd>{formatOutputValue(exampleRecord.neutral_output.recommended_action_type)}</dd></div>
                <div><dt>Variant action</dt><dd>{formatOutputValue(exampleRecord.variant_output.recommended_action_type)}</dd></div>
              </dl>
              <p><strong>Review question:</strong> {exampleRecord.review_guidance.legal_review_questions[0]}</p>
              <p className="caution-line">{exampleRecord.review_guidance.caution_note}</p>
            </Card>
          </div>
        ) : (
          <ComparisonExample />
        )}
      </section>

      <details className="methodology-expand">
        <summary>Metrics & audit signals</summary>
        <ul className="compact-list">
          <li>{DETENTION_METRIC_TIPS.dangerousness_shift}</li>
          <li>{DETENTION_METRIC_TIPS.identity_leakage}</li>
          <li>{DETENTION_METRIC_TIPS.unsupported_inference}</li>
          <li>{DETENTION_METRIC_TIPS.strict_fairness}</li>
        </ul>
      </details>

      <details className="methodology-expand">
        <summary>Limitations</summary>
        <ul className="compact-list">
          <li>Name/language/proxy variants have known limits.</li>
          <li>Model outputs are non-binding toy memos.</li>
          <li>Metrics are audit signals — not proof of unlawful discrimination.</li>
          <li>Full-text deployment requires access control.</li>
          <li>Human legal expert review required before any operational use.</li>
        </ul>
      </details>

      <button type="button" className="btn btn-secondary btn-sm" onClick={onOpenGlossary}>Open glossary</button>
    </div>
  );
}
