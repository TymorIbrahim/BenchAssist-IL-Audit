import type { DashboardData } from "./types";
import { str } from "./format";

export interface StoryStep {
  n: number;
  title: string;
  text: string;
}

export function buildAuditStorySteps(data: DashboardData): StoryStep[] {
  const { overview, manifest } = data;
  const base = overview.base_cases;
  const variants = overview.counterfactual_variants;
  const flagged = overview.total_flagged_cases;
  const model = str(manifest.model);
  const modes = (manifest.prompt_modes ?? []).length ? manifest.prompt_modes.join(", ") : str(manifest.prompt_mode);

  return [
    {
      n: 1,
      title: "Synthetic housing cases",
      text: base != null ? `We generated ${base} synthetic housing scenarios for this audit run.` : "Base case count not available in this exported run.",
    },
    {
      n: 2,
      title: "Counterfactual variants",
      text: variants != null ? `We created ${variants} counterfactual variants (demographic, language-access, narrative, and intersectional cues).` : "Counterfactual variant count not available in this exported run.",
    },
    {
      n: 3,
      title: "Structured bench memos",
      text: model !== "unknown" ? `We ran ${model} under prompt mode(s): ${modes}.` : "Model metadata not available in this exported run.",
    },
    {
      n: 4,
      title: "Neutral vs variant comparison",
      text: "Each variant was compared against the neutral version of the same case on structured legal dimensions.",
    },
    {
      n: 5,
      title: "Flagged for legal review",
      text: flagged != null ? `We flagged ${flagged} comparisons for human legal review (screening signals, not conclusions).` : "Flagged case count not available in this exported run.",
    },
    {
      n: 6,
      title: "Human review materials",
      text: data.humanReview.length ? "Human-review template rows and reviewer packets are available in this export." : "Human-review materials were not exported for this run.",
    },
  ];
}
