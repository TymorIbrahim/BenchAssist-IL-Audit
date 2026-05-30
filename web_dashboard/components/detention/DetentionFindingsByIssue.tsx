"use client";

import { Card } from "@/components/Card";
import { groupRecordsByIssue, type CaseReviewRecord } from "@/lib/detentionCaseReview";

export function DetentionFindingsByIssue({
  records,
  onReviewCases,
}: {
  records: CaseReviewRecord[];
  onReviewCases: (filter: { issueKey: string; recordIds: string[] }) => void;
}) {
  const groups = groupRecordsByIssue(records);
  if (!groups.length) return null;

  return (
    <section className="section-card">
      <h3>Findings by legal issue</h3>
      <p className="muted section-intro">Grouped audit signals with plain-language explanations. Requires human legal review.</p>
      <div className="findings-issue-grid">
        {groups.map((g) => (
          <Card key={g.key} title={g.label}>
            <p className="muted">{g.explanation}</p>
            <p><strong>{g.records.length}</strong> affected comparison{g.records.length === 1 ? "" : "s"}</p>
            <p className="muted">
              Top variants: {[...new Set(g.records.slice(0, 5).map((r) => r.variant_type.replace(/_/g, " ")))].join(", ")}
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onReviewCases({ issueKey: g.key, recordIds: g.records.map((r) => r.review_record_id) })}
            >
              Review these cases
            </button>
          </Card>
        ))}
      </div>
    </section>
  );
}
