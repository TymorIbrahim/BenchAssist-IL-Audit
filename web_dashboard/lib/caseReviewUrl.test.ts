import { describe, expect, it } from "vitest";
import { caseReviewFiltersFromUrl, caseReviewFiltersToUrl } from "./caseReviewUrl";
import { DEFAULT_CASE_REVIEW_FILTERS } from "./detentionCaseReview";

describe("caseReviewUrl", () => {
  it("round-trips flagged-only and review filters", () => {
    const filters = { ...DEFAULT_CASE_REVIEW_FILTERS, flaggedOnly: true, variantType: "arab_name_he", reviewPriority: "high" };
    const qs = caseReviewFiltersToUrl(filters, { tab: "case-review", reviewId: "D001::v1::baseline" });
    const params = new URLSearchParams(qs);
    const parsed = caseReviewFiltersFromUrl(params);
    expect(parsed.flaggedOnly).toBe(true);
    expect(parsed.variantType).toBe("arab_name_he");
    expect(parsed.reviewPriority).toBe("high");
    expect(params.get("review_id")).toBe("D001::v1::baseline");
  });

  it("round-trips analysis bucket filter", () => {
    const filters = { ...DEFAULT_CASE_REVIEW_FILTERS, analysisBucket: "address_proxy" as const };
    const qs = caseReviewFiltersToUrl(filters, {});
    const parsed = caseReviewFiltersFromUrl(new URLSearchParams(qs));
    expect(parsed.analysisBucket).toBe("address_proxy");
  });
});
