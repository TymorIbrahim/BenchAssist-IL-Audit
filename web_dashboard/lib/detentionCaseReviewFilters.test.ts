import { describe, expect, it } from "vitest";
import {
  DEFAULT_CASE_REVIEW_FILTERS,
  filterCaseReviewRecords,
  matchesCaseReviewIssueKey,
  pickReviewRecordId,
  type CaseReviewRecord,
} from "./detentionCaseReview";

const record = (overrides: Partial<CaseReviewRecord>): CaseReviewRecord =>
  ({
    review_record_id: "D001::D001-arab_name_he::baseline",
    base_case_id: "D001",
    variant_id: "D001-arab_name_he",
    prompt_mode: "baseline",
    is_flagged: true,
    review_priority: "high",
    issue_types: [],
    variant_type: "arab_name_he",
    protected_attribute_tested: "arab_name",
    base_case: {},
    variant_case: { variant_label: "arab name he" },
    neutral_output: {},
    variant_output: {},
    diff: {},
    review_guidance: { plain_language_summary: "", why_flagged: "", legal_review_questions: [], caution_note: "" },
    ...overrides,
  }) as CaseReviewRecord;

describe("case review filters", () => {
  it("matches structured issue keys from diff fields", () => {
    const actionShift = record({ diff: { recommended_action_shift: "stricter recommendation" } });
    expect(matchesCaseReviewIssueKey(actionShift, "recommended_action")).toBe(true);
    expect(matchesCaseReviewIssueKey(actionShift, "identity")).toBe(false);
  });

  it("filters records by issue key instead of substring on issue_types", () => {
    const rows = [
      record({ review_record_id: "a::baseline", diff: { recommended_action_shift: "stricter recommendation" } }),
      record({ review_record_id: "b::baseline", diff: { identity_leakage_flag: true } }),
    ];
    const filtered = filterCaseReviewRecords(
      rows,
      { ...DEFAULT_CASE_REVIEW_FILTERS, issueType: "recommended_action" },
      {},
    );
    expect(filtered).toHaveLength(1);
    expect(filtered[0].review_record_id).toBe("a::baseline");
  });

  it("prefers baseline review ids when navigating from all-mode index lists", () => {
    const ids = [
      "D001::D001-arab_name_he::fairness_aware",
      "D001::D001-arab_name_he::baseline",
    ];
    const index = [
      { review_record_id: ids[0], prompt_mode: "fairness_aware", is_flagged: true },
      { review_record_id: ids[1], prompt_mode: "baseline", is_flagged: true },
    ];
    expect(pickReviewRecordId(ids, { promptMode: "baseline" }, index as never)).toBe(ids[1]);
  });

  it("filters records by analysis bucket", () => {
    const rows = [
      record({ review_record_id: "a::baseline", analysis_bucket: "strict_demographic" as const }),
      record({
        review_record_id: "b::baseline",
        analysis_bucket: "address_proxy" as const,
        variant_type: "address_affluent_center",
      }),
    ];
    const filtered = filterCaseReviewRecords(
      rows,
      { ...DEFAULT_CASE_REVIEW_FILTERS, analysisBucket: "address_proxy" },
      {},
    );
    expect(filtered).toHaveLength(1);
    expect(filtered[0].review_record_id).toBe("b::baseline");
  });
});
