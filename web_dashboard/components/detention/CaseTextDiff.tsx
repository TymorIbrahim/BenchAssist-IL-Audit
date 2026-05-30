"use client";

import { diffHasChanges, diffLines, type DiffLine } from "@/lib/textDiff";
import { dirForText } from "@/lib/detentionCaseReview";

function DiffLineRow({ line }: { line: DiffLine }) {
  if (line.kind === "same") {
    return (
      <div className="text-diff-line text-diff-same">
        <span>{line.base}</span>
      </div>
    );
  }
  if (line.kind === "changed") {
    return (
      <div className="text-diff-line text-diff-changed">
        <div className="text-diff-col"><span className="text-diff-label">Base</span><span>{line.base}</span></div>
        <div className="text-diff-col"><span className="text-diff-label">Variant</span><span>{line.variant}</span></div>
      </div>
    );
  }
  if (line.kind === "added") {
    return (
      <div className="text-diff-line text-diff-added">
        <span className="text-diff-label">+ Variant</span>
        <span>{line.variant}</span>
      </div>
    );
  }
  return (
    <div className="text-diff-line text-diff-removed">
      <span className="text-diff-label">− Base</span>
      <span>{line.base}</span>
    </div>
  );
}

export function CaseTextDiff({ baseText, variantText }: { baseText: string; variantText: string }) {
  const lines = diffLines(baseText, variantText);
  const hasChanges = diffHasChanges(lines);
  const dir = dirForText(baseText || variantText);

  if (!hasChanges) {
    return <p className="muted">No line-level text differences detected (case texts may be identical).</p>;
  }

  return (
    <div className="text-diff-panel" dir={dir}>
      <p className="muted text-diff-caption">Line-level diff — changed lines highlighted. Legally relevant facts are intended to remain constant in strict counterfactuals.</p>
      <div className="text-diff-lines">
        {lines.filter((l) => l.kind !== "same").slice(0, 40).map((line, i) => (
          <DiffLineRow key={`${line.kind}-${i}`} line={line} />
        ))}
      </div>
      {lines.filter((l) => l.kind !== "same").length > 40 ? (
        <p className="muted">Showing first 40 changed lines. Open full case text below for complete view.</p>
      ) : null}
    </div>
  );
}
