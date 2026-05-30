import { describe, expect, it } from "vitest";
import { buildExecutiveFindingsFromIndex, groupIndexByIssue } from "./detentionIndexFindings";
import type { CaseReviewIndexEntry } from "./detentionCaseReview";

const sample: CaseReviewIndexEntry[] = [
  {
    review_record_id: "r1",
    base_case_id: "C1",
    base_case_title: "Case 1",
    variant_id: "V1",
    variant_type: "arab_name",
    prompt_mode: "baseline",
    is_flagged: true,
    review_priority: "high",
    issue_types: [],
    issue_flags: { identity: true, dangerousness: true },
  },
  {
    review_record_id: "r2",
    base_case_id: "C1",
    base_case_title: "Case 1",
    variant_id: "V2",
    variant_type: "arab_name",
    prompt_mode: "baseline",
    is_flagged: true,
    review_priority: "medium",
    issue_types: [],
    issue_flags: { identity: true },
  },
  {
    review_record_id: "r3",
    base_case_id: "C2",
    base_case_title: "Case 2",
    variant_id: "V3",
    variant_type: "broken_hebrew",
    prompt_mode: "baseline",
    is_flagged: false,
    review_priority: "low",
    issue_types: [],
  },
];

describe("buildExecutiveFindingsFromIndex", () => {
  it("groups identity leakage from issue_flags", () => {
    const findings = buildExecutiveFindingsFromIndex(sample);
    expect(findings.some((f) => f.id === "identity-leakage")).toBe(true);
    const identity = findings.find((f) => f.id === "identity-leakage");
    expect(identity?.count).toBe(2);
  });
});

describe("groupIndexByIssue", () => {
  it("returns only non-empty issue groups", () => {
    const groups = groupIndexByIssue(sample);
    expect(groups.some((g) => g.key === "identity")).toBe(true);
    expect(groups.find((g) => g.key === "identity")?.recordIds).toEqual(["r1", "r2"]);
    expect(groups.every((g) => g.recordIds.length > 0)).toBe(true);
  });
});
