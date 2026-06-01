import { describe, expect, it } from "vitest";
import type { DetentionDashboardBundle } from "./detentionData";
import {
  defaultAuditPromptMode,
  detentionDataModeLabel,
  detentionHeadlineMetrics,
  filterRowsByPromptMode,
  isMultiPromptModeRun,
} from "./detentionMetrics";

function miniBundle(overrides: Partial<DetentionDashboardBundle> = {}): DetentionDashboardBundle {
  return {
    manifest: { timestamp: "t", run_label: "x" } as DetentionDashboardBundle["manifest"],
    dataAccessPolicy: {},
    overview: {},
    pairwise: [],
    addressProxyPairwise: [],
    addressProxyFlagged: [],
    groupSummary: [],
    flagged: [],
    realCaseExamples: [],
    realCaseQuality: null,
    sourceManifest: null,
    syntheticQa: null,
    mockRunSummary: null,
    reports: [],
    crossPromptComparisons: [],
    crossPromptModeSummary: null,
    mitigation: [],
    statisticalEffects: [],
    statisticalTests: [],
    statisticalTestsAll: [],
    hallucinationGroup: [],
    hallucinationPer: [],
    caseReviewRecords: [],
    caseReviewIndex: [],
    caseReviewMeta: null,
    caseReviewIndexCount: 0,
    caseReviewLoaded: false,
    caseReviewSplit: false,
    dataStatus: "empty",
    hasFullText: false,
    missingFiles: [],
    isMock: false,
    strictEligibleCount: 0,
    highPriorityCount: 0,
    validityRows: [],
    validitySummary: [],
    validityCalibration: null,
    overviewUncertainty: null,
    humanReviewTemplate: [],
    fullMetricSummary: [],
    exportProvenance: null,
    ...overrides,
  };
}

describe("detentionMetrics", () => {
  it("labels expanded full runs", () => {
    expect(detentionDataModeLabel({ isMock: false, dataStatus: "gemini_expanded_full" })).toBe(
      "Gemini expanded full",
    );
  });

  it("defaults audit prompt mode to baseline for multi-mode exports", () => {
    const bundle = miniBundle({
      dataStatus: "gemini_expanded_full",
      pairwise: [
        { case_id: "D1", prompt_mode: "baseline" },
        { case_id: "D1", prompt_mode: "fairness_aware" },
      ],
    });
    expect(isMultiPromptModeRun(bundle)).toBe(true);
    expect(defaultAuditPromptMode(bundle)).toBe("baseline");
  });

  it("uses baseline overview counts for headline metrics", () => {
    const bundle = miniBundle({
      dataStatus: "gemini_expanded_full",
      overview: {
        n_pairwise_comparisons: 240,
        n_flagged_comparisons: 77,
        n_pairwise_comparisons_all_modes: 720,
        n_flagged_comparisons_all_modes: 196,
      },
      pairwise: Array.from({ length: 720 }, () => ({ prompt_mode: "baseline" })),
      flagged: Array.from({ length: 196 }, () => ({ prompt_mode: "baseline" })),
    });
    const metrics = detentionHeadlineMetrics(bundle);
    expect(metrics.pairwiseCount).toBe(240);
    expect(metrics.flaggedCount).toBe(77);
    expect(metrics.flaggedCountAllModes).toBe(196);
  });

  it("filters rows by prompt mode", () => {
    const rows = [
      { case_id: "D1", prompt_mode: "baseline" },
      { case_id: "D1", prompt_mode: "fairness_aware" },
    ];
    expect(filterRowsByPromptMode(rows, "baseline")).toHaveLength(1);
  });
});
