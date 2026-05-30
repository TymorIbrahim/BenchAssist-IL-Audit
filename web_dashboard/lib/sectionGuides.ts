export interface SectionGuide {
  what: string;
  interpret: string;
  next: string;
}

export const SECTION_GUIDES: Record<string, SectionGuide> = {
  overview: {
    what: "This dashboard presents a read-only summary of a Responsible AI audit of a toy Israeli housing bench-memo assistant.",
    interpret: "All numbers are screening signals from a synthetic evaluation — not legal findings or proof of discrimination.",
    next: "Read How the audit works, then open Main findings.",
  },
  "audit-story": {
    what: "This timeline explains how synthetic cases, counterfactual variants, and structured memos were created and compared.",
    interpret: "The audit tests whether legal framing changes when cues change — it does not judge real people or cases.",
    next: "Continue to Main findings for headline rates.",
  },
  "main-findings": {
    what: "These metrics summarize how often the model changed its legal framing when the case was rewritten as a demographic, language-access, intersectional, or narrative variant.",
    interpret: "A high rate is an audit signal. It does not prove discrimination. It tells reviewers where to inspect cases manually.",
    next: "Open Flagged cases and compare neutral vs variant outputs in Inspect a case.",
  },
  "flagged-cases": {
    what: "Cases where at least one legal-framing dimension differed between the neutral memo and a variant memo.",
    interpret: "Flagged for legal review — not labeled as biased or discriminatory.",
    next: "Select a row and inspect the pair in Inspect a case.",
  },
  "case-explorer": {
    what: "Side-by-side comparison of the neutral and variant structured bench memos for one case.",
    interpret: "Focus on whether facts are equivalent and whether differences could affect access to relief.",
    next: "Check Validity checks and Stereotypes sections for context.",
  },
  "real-case-audit": {
    what: "Source-derived Israeli legal examples across housing, labor, welfare, immigration, consumer, and accessibility domains.",
    interpret: "Realism and robustness layer — not the main strict counterfactual fairness test. Not proof of discrimination.",
    next: "Review domain coverage, sample outputs, and the limitations callout.",
  },
  "counterfactual-validity": {
    what: "Whether each variant preserved the same legal facts as the neutral case.",
    interpret: "An output difference is more concerning when facts are equivalent. Changed facts may justify different memos.",
    next: "Review cases marked as invalid or needs human review before interpreting demographic rates.",
  },
  mitigation: {
    what: "Comparison of baseline, fairness-aware, and demographic-blind prompt strategies.",
    interpret: "Mitigation is useful only if it reduces concerning differences without creating new risks. Not proof of safety.",
    next: "Inspect individual cases in Inspect a case to see whether improvements hold case-by-case.",
  },
  "narrative-robustness": {
    what: "How emotional, informal, or procedurally framed language affects outputs when legal facts stay the same.",
    interpret: "Narrative sensitivity is robustness testing — not necessarily demographic discrimination.",
    next: "Compare narrative variant rates with demographic variants in Main findings.",
  },
  stereotype: {
    what: "Whether the model mentions demographic identity in legal reasoning when that identity is not legally relevant.",
    interpret: "Keyword-based screening only — identity in a summary may be harmless; identity in reasoning may be concerning.",
    next: "Review flagged examples and cross-check in Inspect a case.",
  },
  hallucination: {
    what: "In grounded mode, whether memos cite only provided sources and avoid unsupported legal claims.",
    interpret: "This does not certify correctness under Israeli law.",
    next: "Review high-risk examples manually.",
  },
  statistical: {
    what: "Confidence intervals and pairwise tests help avoid overinterpreting small samples.",
    interpret: "Some apparent differences may occur by chance. Statistics are exploratory screening tools.",
    next: "Prioritize signals with narrower intervals and larger sample sizes.",
  },
  "human-review": {
    what: "Workspace for legal experts to triage flagged cases and record review decisions.",
    interpret: "Human judgment is required before any fairness or deployment claim.",
    next: "Download the review template and work through flagged cases systematically.",
  },
  reports: {
    what: "Full written audit reports exported from the pipeline.",
    interpret: "Reports provide narrative context; the dashboard provides interactive exploration.",
    next: "Read the final audit report and limitations sections.",
  },
  methodology: {
    what: "Methods, metrics definitions, and limitations of this toy audit.",
    interpret: "This system is synthetic, limited in scope, and not a substitute for qualified legal review.",
    next: "Share the dashboard with reviewers alongside the written reports.",
  },
};
