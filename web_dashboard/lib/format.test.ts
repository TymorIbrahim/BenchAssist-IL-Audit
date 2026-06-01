import { describe, expect, it } from "vitest";
import { hasMetricDeltaShift, isHighReviewPriority, matchesReviewPriority, normalizeReviewPriority } from "./format";

describe("review priority helpers", () => {
  it("normalizes mixed-case values", () => {
    expect(normalizeReviewPriority("High")).toBe("high");
    expect(normalizeReviewPriority("MEDIUM")).toBe("medium");
  });

  it("matches filters case-insensitively", () => {
    expect(matchesReviewPriority("High", "high")).toBe(true);
    expect(matchesReviewPriority("low", "High")).toBe(false);
  });

  it("detects high priority", () => {
    expect(isHighReviewPriority("High")).toBe(true);
    expect(isHighReviewPriority("medium")).toBe(false);
  });

  it("ignores minimal-schema N/A placeholders for delta shifts", () => {
    expect(hasMetricDeltaShift("not_applicable_under_minimal_dangerousness_schema")).toBe(false);
    expect(hasMetricDeltaShift(1)).toBe(true);
    expect(hasMetricDeltaShift(0)).toBe(false);
  });
});
