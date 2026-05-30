"use client";

import { Card } from "@/components/Card";
import { Callout } from "@/components/Callout";
import { detentionFieldLabel } from "@/lib/detentionLabels";
import {
  CHECKLIST_ITEMS,
  EMPTY_CHECKLIST,
  type ReviewChecklist,
  type ReviewRecord,
  reviewKey,
} from "@/lib/detentionReview";
import { str, toBool, toNumber } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

const COMPARISON_FIELDS = [
  "dangerousness_level",
  "obstruction_risk_level",
  "reasonable_suspicion_assessment",
  "investigative_necessity",
  "recommended_action_type",
  "recommended_duration_days",
  "less_restrictive_alternatives_considered",
  "procedural_safeguards_mentioned",
  "suspect_credibility_framing",
  "rights_orientation",
  "reasoning_text",
  "evidence_needed",
  "limitations",
] as const;

function formatDelta(v: unknown): string {
  const n = toNumber(v);
  if (n === null) return "—";
  if (n === 0) return "0";
  return n > 0 ? `+${n}` : String(n);
}

function deltaKey(base: string): string {
  if (base.includes("alternatives") || base.includes("safeguards")) return `${base}_omission`;
  if (base.includes("credibility") || base.includes("rights")) return `${base.replace("_framing", "_framing_shift").replace("_orientation", "_orientation_shift")}`;
  return `${base}_delta`;
}

export function DetentionCaseComparison({
  row,
  review,
  onUpdateReview,
}: {
  row: JsonRecord;
  review: ReviewRecord | undefined;
  onUpdateReview: (patch: Partial<ReviewRecord>) => void;
}) {
  const checklist = { ...EMPTY_CHECKLIST, ...(review?.checklist ?? {}) };

  const updateChecklist = (key: keyof ReviewChecklist, value: boolean | null) => {
    onUpdateReview({ checklist: { ...checklist, [key]: value } });
  };

  return (
    <div className="case-review-layout">
      <aside className="case-review-left">
        <Card title="Scenario metadata">
          <dl className="meta-dl meta-dl-stack">
            <div><dt>Base scenario</dt><dd>{str(row.case_id)}</dd></div>
            <div><dt>Variant</dt><dd>{str(row.variant_type).replace(/_/g, " ")}</dd></div>
            <div><dt>Protected attribute</dt><dd>{str(row.protected_attribute_tested).replace(/_/g, " ")}</dd></div>
            <div><dt>Prompt mode</dt><dd>{str(row.prompt_mode) || "baseline"}</dd></div>
            <div><dt>Counterfactual strength</dt><dd>{str(row.counterfactual_strength) || "strict (synthetic)"}</dd></div>
            <div><dt>Strict fairness eligible</dt><dd>{toBool(row.exclude_from_strict_bias_rates) ? "No — excluded" : "Yes — synthetic"}</dd></div>
            <div><dt>Review priority</dt><dd>{str(row.review_priority)}</dd></div>
          </dl>
          {Array.isArray(row.detention_audit_flags_list) && (row.detention_audit_flags_list as string[]).length ? (
            <div className="issue-tags">
              {(row.detention_audit_flags_list as string[]).map((tag) => (
                <span key={tag} className="issue-tag">{tag.slice(0, 80)}</span>
              ))}
            </div>
          ) : null}
        </Card>
      </aside>

      <section className="case-review-center">
        <Card title="Neutral vs variant — audit signal comparison">
          <p className="muted">Side-by-side field comparison. Neutral baseline assumed identical legal facts. Full memo text appears when model outputs are exported.</p>
          <div className="side-by-side-table-wrap">
            <table className="side-by-side-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Neutral (baseline)</th>
                  <th>Variant</th>
                  <th>Signal</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_FIELDS.map((field) => {
                  const dk = deltaKey(field);
                  const delta = row[dk];
                  const omission = dk.includes("omission");
                  const changed = omission ? toBool(delta) : (toNumber(delta) !== null && Number(delta) !== 0);
                  const neutralVal = str(row[`neutral_${field}`]) || "— (export model outputs)";
                  const variantVal = str(row[`variant_${field}`]) || (changed ? `Shift: ${formatDelta(delta)}` : "— (export model outputs)");
                  let signal = "Unchanged";
                  if (changed) {
                    if (omission) signal = "Review recommended — omitted";
                    else if (Number(delta) > 0) signal = "Potentially relevant shift — higher";
                    else signal = "Field changed";
                  }
                  return (
                    <tr key={field} className={changed ? "row-changed" : ""}>
                      <td>{detentionFieldLabel(field)}</td>
                      <td>{neutralVal}</td>
                      <td>{variantVal}</td>
                      <td><span className={changed ? "field-tag" : "muted"}>{signal}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!str(row.neutral_reasoning_text) && !str(row.variant_reasoning_text) ? (
            <Callout title="Memo text not exported" variant="info">
              Pairwise deltas are available from mock/Gemini analysis. Export per-case model outputs to populate full side-by-side memo text. This does not block basic case review.
            </Callout>
          ) : null}
        </Card>
      </section>

      <aside className="case-review-right">
        <Card title="Reviewer checklist">
          <p className="muted local-storage-note">Local notes are stored only in this browser unless exported.</p>
          <ul className="checklist-list">
            {CHECKLIST_ITEMS.map((item) => (
              <li key={item.key}>
                <span>{item.label}</span>
                <div className="checklist-btns">
                  <button type="button" className={`btn btn-sm ${checklist[item.key] === true ? "btn-primary" : "btn-ghost"}`} onClick={() => updateChecklist(item.key, true)}>Yes</button>
                  <button type="button" className={`btn btn-sm ${checklist[item.key] === false ? "btn-primary" : "btn-ghost"}`} onClick={() => updateChecklist(item.key, false)}>No</button>
                  <button type="button" className={`btn btn-sm ${checklist[item.key] === null ? "btn-secondary" : "btn-ghost"}`} onClick={() => updateChecklist(item.key, null)}>—</button>
                </div>
              </li>
            ))}
          </ul>
          <label>Review notes
            <textarea
              rows={5}
              value={review?.notes ?? ""}
              onChange={(e) => onUpdateReview({ notes: e.target.value })}
              placeholder="Legal expert notes…"
            />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={review?.reviewed ?? false} onChange={(e) => onUpdateReview({ reviewed: e.target.checked, reviewedAt: new Date().toISOString() })} />
            Mark reviewed locally
          </label>
        </Card>
      </aside>
    </div>
  );
}

export { reviewKey };
