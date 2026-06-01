"use client";

import { useOverlayDismiss } from "@/lib/useOverlayDismiss";

export interface GlossaryEntry {
  term: string;
  meaning: string;
  whyItMatters: string;
  caution: string;
}

export const GLOSSARY_ENTRIES: GlossaryEntry[] = [
  {
    term: "Legal framing signal",
    meaning: "A screening flag that at least one structured legal dimension changed between neutral and variant memos.",
    whyItMatters: "Helps reviewers find comparisons worth human inspection.",
    caution: "Not proof of discrimination or unlawful treatment.",
  },
  {
    term: "Action type flip",
    meaning: "The recommended action category changed (e.g., temporary relief vs request more evidence).",
    whyItMatters: "Category changes can alter procedural next steps.",
    caution: "Some changes may be legally justified if facts differ.",
  },
  {
    term: "Remedy weaker",
    meaning: "The variant recommends a less protective remedy than the neutral memo.",
    whyItMatters: "Weaker remedies may reduce access to relief.",
    caution: "Check counterfactual validity before interpreting.",
  },
  {
    term: "Evidence burden higher",
    meaning: "The variant asks for more documentation or proof before acting.",
    whyItMatters: "Higher evidence demands can delay housing relief.",
    caution: "May reflect appropriate caution — human review required.",
  },
  {
    term: "Credibility more skeptical",
    meaning: "The variant frames the petitioner with more doubt or skepticism.",
    whyItMatters: "Credibility framing can affect how seriously claims are treated.",
    caution: "Tone shifts are screening signals only.",
  },
  {
    term: "Rights orientation weaker",
    meaning: "The variant gives less weight to protective or rights-based considerations.",
    whyItMatters: "Rights orientation affects how protective the memo appears.",
    caution: "Not all differences imply unfair treatment.",
  },
  {
    term: "Counterfactual validity",
    meaning: "Whether a variant preserved the same legal facts as the neutral case.",
    whyItMatters: "Invalid comparisons cannot support strong causal claims.",
    caution: "Validity categories guide how cautiously to interpret differences.",
  },
  {
    term: "Strict counterfactual",
    meaning: "Variant preserves legal facts; suitable for direct neutral-vs-variant comparison.",
    whyItMatters: "Supports more confident comparison when other checks pass.",
    caution: "Still requires human legal review.",
  },
  {
    term: "Stress test",
    meaning: "Variant intentionally changes narrative framing or adds contextual cues.",
    whyItMatters: "Tests sensitivity but may not be a fair apples-to-apples comparison.",
    caution: "Interpret results cautiously; not direct-bias eligible.",
  },
  {
    term: "Identity leakage",
    meaning: "Demographic identity appears in legal reasoning where it may not be legally relevant.",
    whyItMatters: "Identity should not drive legal conclusions without justification.",
    caution: "Screening flag — requires contextual review.",
  },
  {
    term: "Unsupported assumption",
    meaning: "The model inferred identity or background not present in the case facts.",
    whyItMatters: "Unsupported assumptions can skew legal framing.",
    caution: "May appear in stereotype audit outputs when exported.",
  },
  {
    term: "Hallucination risk",
    meaning: "Model cites sources not provided or makes unsupported legal claims in grounded mode.",
    whyItMatters: "Grounding failures undermine trust in memo content.",
    caution: "Separate from fairness audit signals.",
  },
  {
    term: "Confidence interval",
    meaning: "A range estimating where a true rate might fall given sample size.",
    whyItMatters: "Wide intervals mean aggregate rates are uncertain.",
    caution: "Small pilot samples need extra caution.",
  },
  {
    term: "Mitigation mode",
    meaning: "Prompt strategy (baseline, fairness-aware, demographic-blind) intended to reduce concerning differences.",
    whyItMatters: "Shows whether prompt design may reduce screening signals.",
    caution: "Mitigation may help one metric while affecting others.",
  },
];

export function GlossaryDrawer({
  open,
  onClose,
  entries = GLOSSARY_ENTRIES,
}: {
  open: boolean;
  onClose: () => void;
  entries?: GlossaryEntry[];
}) {
  useOverlayDismiss(open, onClose);
  if (!open) return null;

  return (
    <div className="drawer-backdrop" onClick={onClose} role="presentation">
      <aside className="glossary-drawer" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Metric glossary">
        <div className="drawer-header">
          <h2>Glossary</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
        </div>
        <p className="muted drawer-lead">Plain-language definitions for legal and RAI reviewers. Screening signals only — not legal advice.</p>
        <dl className="glossary-drawer-list">
          {entries.map((item) => (
            <div key={item.term} className="glossary-drawer-item">
              <dt>{item.term}</dt>
              <dd><strong>Meaning:</strong> {item.meaning}</dd>
              <dd><strong>Why it matters:</strong> {item.whyItMatters}</dd>
              <dd className="caution-line"><strong>Caution:</strong> {item.caution}</dd>
            </div>
          ))}
        </dl>
      </aside>
    </div>
  );
}
