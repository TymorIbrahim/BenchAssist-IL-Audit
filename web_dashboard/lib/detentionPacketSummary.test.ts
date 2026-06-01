import { describe, expect, it } from "vitest";
import { buildPacketSummaryRows, packetSummaryStats } from "./detentionPacketSummary";
import type { CaseReviewRecord } from "./detentionCaseReview";

const sample: CaseReviewRecord = {
  review_record_id: "D001::D001-jewish_name_he::baseline",
  base_case_id: "D001",
  base_case_title: "Test",
  variant_id: "D001-jewish_name_he",
  prompt_mode: "baseline",
  dataset_mode: "synthetic_counterfactual",
  counterfactual_strength: "strict",
  use_for_strict_bias_rates: true,
  review_priority: "high",
  is_flagged: true,
  issue_types: [],
  variant_type: "jewish_name_he",
  analysis_bucket: "strict_demographic",
  base_case: { full_case_text: "", structured_facts: {}, prompt_mode: "baseline" },
  variant_case: { variant_label: "jewish name he", full_case_text: "", structured_facts: {}, prompt_mode: "baseline" },
  neutral_output: { dangerousness_level: "low", reasoning_text: "" },
  variant_output: { dangerousness_level: "medium", reasoning_text: "" },
  diff: { diff_summary: "" },
  cross_prompt: { modes_available: [], variant_outputs_by_mode: {}, neutral_outputs_by_mode: {}, cross_prompt_instability: [] },
  review_guidance: { why_flagged: "test", plain_language_summary: "", legal_review_questions: [], caution_note: "" },
};

describe("detentionPacketSummary", () => {
  it("builds counsel-facing summary rows", () => {
    const rows = buildPacketSummaryRows([sample], {});
    expect(rows[0].dangerousness).toBe("low → medium");
    expect(rows[0].flagged).toBe(true);
  });

  it("aggregates packet stats", () => {
    const stats = packetSummaryStats([sample]);
    expect(stats.total).toBe(1);
    expect(stats.flagged).toBe(1);
    expect(stats.high).toBe(1);
  });
});
