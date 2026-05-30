import { buildDiffSummary, reasoningDiffNotes } from "@/lib/diffSummary";
import { Card } from "./Card";
import { ExpandableText } from "./ExpandableText";
import type { JsonRecord } from "@/lib/types";
import { str, textDir } from "@/lib/format";

export function WhatChangedPanel({ row }: { row: JsonRecord | null }) {
  if (!row) return null;

  const diffs = buildDiffSummary(row);
  const notes = reasoningDiffNotes(row);
  const neutralReason = str(row.neutral_reasoning_text);
  const variantReason = str(row.reasoning_text ?? row.variant_reasoning_text);

  return (
    <Card title="What changed?">
      <p className="muted">Compact diff summary for legal review. Neutral labels — not a verdict.</p>
      <table className="diff-table">
        <thead>
          <tr><th>Field</th><th>Summary</th></tr>
        </thead>
        <tbody>
          {diffs.map((d) => (
            <tr key={d.field} className={d.changed ? "diff-changed" : ""}>
              <td>{d.field}</td>
              <td>{d.summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="reasoning-diff">
        <h4>Reasoning comparison</h4>
        <div className="two-col">
          <div>
            <strong>Neutral</strong>
            {notes.neutralHits.length ? <p className="keyword-hits">Keywords: {notes.neutralHits.join(", ")}</p> : null}
            <ExpandableText text={neutralReason || "—"} dir={textDir(neutralReason)} />
          </div>
          <div>
            <strong>Variant</strong>
            {notes.variantHits.length ? <p className="keyword-hits">Keywords: {notes.variantHits.join(", ")}</p> : null}
            <ExpandableText text={variantReason || "—"} dir={textDir(variantReason)} />
          </div>
        </div>
      </div>
    </Card>
  );
}
