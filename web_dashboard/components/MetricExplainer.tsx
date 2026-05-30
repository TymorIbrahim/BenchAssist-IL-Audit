"use client";

import { scrollToSection } from "@/lib/navigation";
import { getMetricDefinition, interpretationForMetric } from "@/lib/metricDefinitions";
import { formatRate } from "@/lib/format";

export function MetricExplainer({
  metricKey,
  value,
}: {
  metricKey: string;
  value?: unknown;
}) {
  const def = getMetricDefinition(metricKey);
  if (!def) return null;

  return (
    <div className="metric-explainer" aria-live="polite">
      <h4>{def.label}</h4>
      {value !== undefined ? <p className="metric-explainer-value">Current rate: {formatRate(value)}</p> : null}
      <p><strong>What this means:</strong> {def.plainMeaning}</p>
      <p><strong>Why this matters:</strong> {def.whyItMatters}</p>
      <p><strong>How to interpret:</strong> {interpretationForMetric(metricKey)}</p>
      <p className="metric-caution"><strong>Caution:</strong> {def.caution}</p>
    </div>
  );
}

export function ReviewWorkflow() {
  const steps = [
    { n: 1, title: "Understand the audit", text: "Read how synthetic cases and counterfactual variants were built.", section: "audit-story", action: "Go to audit story" },
    { n: 2, title: "Review main signals", text: "Start with Main Findings to see which variant types produced the most audit signals.", section: "main-findings", action: "View main findings" },
    { n: 3, title: "Inspect flagged cases", text: "Triage cases flagged for legal review — not labeled as biased.", section: "flagged-cases", action: "Open flagged cases" },
    { n: 4, title: "Compare neutral vs variant", text: "Use Inspect a case for side-by-side memo comparison.", section: "case-explorer", action: "Open case explorer" },
    { n: 5, title: "Check validity & safety", text: "Review validity, stereotypes, and hallucination sections.", section: "counterfactual-validity", action: "Check validity" },
    { n: 6, title: "Download reports", text: "Export human review template and written audit reports.", section: "human-review", action: "Human review workspace" },
  ];

  return (
    <nav className="review-workflow" aria-label="Recommended review workflow">
      <h3>Guided review path</h3>
      <p className="muted">Follow these steps to explore the audit like a legal reviewer.</p>
      <ol className="workflow-steps">
        {steps.map((s) => (
          <li key={s.n} className="workflow-step">
            <div className="workflow-step-num">{s.n}</div>
            <div>
              <strong>{s.title}</strong>
              <p>{s.text}</p>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => scrollToSection(s.section)}>
                {s.action}
              </button>
            </div>
          </li>
        ))}
      </ol>
    </nav>
  );
}
