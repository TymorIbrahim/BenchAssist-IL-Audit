import type { GlossaryEntry } from "@/components/GlossaryDrawer";

export const DETENTION_GLOSSARY_ENTRIES: GlossaryEntry[] = [
  {
    term: "Audit signal",
    meaning: "A structured screening flag that a detention risk memo field changed between neutral and variant inputs on the same legal facts.",
    whyItMatters: "Helps legal experts prioritize comparisons for human review.",
    caution: "Not proof of unlawful discrimination.",
  },
  {
    term: "Dangerousness",
    meaning: "The model's assessed level of public-safety risk if the suspect were released.",
    whyItMatters: "Higher dangerousness may correlate with longer detention recommendations.",
    caution: "Could reflect appropriate legal reasoning — requires human review.",
  },
  {
    term: "Obstruction risk",
    meaning: "The model's assessment of whether the suspect may interfere with investigation if released.",
    whyItMatters: "Obstruction risk is a standard remand consideration in Israeli criminal procedure.",
    caution: "May indicate a possible concern — not a proven risk score.",
  },
  {
    term: "Reasonable suspicion",
    meaning: "The model's framing of whether reasonable suspicion supports continued detention.",
    whyItMatters: "Reasonable suspicion is a core legal threshold for remand decisions.",
    caution: "Model assessment is non-binding and requires legal expert review.",
  },
  {
    term: "Investigative necessity",
    meaning: "Whether continued detention is framed as necessary for the investigation.",
    whyItMatters: "Investigative necessity balances liberty against investigation needs.",
    caution: "Shifts may indicate audit signals, not definitive legal conclusions.",
  },
  {
    term: "Alternatives to detention",
    meaning: "Whether the memo discusses less restrictive options (conditions, supervision, release).",
    whyItMatters: "Omission of alternatives may affect liberty/public-safety balance framing.",
    caution: "Omission is flagged for legal review, not proof of improper reasoning.",
  },
  {
    term: "Procedural safeguards",
    meaning: "Whether the memo mentions rights, hearing requirements, or procedural protections.",
    whyItMatters: "Procedural safeguards reflect rights orientation in detention decisions.",
    caution: "Absence may indicate a possible concern requiring human review.",
  },
  {
    term: "Strict counterfactual",
    meaning: "A synthetic variant that changes only names, language, or identity proxies while preserving legal facts.",
    whyItMatters: "Strict counterfactuals support controlled fairness-rate comparisons.",
    caution: "Still requires human legal review — not proof of discrimination.",
  },
  {
    term: "Real-case-inspired",
    meaning: "Public Israeli legal text used for realism, grounding, and qualitative expert review.",
    whyItMatters: "Grounds the audit in authentic detention/remand language and context.",
    caution: "Excluded from strict synthetic fairness rates.",
  },
  {
    term: "Identity leakage",
    meaning: "Demographic identity appears in reasoning where it may not be legally relevant.",
    whyItMatters: "Identity should not drive detention conclusions without legal justification.",
    caution: "Flagged for legal review — not proof of unlawful discrimination.",
  },
  {
    term: "Unsupported risk inference",
    meaning: "The model infers elevated risk from identity or narrative cues not supported by case facts.",
    whyItMatters: "Unsupported inferences undermine reliability of non-binding memos.",
    caution: "Requires human review — may indicate hallucination or overreach.",
  },
  {
    term: "Review priority",
    meaning: "A screening tier (High / Medium / Low) for expert review queue ordering.",
    whyItMatters: "Helps legal experts focus limited review time on higher-signal comparisons.",
    caution: "Priority reflects audit methodology, not legal guilt or liability.",
  },
  {
    term: "Not proof of unlawful discrimination",
    meaning: "Dashboard metrics are screening signals for Responsible AI audit — they do not establish legal wrongdoing.",
    whyItMatters: "Prevents over-interpretation of automated comparisons.",
    caution: "All flagged items require human legal review before any external claim.",
  },
];
