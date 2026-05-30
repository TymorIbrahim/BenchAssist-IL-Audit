import { str, toBool, toNumber } from "./format";
import type { JsonRecord } from "./types";
import type { ComparisonMode } from "@/components/CaseComparison";

export const COMPARISON_TYPE_BY_MODE: Partial<Record<ComparisonMode, string>> = {
  baseline_vs_fairness: "baseline_vs_fairness_aware",
  baseline_vs_blind: "baseline_vs_demographic_blind",
  fairness_vs_blind: "fairness_aware_vs_demographic_blind",
};

export const COMPARISON_MODE_LABELS: Record<
  ComparisonMode,
  { label: string; subtitle: string }
> = {
  neutral_vs_variant: {
    label: "Neutral vs selected variant",
    subtitle: "Shows whether changing the case wording changed the legal framing.",
  },
  baseline_vs_fairness: {
    label: "Baseline vs fairness-aware prompt",
    subtitle: "Shows whether fairness instructions changed the memo for the same case.",
  },
  baseline_vs_blind: {
    label: "Baseline vs demographic-blind prompt",
    subtitle: "Shows whether removing demographic cues changed the memo.",
  },
  fairness_vs_blind: {
    label: "Fairness-aware vs demographic-blind prompt",
    subtitle: "Compares two mitigation approaches.",
  },
  variant_to_variant: {
    label: "Variant-to-variant",
    subtitle: "Compare two counterfactual variants within the same case.",
  },
};

export const CROSS_PROMPT_EMPTY_MESSAGE =
  "Cross-prompt comparison is not available in this exported run. This usually means the export only found one prompt mode, such as baseline. Run or export baseline, fairness-aware, and demographic-blind outputs, then rerun `python -m benchassist.vercel_export --auto`.";

export function getCrossPromptRow(
  rows: JsonRecord[],
  caseId: string,
  variantId: string,
  comparisonType: string,
): JsonRecord | null {
  return (
    rows.find(
      (r) =>
        str(r.case_id) === caseId
        && str(r.variant_id) === variantId
        && str(r.comparison_type) === comparisonType,
    ) ?? null
  );
}

/** Map cross-prompt export row to Case Explorer pairwise-style shape. */
export function crossPromptToComparisonRow(cross: JsonRecord): JsonRecord {
  return {
    ...cross,
    neutral_recommended_action_type: cross.left_recommended_action_type,
    variant_recommended_action_type: cross.right_recommended_action_type,
    neutral_urgency_score: cross.left_urgency,
    variant_urgency_score: cross.right_urgency,
    neutral_remedy_strength_score: cross.left_remedy_strength_score,
    variant_remedy_strength_score: cross.right_remedy_strength_score,
    neutral_evidence_burden_score: cross.left_evidence_burden_level,
    variant_evidence_burden_score: cross.right_evidence_burden_level,
    neutral_credibility_skepticism_score: cross.left_party_credibility_framing,
    variant_credibility_skepticism_score: cross.right_party_credibility_framing,
    neutral_rights_orientation_score: cross.left_rights_orientation,
    variant_rights_orientation_score: cross.right_rights_orientation,
    neutral_procedural_posture_score: cross.left_procedural_posture,
    variant_procedural_posture_score: cross.right_procedural_posture,
    neutral_reasoning_text: cross.left_reasoning_text,
    reasoning_text: cross.right_reasoning_text,
    action_type_flip: cross.action_type_changed,
    urgency_delta: cross.urgency_changed ? "changed" : "unchanged",
    remedy_strength_delta: cross.remedy_strength_delta,
    evidence_burden_delta: cross.evidence_burden_changed ? "changed" : "unchanged",
    credibility_skepticism_delta: cross.credibility_framing_changed ? "changed" : "unchanged",
    rights_orientation_delta: cross.rights_orientation_changed ? "changed" : "unchanged",
    procedural_posture_delta: cross.procedural_posture_changed ? "changed" : "unchanged",
    _leftLabel: str(cross.left_prompt_mode).replace(/_/g, " "),
    _rightLabel: str(cross.right_prompt_mode).replace(/_/g, " "),
    _isCrossPrompt: true,
  };
}

export function crossPromptEmptyDetail(
  mode: ComparisonMode,
  manifest: { missing_prompt_modes_for_comparison?: string[]; prompt_modes_detected?: string[] },
): string {
  const missing = manifest.missing_prompt_modes_for_comparison ?? [];
  const detected = manifest.prompt_modes_detected ?? [];
  if (mode === "baseline_vs_fairness" && missing.includes("fairness_aware")) {
    return "Fairness-aware outputs were not found in this export. Run the fairness-aware experiment, then re-export.";
  }
  if (mode === "baseline_vs_blind" && missing.includes("demographic_blind")) {
    return "Demographic-blind outputs were not found in this export. Run the demographic-blind experiment, then re-export.";
  }
  if (mode === "fairness_vs_blind") {
    if (missing.includes("fairness_aware") && missing.includes("demographic_blind")) {
      return "Neither fairness-aware nor demographic-blind outputs were exported.";
    }
    if (missing.includes("fairness_aware")) {
      return "Fairness-aware outputs are missing for this comparison.";
    }
    if (missing.includes("demographic_blind")) {
      return "Demographic-blind outputs are missing for this comparison.";
    }
  }
  if (detected.length <= 1) {
    return CROSS_PROMPT_EMPTY_MESSAGE;
  }
  return "No matching cross-prompt row for this case and variant in the exported comparison file.";
}

export interface CrossPromptSummary {
  comparableRows: number;
  baselineVsFairnessActionRate: number | null;
  baselineVsBlindActionRate: number | null;
  avgRemedyStrengthDelta: number | null;
  evidenceBurdenChangedRate: number | null;
  credibilityChangedRate: number | null;
  rightsOrientationChangedRate: number | null;
}

function rate(rows: JsonRecord[], flagKey: string): number | null {
  if (!rows.length) return null;
  const n = rows.filter((r) => toBool(r[flagKey])).length;
  return n / rows.length;
}

function avgDelta(rows: JsonRecord[]): number | null {
  const vals = rows.map((r) => toNumber(r.remedy_strength_delta)).filter((v): v is number => v !== null);
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

export function summarizeCrossPromptComparisons(rows: JsonRecord[]): CrossPromptSummary {
  const baselineFairness = rows.filter((r) => str(r.comparison_type) === "baseline_vs_fairness_aware");
  const baselineBlind = rows.filter((r) => str(r.comparison_type) === "baseline_vs_demographic_blind");
  const allTypes = new Set(rows.map((r) => `${str(r.case_id)}::${str(r.variant_id)}`));

  return {
    comparableRows: allTypes.size,
    baselineVsFairnessActionRate: rate(baselineFairness, "action_type_changed"),
    baselineVsBlindActionRate: rate(baselineBlind, "action_type_changed"),
    avgRemedyStrengthDelta: avgDelta(rows),
    evidenceBurdenChangedRate: rate(rows, "evidence_burden_changed"),
    credibilityChangedRate: rate(rows, "credibility_framing_changed"),
    rightsOrientationChangedRate: rate(rows, "rights_orientation_changed"),
  };
}
