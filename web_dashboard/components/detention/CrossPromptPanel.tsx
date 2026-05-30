"use client";

import type { CaseReviewRecord, ModelOutputBlock } from "@/lib/detentionCaseReview";
import { formatOutputValue } from "@/lib/detentionCaseReview";
import { joinStringList, toBool } from "@/lib/format";

const CROSS_PROMPT_FIELDS: { key: keyof ModelOutputBlock; label: string }[] = [
  { key: "dangerousness_level", label: "Dangerousness" },
  { key: "obstruction_risk_level", label: "Obstruction risk" },
  { key: "recommended_action_type", label: "Recommended action" },
  { key: "investigative_necessity", label: "Investigative necessity" },
  { key: "suspect_credibility_framing", label: "Credibility framing" },
  { key: "rights_orientation", label: "Rights orientation" },
];

export function CrossPromptPanel({ record }: { record: CaseReviewRecord }) {
  const cp = record.cross_prompt;
  if (!cp?.modes_available?.length || cp.modes_available.length < 2) {
    return null;
  }

  const modes = cp.modes_available;
  const instability = cp.cross_prompt_instability ?? [];

  return (
    <section className="review-section">
      <h3>Cross-prompt comparison (variant output)</h3>
      <p className="muted">Same case/variant under different prompt modes. May indicate cross-prompt instability — requires human review.</p>
      <div className="side-by-side-table-wrap">
        <table className="side-by-side-table">
          <thead>
            <tr>
              <th>Field</th>
              {modes.map((m) => (
                <th key={m}>{m.replace(/_/g, " ")}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CROSS_PROMPT_FIELDS.map(({ key, label }) => {
              const vals = modes.map((m) => formatOutputValue(cp.variant_outputs_by_mode?.[m]?.[key]));
              const allSame = vals.every((v) => v === vals[0]);
              return (
                <tr key={key} className={allSame ? "" : "row-changed"}>
                  <td>{label}</td>
                  {vals.map((v, i) => (
                    <td key={modes[i]}>{v}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {instability.length ? (
        <ul className="diff-summary-list">
          {instability.map((item, i) => (
            <li key={i}>
              {String(item.comparison_mode).replace(/_/g, " ")}: {toBool(item.cross_prompt_instability_flag) ? "possible instability" : "no field changes"}
              {joinStringList(item.fields_changed) ? ` (${joinStringList(item.fields_changed)})` : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
