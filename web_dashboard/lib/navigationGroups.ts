import type { NavSection } from "./types";

export interface NavGroup {
  title: string;
  sections: NavSection[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: "Overview",
    sections: [
      { id: "overview", label: "Executive overview", subtitle: "Start here" },
      { id: "key-takeaways", label: "Key takeaways", subtitle: "Plain-language summary" },
      { id: "audit-story", label: "Audit story", subtitle: "How it works" },
    ],
  },
  {
    title: "Results",
    sections: [
      { id: "main-findings", label: "Main findings", subtitle: "Headline signals" },
      { id: "flagged-cases", label: "Flagged cases", subtitle: "Review queue" },
      { id: "case-explorer", label: "Case explorer", subtitle: "Compare memos" },
      { id: "real-case-audit", label: "Real-case domain audit", subtitle: "Multi-domain realism" },
      { id: "counterfactual-validity", label: "Validity checks", subtitle: "Fact preservation" },
      { id: "mitigation", label: "Mitigation", subtitle: "Prompt comparison" },
      { id: "narrative-robustness", label: "Narrative robustness", subtitle: "Language effects" },
    ],
  },
  {
    title: "Safety audits",
    sections: [
      { id: "stereotype", label: "Identity leakage", subtitle: "Stereotype screening" },
      { id: "hallucination", label: "Grounding & hallucination", subtitle: "Source fidelity" },
      { id: "statistical", label: "Statistical uncertainty", subtitle: "Confidence intervals" },
    ],
  },
  {
    title: "Review & export",
    sections: [
      { id: "human-review", label: "Human review", subtitle: "Reviewer workflow" },
      { id: "reports", label: "Reports & downloads", subtitle: "Written outputs" },
      { id: "methodology", label: "Methodology & limitations", subtitle: "Scope & caveats" },
    ],
  },
];

export const ALL_NAV_SECTIONS = NAV_GROUPS.flatMap((g) => g.sections);
