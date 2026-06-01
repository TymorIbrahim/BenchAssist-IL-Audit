import type { DetentionTab } from "./detentionNavigation";

export interface ProcessStep {
  id: string;
  title: string;
  description: string;
  tab?: DetentionTab;
  exampleId?: string;
}

export const RESEARCH_PROCESS_STEPS: ProcessStep[] = [
  {
    id: "synthetic",
    title: "Build slim synthetic corpus",
    description: "10 base detention scenarios with core demographic variants plus proxy-cautious address variants (130 rows).",
    tab: "methodology",
  },
  {
    id: "variants",
    title: "Hold legal facts constant",
    description: "Variants change identity, language, or address presentation only — legally relevant facts stay fixed.",
    tab: "methodology",
  },
  {
    id: "prompts",
    title: "Run three prompt modes",
    description: "Baseline, fairness-aware, and demographic-blind prompts on the same cases.",
    tab: "mitigation",
  },
  {
    id: "parse",
    title: "Parse minimal schema outputs",
    description: "Each memo contains case_summary, dangerousness_level, and reasoning_text only.",
    tab: "methodology",
  },
  {
    id: "compare",
    title: "Compare neutral vs variant",
    description: "Pairwise comparison flags only when dangerousness_level changes between neutral and variant.",
    tab: "case-review",
  },
  {
    id: "address",
    title: "Review address-proxy bucket separately",
    description: "Address variants are strict-excluded and analyzed in a separate audit bucket.",
    tab: "audit-results",
  },
  {
    id: "export",
    title: "Expert review & export",
    description: "Review flagged comparisons, complete checklists, and export a reviewer packet.",
    tab: "case-review",
  },
];

export const RESEARCH_QUESTION =
  "When legally relevant facts are held constant, does the model assign a different dangerousness level to counterfactual variants (identity, language, or address presentation)?";
