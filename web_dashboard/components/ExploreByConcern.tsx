"use client";

import { DEFAULT_FILTERS, countRowsWithIssueTag, type FilterState } from "@/lib/filters";
import { formatRate } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export const CONCERN_ITEMS: {
  id: string;
  tag: string;
  label: string;
  explanation: string;
  apply: (f: FilterState) => FilterState;
}[] = [
  { id: "weaker_remedy", tag: "weaker_remedy", label: "Weaker remedy", explanation: "The variant received a less protective remedy than the neutral version.", apply: (f) => ({ ...f, issueTag: "weaker_remedy", flaggedOnly: true }) },
  { id: "higher_evidence", tag: "higher_evidence_burden", label: "Higher evidence burden", explanation: "The variant asked for more proof before acting.", apply: (f) => ({ ...f, issueTag: "higher_evidence_burden", flaggedOnly: true }) },
  { id: "skeptical_credibility", tag: "skeptical_credibility", label: "More skeptical credibility", explanation: "The variant framed the petitioner with more skepticism.", apply: (f) => ({ ...f, issueTag: "skeptical_credibility", flaggedOnly: true }) },
  { id: "weaker_rights", tag: "weaker_rights_framing", label: "Weaker rights framing", explanation: "The variant placed less emphasis on protective rights.", apply: (f) => ({ ...f, issueTag: "weaker_rights_framing", flaggedOnly: true }) },
  { id: "identity_leakage", tag: "identity_leakage", label: "Identity leakage", explanation: "Identity may appear in legal reasoning where not legally relevant.", apply: (f) => ({ ...f, issueTag: "identity_leakage", flaggedOnly: true }) },
  { id: "unsupported_identity", tag: "unsupported_identity", label: "Unsupported identity assumption", explanation: "The model may have inferred identity not present in the facts.", apply: (f) => ({ ...f, issueTag: "unsupported_identity", flaggedOnly: true }) },
  { id: "language_credibility", tag: "language_credibility", label: "Language credibility concern", explanation: "Language-access variants may affect credibility framing.", apply: (f) => ({ ...f, issueTag: "language_credibility", flaggedOnly: true }) },
  { id: "hallucination", tag: "hallucination_risk", label: "Hallucination risk", explanation: "Grounding checks flagged unsupported claims or citations.", apply: (f) => ({ ...f, issueTag: "hallucination_risk", flaggedOnly: true }) },
  { id: "validity", tag: "validity_concern", label: "Validity concern", explanation: "Comparison may not be a strict counterfactual — interpret cautiously.", apply: (f) => ({ ...f, validityCategory: "cautious_interpretation", flaggedOnly: true }) },
  { id: "narrative", tag: "narrative_sensitivity", label: "Narrative sensitivity", explanation: "Emotional or informal language variants — not necessarily demographic bias.", apply: (f) => ({ ...f, variantType: "narrative_framing_he", flaggedOnly: true }) },
];

export function ExploreByConcern({
  flaggedRows,
  onViewCases,
}: {
  flaggedRows: JsonRecord[];
  onViewCases: (filters: FilterState, explanation: string) => void;
}) {
  return (
    <div className="concern-panel">
      <h3>Explore by concern</h3>
      <p className="muted">Start from legal concerns instead of metric names. Each card filters the review queue below.</p>
      <div className="concern-grid">
        {CONCERN_ITEMS.map((item) => {
          const count = item.tag === "validity_concern"
            ? flaggedRows.filter((r) => String(r.validity_category ?? "").includes("cautious")).length
            : countRowsWithIssueTag(flaggedRows, item.tag);
          const rate = flaggedRows.length ? count / flaggedRows.length : null;
          return (
            <article key={item.id} className="concern-card">
              <h4>{item.label}</h4>
              <p>{item.explanation}</p>
              <p className="concern-stat">
                {flaggedRows.length ? `${count} flagged case${count === 1 ? "" : "s"} (${formatRate(rate)})` : "Not available in this export"}
              </p>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onViewCases(item.apply({ ...DEFAULT_FILTERS }), item.explanation)}
              >
                View related cases
              </button>
            </article>
          );
        })}
      </div>
    </div>
  );
}
