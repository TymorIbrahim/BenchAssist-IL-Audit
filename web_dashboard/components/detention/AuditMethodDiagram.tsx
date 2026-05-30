"use client";

export function AuditMethodDiagram() {
  return (
    <div className="audit-method-diagram" aria-label="Audit method at a glance">
      <div className="audit-lane audit-lane-primary">
        <h4 className="audit-lane-title">Synthetic strict-fairness audit</h4>
        <div className="audit-lane-flow">
          {[
            "Synthetic cases",
            "Counterfactual variants",
            "Prompt modes",
            "Structured outputs",
            "Pairwise comparisons",
            "Audit signals",
            "Legal expert review",
          ].map((step, i, arr) => (
            <div key={step} className="audit-flow-step">
              <span className="audit-flow-node">{step}</span>
              {i < arr.length - 1 ? <span className="audit-flow-connector" aria-hidden>→</span> : null}
            </div>
          ))}
        </div>
      </div>
      <div className="audit-lane audit-lane-secondary">
        <h4 className="audit-lane-title">Real-case layer (separate)</h4>
        <div className="audit-lane-flow audit-lane-flow-wrap">
          {[
            "Real Israeli public cases",
            "Legal realism review",
            "Grounding / reliability",
            "Expert case review",
            "Not in strict fairness rates",
          ].map((step, i, arr) => (
            <div key={step} className="audit-flow-step">
              <span className="audit-flow-node audit-flow-node-secondary">{step}</span>
              {i < arr.length - 1 ? <span className="audit-flow-connector" aria-hidden>→</span> : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
