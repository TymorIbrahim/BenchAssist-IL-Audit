import { describe, expect, it } from "vitest";
import {
  dangerousnessPairLabel,
  defaultWhyFlagged,
  displayWhyFlagged,
  formatOutputValue,
  normalizeCaseReviewRecord,
  shortQueueIssueLabel,
  type CaseReviewRecord,
} from "./detentionCaseReview";

const baseRecord: CaseReviewRecord = {
  review_record_id: "D008::D008-jewish_name_he::baseline",
  use_case: "detention",
  data_status: "gemini_full",
  base_case_id: "D008",
  base_case_title: "Test",
  variant_id: "D008-jewish_name_he",
  prompt_mode: "baseline",
  dataset_mode: "synthetic_counterfactual",
  counterfactual_strength: "strict",
  use_for_strict_bias_rates: true,
  review_priority: "low",
  is_flagged: false,
  issue_types: [],
  variant_type: "jewish_name_he",
  protected_attribute_tested: "jewish_name",
  base_case: {},
  variant_case: { variant_label: "jewish name he" },
  neutral_output: { recommended_duration_days: null, dangerousness_level: "low" },
  variant_output: { recommended_duration_days: null, dangerousness_level: "medium" },
  diff: { diff_summary: "No structured output field changes detected." },
  review_guidance: {
    why_flagged: "Flagged for legal review: nan",
    plain_language_summary: "summary",
    legal_review_questions: [],
    caution_note: "caution",
  },
};

describe("case review display helpers", () => {
  it("sanitizes nan why_flagged text", () => {
    const normalized = normalizeCaseReviewRecord(baseRecord);
    expect(displayWhyFlagged(normalized)).toBe("Not flagged — included for controlled-comparison review.");
  });

  it("formats null output values clearly", () => {
    expect(formatOutputValue(null)).toBe("Not specified");
    expect(formatOutputValue("nan")).toBe("Not specified");
  });

  it("falls back to diff summary for flagged records without issue types", () => {
    const flagged = normalizeCaseReviewRecord({
      ...baseRecord,
      is_flagged: true,
      review_guidance: { ...baseRecord.review_guidance, why_flagged: "" },
      diff: { diff_summary: "Recommended action changed", recommended_action_shift: "stricter recommendation" },
    });
    expect(defaultWhyFlagged(flagged)).toContain("Recommended action changed");
  });

  it("formats dangerousness pair label", () => {
    expect(dangerousnessPairLabel(baseRecord)).toBe("low → medium");
  });

  it("shortens queue issue labels", () => {
    expect(shortQueueIssueLabel("possible concern: higher dangerousness vs neutral")).toBe("Dangerousness Δ");
  });
});
