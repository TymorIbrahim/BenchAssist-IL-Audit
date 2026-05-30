import type { CaseReviewFilters } from "./detentionCaseReview";

export function caseReviewFiltersFromUrl(params: URLSearchParams): Partial<CaseReviewFilters> {
  const out: Partial<CaseReviewFilters> = {};
  const pick = (key: keyof CaseReviewFilters, param: string) => {
    const v = params.get(param);
    if (v) (out as Record<string, string>)[key] = v;
  };
  pick("reviewPriority", "cr_priority");
  pick("issueType", "cr_issue");
  pick("promptMode", "cr_prompt");
  pick("variantType", "cr_variant");
  pick("baseCaseId", "cr_base");
  pick("protectedAttribute", "cr_protected");
  pick("strictEligible", "cr_strict");
  pick("identityLeakage", "cr_identity");
  pick("unsupportedInference", "cr_unsupported");
  pick("decision", "cr_decision");
  pick("search", "cr_search");
  const local = params.get("cr_local");
  if (local === "reviewed" || local === "unreviewed") out.localReview = local;
  if (params.get("cr_flagged") === "1") out.flaggedOnly = true;
  if (params.get("cr_focus") === "1") out.focusMode = true;
  return out;
}

export function caseReviewFiltersToUrl(
  filters: CaseReviewFilters,
  opts?: { reviewId?: string; tab?: string },
): string {
  const qs = new URLSearchParams();
  if (opts?.tab) qs.set("tab", opts.tab);
  if (opts?.reviewId) qs.set("review_id", opts.reviewId);
  if (filters.reviewPriority) qs.set("cr_priority", filters.reviewPriority);
  if (filters.issueType) qs.set("cr_issue", filters.issueType);
  if (filters.promptMode) qs.set("cr_prompt", filters.promptMode);
  if (filters.variantType) qs.set("cr_variant", filters.variantType);
  if (filters.baseCaseId) qs.set("cr_base", filters.baseCaseId);
  if (filters.protectedAttribute) qs.set("cr_protected", filters.protectedAttribute);
  if (filters.strictEligible) qs.set("cr_strict", filters.strictEligible);
  if (filters.identityLeakage) qs.set("cr_identity", filters.identityLeakage);
  if (filters.unsupportedInference) qs.set("cr_unsupported", filters.unsupportedInference);
  if (filters.decision) qs.set("cr_decision", filters.decision);
  if (filters.search) qs.set("cr_search", filters.search);
  if (filters.localReview !== "all") qs.set("cr_local", filters.localReview);
  if (filters.flaggedOnly) qs.set("cr_flagged", "1");
  if (filters.focusMode) qs.set("cr_focus", "1");
  return qs.toString();
}
