"use client";

export function DetentionAuditMap() {
  const steps = [
    { title: "Inputs", desc: "Synthetic counterfactuals + optional real public legal text" },
    { title: "Prompt modes", desc: "Baseline, fairness-aware, demographic-blind, grounded" },
    { title: "Model outputs", desc: "Non-binding detention risk memos" },
    { title: "Metrics", desc: "Audit signals on framing shifts" },
    { title: "Review queue", desc: "Flagged for legal review" },
    { title: "Human legal review", desc: "Required before any external claim" },
  ];

  return (
    <div className="audit-map" aria-label="Audit process map">
      <div className="audit-map-primary">
        {steps.map((s, i) => (
          <div key={s.title} className="audit-map-node">
            <strong>{s.title}</strong>
            <p>{s.desc}</p>
            {i < steps.length - 1 ? <span className="audit-map-arrow">↓</span> : null}
          </div>
        ))}
      </div>
      <div className="audit-map-branches">
        <div className="audit-map-branch">
          <strong>Synthetic controlled audit</strong>
          <p>→ strict fairness audit signals</p>
        </div>
        <div className="audit-map-branch">
          <strong>Real public legal cases</strong>
          <p>→ realism / legal reliability review (excluded from strict rates)</p>
        </div>
      </div>
    </div>
  );
}
