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
    title: "Build synthetic detention scenarios",
    description: "Controlled base cases with documented legal facts (evidence, priors, witness risk, release options).",
    tab: "methodology",
    exampleId: "base-case",
  },
  {
    id: "variants",
    title: "Create controlled variants",
    description: "Change only identity, language, or narrative framing while holding legally relevant facts constant.",
    tab: "methodology",
    exampleId: "variant",
  },
  {
    id: "prompts",
    title: "Run model prompt modes",
    description: "Baseline, fairness-aware, and demographic-blind prompts produce structured risk memos.",
    tab: "mitigation",
  },
  {
    id: "parse",
    title: "Parse structured risk memos",
    description: "Outputs validated against a schema: dangerousness, obstruction, action, alternatives, safeguards.",
    tab: "methodology",
    exampleId: "output",
  },
  {
    id: "compare",
    title: "Compare neutral vs variant",
    description: "Pairwise comparison detects field-level shifts that may require legal review.",
    tab: "case-review",
    exampleId: "comparison",
  },
  {
    id: "flag",
    title: "Flag possible concerns",
    description: "Audit signals highlight shifts, omissions, identity language, or unsupported inferences.",
    tab: "audit-results",
  },
  {
    id: "real",
    title: "Review real Israeli legal examples",
    description: "Public legal text supports realism, grounding, and qualitative expert review — excluded from strict rates.",
    tab: "real-cases",
  },
  {
    id: "export",
    title: "Export legal-expert review packet",
    description: "Selected cases, notes, and checklists export for final report preparation.",
    tab: "expert-workspace",
  },
];

export const RESEARCH_QUESTION =
  "Does the model produce different risk memos when only identity, language, or framing changes while legally relevant facts remain constant?";
