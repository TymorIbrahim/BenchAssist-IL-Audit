import { describe, expect, it } from "vitest";
import { buildDetentionTakeaways } from "./detentionTakeaways";

describe("buildDetentionTakeaways", () => {
  it("prefers action-shift headline when action delta dominates", () => {
    const takeaways = buildDetentionTakeaways({
      groupSummary: [
        {
          variant_type: "jewish_name_he",
          mean_dangerousness_delta: 0,
          mean_action_delta: 0.35,
          flagged_rate: 0.4,
          n_comparisons: 8,
          protected_attribute_tested: "jewish_name",
        },
      ],
      flagged: [],
      isMock: false,
      dataStatus: "gemini_full",
    });
    expect(takeaways[0]?.headline).toMatch(/recommended-action shifts/i);
  });
});
