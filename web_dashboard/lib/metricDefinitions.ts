export type MetricFormat = "rate" | "score" | "count";
export type ConcernDirection = "higher" | "lower" | "neutral";

export interface MetricDefinition {
  key: string;
  label: string;
  shortLabel: string;
  plainMeaning: string;
  whyItMatters: string;
  caution: string;
  preferredFormat: MetricFormat;
  concernDirection: ConcernDirection;
}

export const METRIC_CATALOG: Record<string, MetricDefinition> = {
  legal_framing_bias_flag_rate: {
    key: "legal_framing_bias_flag_rate",
    label: "Legal framing signal rate",
    shortLabel: "Legal framing",
    plainMeaning: "How often any important legal-framing difference was flagged between neutral and variant memos.",
    whyItMatters: "Shows where the model may treat similar cases differently in structured legal dimensions.",
    caution: "Audit signal only — not proof of discrimination or unlawful treatment.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  action_type_flip_rate: {
    key: "action_type_flip_rate",
    label: "Action changed rate",
    shortLabel: "Action changed",
    plainMeaning: "How often the recommended action category changed (e.g., temporary relief vs request more evidence).",
    whyItMatters: "A category change can affect what procedural step a clerk or judge might consider next.",
    caution: "Some action changes may be legally justified if facts differ.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  remedy_weaker_rate: {
    key: "remedy_weaker_rate",
    label: "Weaker remedy rate",
    shortLabel: "Weaker remedy",
    plainMeaning: "How often the variant received a weaker remedy than the neutral case.",
    whyItMatters: "Weaker remedies may mean less protective relief for the same dispute facts.",
    caution: "Compare validity before concluding the difference is concerning.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  evidence_burden_higher_rate: {
    key: "evidence_burden_higher_rate",
    label: "More evidence requested rate",
    shortLabel: "More evidence",
    plainMeaning: "How often the variant was asked for more proof before acting.",
    whyItMatters: "Higher evidence demands can delay relief and affect access to housing remedies.",
    caution: "May reflect appropriate caution — human review required.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  credibility_more_skeptical_rate: {
    key: "credibility_more_skeptical_rate",
    label: "More skeptical credibility rate",
    shortLabel: "Skeptical credibility",
    plainMeaning: "How often the variant framed the petitioner with more skepticism.",
    whyItMatters: "Credibility framing can influence how seriously a memo treats a litigant's claims.",
    caution: "Tone shifts are screening signals, not findings of bias.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  rights_orientation_weaker_rate: {
    key: "rights_orientation_weaker_rate",
    label: "Weaker rights framing rate",
    shortLabel: "Weaker rights",
    plainMeaning: "How often the variant placed less emphasis on protective rights.",
    whyItMatters: "Rights orientation affects how strongly protective considerations appear in the memo.",
    caution: "Not all differences imply unfair treatment.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  identity_leakage_flag_rate: {
    key: "identity_leakage_flag_rate",
    label: "Identity leakage rate",
    shortLabel: "Identity leakage",
    plainMeaning: "How often demographic identity appeared in legal reasoning when it may not be legally relevant.",
    whyItMatters: "Identity in reasoning can suggest the model used demographic cues beyond the legal facts.",
    caution: "Keyword screening only — requires human review.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  unsupported_identity_assumption_rate: {
    key: "unsupported_identity_assumption_rate",
    label: "Unsupported identity assumption rate",
    shortLabel: "Unsupported identity",
    plainMeaning: "How often the model assumed identity details not supported by the case text.",
    whyItMatters: "Unsupported assumptions can distort legal analysis.",
    caution: "Screening signal — not proof of stereotyping.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  invalid_citation_rate: {
    key: "invalid_citation_rate",
    label: "Invalid citation rate",
    shortLabel: "Invalid citations",
    plainMeaning: "How often the model cited sources not in the provided toy legal source set.",
    whyItMatters: "Invalid citations suggest the memo went beyond grounded materials.",
    caution: "Does not certify correctness under Israeli law.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  unsupported_legal_claim_rate: {
    key: "unsupported_legal_claim_rate",
    label: "Unsupported legal claim rate",
    shortLabel: "Unsupported claims",
    plainMeaning: "How often the model made legal claims not supported by provided sources.",
    whyItMatters: "Unsupported claims can mislead reviewers about applicable law.",
    caution: "Grounding check only — not a legal accuracy certification.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
  high_hallucination_risk_rate: {
    key: "high_hallucination_risk_rate",
    label: "High hallucination risk rate",
    shortLabel: "Hallucination risk",
    plainMeaning: "How often outputs were flagged as high risk for unsupported or ungrounded legal content.",
    whyItMatters: "High-risk memos need manual verification before any real workflow use.",
    caution: "Toy source set — exploratory safety signal.",
    preferredFormat: "rate",
    concernDirection: "higher",
  },
};

export function getMetricDefinition(key: string): MetricDefinition | undefined {
  return METRIC_CATALOG[key];
}

export function interpretationForMetric(key: string): string {
  const def = getMetricDefinition(key);
  if (!def) return "Select a metric to see a plain-language interpretation.";
  return `The selected metric is ${def.label}. ${def.plainMeaning} This is not proof of bias, but it identifies comparisons that legal reviewers should inspect.`;
}
