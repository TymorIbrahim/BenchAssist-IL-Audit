import {
  analysisBucketLabel,
  caseReviewKey,
  dangerousnessPairLabel,
  type CaseReviewRecord,
} from "./detentionCaseReview";
import type { ReviewRecord } from "./detentionReview";

export type PacketSummaryRow = {
  id: string;
  baseCaseId: string;
  variantLabel: string;
  dangerousness: string;
  flagged: boolean;
  bucket: string;
  priority: string;
  decision: string;
};

export function buildPacketSummaryRows(
  records: CaseReviewRecord[],
  reviewState: Record<string, ReviewRecord>,
): PacketSummaryRow[] {
  return records.map((rec) => {
    const key = caseReviewKey(rec);
    const review = reviewState[key];
    return {
      id: key,
      baseCaseId: rec.base_case_id,
      variantLabel: rec.variant_case.variant_label || rec.variant_type.replace(/_/g, " "),
      dangerousness: dangerousnessPairLabel(rec),
      flagged: rec.is_flagged,
      bucket: analysisBucketLabel(rec.analysis_bucket) || "—",
      priority: rec.review_priority,
      decision: review?.decision ?? "not_reviewed",
    };
  });
}

export function packetSummaryStats(records: CaseReviewRecord[]) {
  const flagged = records.filter((r) => r.is_flagged).length;
  const addressProxy = records.filter((r) => r.analysis_bucket === "address_proxy").length;
  const high = records.filter((r) => r.review_priority === "high").length;
  return { total: records.length, flagged, addressProxy, high };
}
