import type { CaseReviewFilters } from "./detentionCaseReview";

export interface CaseReviewFilterPreset {
  id: string;
  label: string;
  patch: Partial<CaseReviewFilters>;
}

export const CASE_REVIEW_FILTER_PRESETS: CaseReviewFilterPreset[] = [
  {
    id: "strict-flagged",
    label: "Flagged · strict demographic",
    patch: { flaggedOnly: true, analysisBucket: "strict_demographic", reviewPriority: "", localReview: "all" },
  },
  {
    id: "address-proxy",
    label: "Address-proxy only",
    patch: { flaggedOnly: false, analysisBucket: "address_proxy", reviewPriority: "", localReview: "all" },
  },
  {
    id: "high-unreviewed",
    label: "High priority · unreviewed",
    patch: { flaggedOnly: true, reviewPriority: "high", localReview: "unreviewed", analysisBucket: "" },
  },
];

export function presetPatchById(id: string | null | undefined): Partial<CaseReviewFilters> | null {
  if (!id) return null;
  const preset = CASE_REVIEW_FILTER_PRESETS.find((p) => p.id === id);
  return preset?.patch ?? null;
}
