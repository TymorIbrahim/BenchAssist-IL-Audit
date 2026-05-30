"use client";

import { Card } from "@/components/Card";
import type { CaseReviewRecord } from "@/lib/detentionCaseReview";
import { caseReviewKey } from "@/lib/detentionCaseReview";
import type { ReviewRecord } from "@/lib/detentionReview";

export interface ReviewProgress {
  totalFlagged: number;
  reviewed: number;
  includeInReport: number;
  inPacket: number;
  possibleConcern: number;
}

export function computeReviewProgress(
  records: CaseReviewRecord[],
  reviewState: Record<string, ReviewRecord>,
  packetIds: string[],
  indexFlaggedCount?: number,
): ReviewProgress {
  const flagged = records.filter((r) => r.is_flagged);
  const totalFlagged = flagged.length || indexFlaggedCount || 0;
  let reviewed = 0;
  let includeInReport = 0;
  let possibleConcern = 0;
  const keys = records.length
    ? flagged.map((r) => caseReviewKey(r))
    : Object.keys(reviewState);
  for (const key of keys) {
    const st = reviewState[key];
    if (st?.reviewed || (st?.decision && st.decision !== "not_reviewed")) reviewed += 1;
    if (st?.decision === "include_in_report") includeInReport += 1;
    if (st?.decision === "possible_concern") possibleConcern += 1;
  }
  return {
    totalFlagged,
    reviewed,
    includeInReport,
    inPacket: packetIds.length,
    possibleConcern,
  };
}

export function ReviewProgressPanel({ progress, pendingLoad }: { progress: ReviewProgress; pendingLoad?: boolean }) {
  const pct = progress.totalFlagged ? Math.round((progress.reviewed / progress.totalFlagged) * 100) : 0;
  return (
    <Card title="Review progress">
      <div className="review-progress-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="review-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <p className="muted">
        {progress.reviewed}/{progress.totalFlagged} flagged reviewed locally ({pct}%)
        · {progress.includeInReport} marked for report
        · {progress.possibleConcern} possible concern
        · {progress.inPacket} in packet
        {pendingLoad ? " · full records still loading" : ""}
      </p>
    </Card>
  );
}
