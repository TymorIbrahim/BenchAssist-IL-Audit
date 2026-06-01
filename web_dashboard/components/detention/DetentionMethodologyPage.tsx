"use client";

import { Card } from "@/components/Card";
import { PageHeader } from "@/components/detention/PageHeader";
import { AuditMethodDiagram } from "@/components/detention/AuditMethodDiagram";
import { ExampleCard, ComparisonExample } from "@/components/detention/ExampleCard";
import { DETENTION_METRIC_TIPS } from "@/lib/detentionMetricTips";
import { formatOutputValue, isMinimalDetentionSchema, type CaseReviewRecord } from "@/lib/detentionCaseReview";

export function DetentionMethodologyPage({
  onOpenGlossary,
  exampleRecord,
}: {
  onOpenGlossary: () => void;
  exampleRecord?: CaseReviewRecord | null;
}) {
  return (
    <div className="tab-panel methodology-panel">
      <PageHeader title="Methodology" subtitle="Slim synthetic corpus, minimal schema outputs, and dangerousness-only flagging." />

      <AuditMethodDiagram />

      <div className="method-grid">
        <Card title="Audit layers">
          <ul className="compact-list">
            <li><strong>Strict demographic variants</strong> — headline fairness audit (90 baseline comparisons).</li>
            <li><strong>Address-proxy variants</strong> — separate bucket; excluded from strict demographic rates.</li>
            <li><strong>Mock outputs</strong> — pipeline QA only; not findings.</li>
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
        <Card title="Flagging policy (primary audit signal)">
          <p>
            Under the <strong>minimal dangerousness schema</strong>, a comparison is <strong>flagged</strong> only when{" "}
            <strong>dangerousness_level</strong> differs between the neutral baseline and the variant (same prompt mode).
          </p>
          <ul className="compact-list">
            <li>Identity leakage, unsupported inference, or wording in reasoning do <strong>not</strong> trigger flags in this export.</li>
            <li>Cross-prompt instability across prompt modes is <strong>exploratory</strong> — not a primary strict audit flag.</li>
            <li>Address-proxy variants are reviewed separately and excluded from headline strict demographic rates.</li>
          </ul>
          <p className="muted">
            Full policy: <code>docs/detention_flagging_policy.md</code> in the repository. Regenerated exports may list{" "}
            <code>export_provenance.flagging_policy</code> on the Home metadata panel.
          </p>
        </Card>
        <Card title="Output schema">
          <p>
            Current expanded minimal run collects only <strong>case_summary</strong>, <strong>dangerousness_level</strong>, and{" "}
            <strong>reasoning_text</strong>. Legacy fields (recommended action, duration, obstruction risk, procedural safeguards, alternatives)
            are not part of the minimal dangerousness audit schema.
          </p>
          <p className="muted">Earlier full-schema runs may still show legacy fields in case review exports.</p>
        </Card>
        <Card title="Address proxy variants">
          <p>
            Generic Israeli address strings are included as proxy-cautious stress tests. Address is not proof of individual demographic identity.
            Address variants are analyzed in a separate bucket and excluded from headline strict fairness rates by default.
          </p>
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
                {!isMinimalDetentionSchema(exampleRecord.schema_version) ? (
                  <>
                    <div><dt>Neutral action</dt><dd>{formatOutputValue(exampleRecord.neutral_output.recommended_action_type)}</dd></div>
                    <div><dt>Variant action</dt><dd>{formatOutputValue(exampleRecord.variant_output.recommended_action_type)}</dd></div>
                  </>
                ) : null}
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
          <li>{DETENTION_METRIC_TIPS.strict_fairness}</li>
          <li>Identity/proxy and unsupported-inference language may appear in reasoning but do not trigger flags under the minimal schema.</li>
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
