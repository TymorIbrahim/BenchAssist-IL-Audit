"use client";

export function ExampleCard({
  title,
  children,
  onSeeExample,
  linkLabel = "See example",
}: {
  title: string;
  children: React.ReactNode;
  onSeeExample?: () => void;
  linkLabel?: string;
}) {
  return (
    <article className="example-card">
      <h4>{title}</h4>
      <div className="example-card-body">{children}</div>
      {onSeeExample ? (
        <button type="button" className="btn btn-secondary btn-sm example-card-action" onClick={onSeeExample}>
          {linkLabel}
        </button>
      ) : null}
    </article>
  );
}

export function ComparisonExample() {
  return (
    <div className="comparison-example-grid">
      <div className="comparison-example-col">
        <span className="comparison-example-label">Neutral</span>
        <dl className="comparison-example-dl">
          <div><dt>Dangerousness</dt><dd>medium</dd></div>
          <div><dt>Obstruction</dt><dd>low</dd></div>
          <div><dt>Action</dt><dd>release with conditions</dd></div>
        </dl>
      </div>
      <div className="comparison-example-arrow">→</div>
      <div className="comparison-example-col comparison-example-col-variant">
        <span className="comparison-example-label">Variant (Arabic input)</span>
        <dl className="comparison-example-dl">
          <div className="field-changed"><dt>Dangerousness</dt><dd>high</dd></div>
          <div><dt>Obstruction</dt><dd>low</dd></div>
          <div><dt>Action</dt><dd>detention extension</dd></div>
        </dl>
      </div>
      <p className="comparison-example-result">Potentially relevant shift — flagged for legal review</p>
    </div>
  );
}
