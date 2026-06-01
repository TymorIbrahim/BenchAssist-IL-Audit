"use client";

import { useState } from "react";
import type { CaseReviewRecord, ModelOutputBlock } from "@/lib/detentionCaseReview";
import { formatOutputValue, isMinimalDetentionSchema } from "@/lib/detentionCaseReview";
import { joinStringList, toBool } from "@/lib/format";

const FULL_CROSS_PROMPT_FIELDS: { key: keyof ModelOutputBlock; label: string }[] = [
  { key: "dangerousness_level", label: "Dangerousness" },
  { key: "obstruction_risk_level", label: "Obstruction risk" },
  { key: "recommended_action_type", label: "Recommended action" },
  { key: "investigative_necessity", label: "Investigative necessity" },
  { key: "suspect_credibility_framing", label: "Credibility framing" },
  { key: "rights_orientation", label: "Rights orientation" },
];

const MINIMAL_CROSS_PROMPT_FIELDS: { key: keyof ModelOutputBlock; label: string }[] = [
  { key: "dangerousness_level", label: "Dangerousness" },
  { key: "case_summary", label: "Case summary" },
  { key: "reasoning_text", label: "Reasoning" },
];

function CrossPromptDangerousnessStrip({
  modes,
  variantByMode,
}: {
  modes: string[];
  variantByMode: Record<string, ModelOutputBlock | undefined>;
}) {
  const levels = modes.map((m) => formatOutputValue(variantByMode[m]?.dangerousness_level));
  const unstable = new Set(levels).size > 1;
  if (!unstable && levels.every((l) => l === levels[0])) {
    return (
      <div className="cross-prompt-danger-strip cross-prompt-danger-strip-stable">
        <span className="muted">Dangerousness across prompt modes (variant output):</span>
        {modes.map((m) => (
          <span key={m} className="cross-prompt-mode-pill">
            {m.replace(/_/g, " ")}: <strong>{levels[modes.indexOf(m)]}</strong>
          </span>
        ))}
        <span className="muted">Stable — exploratory check only.</span>
      </div>
    );
  }
  return (
    <div className="cross-prompt-danger-strip cross-prompt-danger-strip-unstable" role="status">
      <span className="muted">Dangerousness across prompt modes (variant output):</span>
      {modes.map((m, i) => (
        <span key={m} className="cross-prompt-mode-pill cross-prompt-mode-pill-warn">
          {m.replace(/_/g, " ")}: <strong>{levels[i]}</strong>
        </span>
      ))}
      <span className="cross-prompt-instability-note">Material instability across prompts — not a primary strict audit flag.</span>
    </div>
  );
}

export function CrossPromptPanel({
  record,
  defaultExpanded,
}: {
  record: CaseReviewRecord;
  defaultExpanded?: boolean;
}) {
  const cp = record.cross_prompt;
  const modes = cp?.modes_available ?? [];
  const instability = cp?.cross_prompt_instability ?? [];
  const hasMaterial = instability.some((item) => item.cross_prompt_instability_flag);
  const [detailsOpen, setDetailsOpen] = useState(defaultExpanded ?? hasMaterial);

  if (!cp?.modes_available?.length || cp.modes_available.length < 2) {
    return null;
  }
  const fields = isMinimalDetentionSchema(record.schema_version)
    ? MINIMAL_CROSS_PROMPT_FIELDS
    : FULL_CROSS_PROMPT_FIELDS;

  return (
    <section className="review-section">
      <h3>Cross-prompt comparison (variant output)</h3>
      <p className="muted">Same case/variant under different prompt modes. Instability here is exploratory — not a primary audit flag.</p>
      <CrossPromptDangerousnessStrip modes={modes} variantByMode={cp.variant_outputs_by_mode ?? {}} />
      <details className="cross-prompt-details" open={detailsOpen} onToggle={(e) => setDetailsOpen(e.currentTarget.open)}>
        <summary>{detailsOpen ? "Hide" : "Show"} full cross-prompt field table</summary>
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
            {fields.map(({ key, label }) => {
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
        <ul className="diff-summary-list compact">
          {instability.map((item, i) => (
            <li key={i}>
              {String(item.comparison_mode).replace(/_/g, " ")}: {toBool(item.cross_prompt_instability_flag) ? "field changes" : "stable"}
              {joinStringList(item.fields_changed) ? ` (${joinStringList(item.fields_changed)})` : ""}
            </li>
          ))}
        </ul>
      ) : null}
      </details>
    </section>
  );
}
