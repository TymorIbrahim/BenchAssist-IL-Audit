"use client";

import { Card } from "@/components/Card";
import { groupIndexByIssue } from "@/lib/detentionIndexFindings";
import type { CaseReviewIndexEntry } from "@/lib/detentionCaseReview";

export function DetentionFindingsByIssueIndex({
  index,
  onReviewCases,
}: {
  index: CaseReviewIndexEntry[];
  onReviewCases: (filter: { issueKey: string; recordIds: string[] }) => void;
}) {
  const groups = groupIndexByIssue(index);
  if (!groups.length) return null;

  return (
    <section className="section-card">
      <h3>Findings by legal issue</h3>
      <p className="muted section-intro">From review index — full detail loads when you open Case Review.</p>
      <div className="findings-issue-grid">
        {groups.map((g) => (
          <Card key={g.key} title={g.label}>
            <p className="muted">{g.explanation}</p>
            <p><strong>{g.recordIds.length}</strong> affected comparison{g.recordIds.length === 1 ? "" : "s"}</p>
            <p className="muted">Top variants: {g.variantTypes.join(", ")}</p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onReviewCases({ issueKey: g.key, recordIds: g.recordIds })}>
              Review these cases
            </button>
          </Card>
        ))}
      </div>
    </section>
  );
}
