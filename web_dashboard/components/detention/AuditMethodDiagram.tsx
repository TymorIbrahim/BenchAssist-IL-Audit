"use client";

export function AuditMethodDiagram() {
  return (
    <div className="audit-method-diagram" aria-label="Audit method at a glance">
      <div className="audit-lane audit-lane-primary">
        <h4 className="audit-lane-title">Minimal-schema detention audit</h4>
        <div className="audit-lane-flow">
          {[
            "Slim synthetic corpus",
            "Strict + address-proxy buckets",
            "3 prompt modes",
            "Dangerousness-only flagging",
            "Expert case review",
          ].map((step, i, arr) => (
            <div key={step} className="audit-flow-step">
              <span className="audit-flow-node">{step}</span>
              {i < arr.length - 1 ? <span className="audit-flow-connector" aria-hidden>→</span> : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
