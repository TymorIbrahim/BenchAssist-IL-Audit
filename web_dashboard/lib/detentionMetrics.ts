import type { DetentionDashboardBundle } from "./detentionData";
import { caseReviewKey } from "./detentionCaseReview";
import type { JsonRecord } from "./types";
import { str } from "./format";

export function detentionDataModeLabel(bundle: Pick<DetentionDashboardBundle, "isMock" | "dataStatus">): string {
  if (bundle.isMock) return "Mock";
  switch (bundle.dataStatus) {
    case "gemini_expanded_full":
      return "Gemini expanded full";
    case "gemini_minimal_address":
      return "Gemini minimal address";
    case "gemini_full":
      return "Gemini full";
    case "gemini":
      return "Gemini pilot";
    case "pilot":
      return "Pilot";
    case "final":
      return "Final";
    default:
      return "Awaiting export";
  }
}

export function detentionDataModeBadge(bundle: Pick<DetentionDashboardBundle, "isMock" | "dataStatus">): string {
  if (bundle.isMock) return "Mock data";
  switch (bundle.dataStatus) {
    case "gemini_expanded_full":
      return "Gemini expanded full";
    case "gemini_minimal_address":
      return "Gemini minimal address";
    case "gemini_full":
      return "Gemini full";
    case "gemini":
      return "Gemini pilot";
    case "pilot":
      return "Pilot corpus";
    default:
      return "Exported data";
  }
}

export function uniquePromptModes(rows: JsonRecord[]): string[] {
  const modes = new Set<string>();
  for (const row of rows) {
    const mode = str(row.prompt_mode);
    if (mode) modes.add(mode);
  }
  return [...modes].sort();
}

export function isMultiPromptModeRun(
  bundle: Pick<DetentionDashboardBundle, "pairwise" | "dataStatus" | "overview">,
): boolean {
  if (bundle.dataStatus === "gemini_expanded_full") return true;
  if (bundle.dataStatus === "gemini_minimal_address") return true;
  if (bundle.overview.minimal_address_run === true) return true;
  return uniquePromptModes(bundle.pairwise).length > 1;
}

export function filterRowsByPromptMode(rows: JsonRecord[], promptMode: string): JsonRecord[] {
  if (!promptMode) return rows;
  return rows.filter((row) => str(row.prompt_mode || "baseline") === promptMode);
}

export interface DetentionHeadlineMetrics {
  pairwiseCount: number;
  flaggedCount: number;
  pairwiseCountAllModes: number;
  flaggedCountAllModes: number;
  usesBaselineHeadline: boolean;
}

export function detentionHeadlineMetrics(bundle: DetentionDashboardBundle): DetentionHeadlineMetrics {
  const pairwiseCountAllModes = bundle.pairwise.length;
  const flaggedCountAllModes = bundle.flagged.length;
  const multi = isMultiPromptModeRun(bundle);
  const baselinePairwise = Number(bundle.overview.n_pairwise_comparisons);
  const baselineFlagged = Number(bundle.overview.n_flagged_comparisons);
  const hasBaselineOverview = multi && baselinePairwise > 0 && baselineFlagged >= 0;

  return {
    pairwiseCount: hasBaselineOverview ? baselinePairwise : pairwiseCountAllModes,
    flaggedCount: hasBaselineOverview ? baselineFlagged : flaggedCountAllModes,
    pairwiseCountAllModes: Number(bundle.overview.n_pairwise_comparisons_all_modes) || pairwiseCountAllModes,
    flaggedCountAllModes: Number(bundle.overview.n_flagged_comparisons_all_modes) || flaggedCountAllModes,
    usesBaselineHeadline: hasBaselineOverview,
  };
}

export function defaultAuditPromptMode(
  bundle: Pick<DetentionDashboardBundle, "pairwise" | "dataStatus" | "overview">,
): string {
  return isMultiPromptModeRun(bundle) ? "baseline" : "";
}

export function findCaseReviewTarget(
  bundle: DetentionDashboardBundle,
  caseId: string,
  variantId: string,
  promptMode = "baseline",
): { reviewId: string; variantType: string } | null {
  const records = bundle.caseReviewRecords.filter(
    (r) => r.base_case_id === caseId && r.variant_id === variantId,
  );
  const indexEntries = bundle.caseReviewIndex.filter(
    (e) => e.base_case_id === caseId && e.variant_id === variantId,
  );
  const record =
    records.find((r) => str(r.prompt_mode) === promptMode)
    ?? records.find((r) => str(r.prompt_mode) === "baseline")
    ?? records[0];
  if (record) {
    return { reviewId: caseReviewKey(record), variantType: record.variant_type };
  }
  const indexEntry =
    indexEntries.find((e) => str(e.prompt_mode) === promptMode)
    ?? indexEntries.find((e) => str(e.prompt_mode) === "baseline")
    ?? indexEntries[0];
  if (indexEntry) {
    return { reviewId: indexEntry.review_record_id, variantType: indexEntry.variant_type };
  }
  return null;
}
