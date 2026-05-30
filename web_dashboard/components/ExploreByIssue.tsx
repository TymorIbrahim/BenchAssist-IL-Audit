"use client";

import { DEFAULT_FILTERS, type FilterState } from "@/lib/filters";

export const ISSUE_FILTERS: {
  id: string;
  label: string;
  explanation: string;
  section: string;
  apply: (f: FilterState) => FilterState;
}[] = [
  {
    id: "weaker_remedy",
    label: "Weaker remedy",
    explanation: "Cases where the variant received a weaker remedy than neutral.",
    section: "flagged-cases",
    apply: (f) => ({ ...f, metricKey: "remedy_weaker_rate", flaggedOnly: true }),
  },
  {
    id: "higher_evidence",
    label: "Higher evidence burden",
    explanation: "Cases where the variant asked for more proof before acting.",
    section: "flagged-cases",
    apply: (f) => ({ ...f, metricKey: "evidence_burden_higher_rate", flaggedOnly: true }),
  },
  {
    id: "skeptical_credibility",
    label: "More skeptical credibility framing",
    explanation: "Cases with more skeptical credibility framing in the variant memo.",
    section: "flagged-cases",
    apply: (f) => ({ ...f, metricKey: "credibility_more_skeptical_rate", flaggedOnly: true }),
  },
  {
    id: "weaker_rights",
    label: "Weaker rights framing",
    explanation: "Cases where rights orientation appears weaker in the variant.",
    section: "flagged-cases",
    apply: (f) => ({ ...f, metricKey: "rights_orientation_weaker_rate", flaggedOnly: true }),
  },
  {
    id: "identity_leakage",
    label: "Identity leakage",
    explanation: "Review identity leakage screening flags.",
    section: "stereotype",
    apply: (f) => ({ ...f, flaggedOnly: true }),
  },
  {
    id: "hallucination",
    label: "Hallucination risk",
    explanation: "Review grounding and hallucination flags.",
    section: "hallucination",
    apply: (f) => ({ ...f, flaggedOnly: true }),
  },
  {
    id: "narrative",
    label: "Narrative sensitivity",
    explanation: "Explore narrative-framing variants and robustness summary.",
    section: "narrative-robustness",
    apply: (f) => ({ ...f, variantType: "narrative_framing_he" }),
  },
  {
    id: "validity",
    label: "Validity concerns",
    explanation: "Cases needing cautious interpretation due to non-strict counterfactuals.",
    section: "counterfactual-validity",
    apply: (f) => ({ ...f, validityCategory: "cautious_interpretation", flaggedOnly: true }),
  },
];

export function ExploreByIssue({
  onSelect,
}: {
  onSelect: (issueId: string, filters: FilterState, section: string, explanation: string) => void;
}) {
  return (
    <div className="issue-panel">
      <h4>Explore by issue</h4>
      <p className="muted">Start from legal concerns instead of metric names.</p>
      <div className="issue-grid">
        {ISSUE_FILTERS.map((issue) => (
          <button
            key={issue.id}
            type="button"
            className="issue-chip"
            title={issue.explanation}
            onClick={() => onSelect(issue.id, issue.apply({ ...DEFAULT_FILTERS }), issue.section, issue.explanation)}
          >
            {issue.label}
          </button>
        ))}
      </div>
    </div>
  );
}
