"use client";

import { useMemo } from "react";
import { isMinimalDetentionSchema } from "@/lib/detentionCaseReview";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { coerceStringList, str, toBool } from "@/lib/format";

const MODES = ["baseline", "fairness_aware", "demographic_blind"] as const;

export function MitigationFieldHeatmap({ bundle }: { bundle: DetentionDashboardBundle }) {
  const schemaVersion =
    str(bundle.manifest.schema_version) ||
    str(bundle.fullMetricSummary[0]?.schema_version) ||
    str(bundle.overview.schema_version);
  const minimalSchema = isMinimalDetentionSchema(schemaVersion);
  const rows = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of bundle.crossPromptComparisons) {
      if (!toBool(row.cross_prompt_instability_flag)) continue;
      const mode = str(row.comparison_mode) || "unknown";
      for (const field of coerceStringList(row.fields_changed_list ?? row.fields_changed)) {
        const key = `${mode}::${field}`;
        counts.set(key, (counts.get(key) ?? 0) + 1);
      }
    }
    const fields = [...new Set([...counts.keys()].map((k) => k.split("::")[1]).filter(Boolean))].sort();
    return fields.slice(0, 12).map((field) => ({
      field: field.replace(/_/g, " "),
      rawField: field,
      byMode: Object.fromEntries(
        MODES.map((mode) => [mode, counts.get(`${mode}::${field}`) ?? 0]),
      ) as Record<string, number>,
    }));
  }, [bundle.crossPromptComparisons]);

  if (!rows.length) return null;

  const max = Math.max(1, ...rows.flatMap((r) => Object.values(r.byMode)));

  return (
    <section className="section-card mitigation-heatmap">
      <h3>Cross-prompt field instability</h3>
      <p className="muted section-intro">
        {minimalSchema
          ? "Which minimal-schema fields change most often across prompt modes. Material instability here means dangerousness-level changes — screening only."
          : "Which structured output fields change most often across prompt modes (screening only)."}
      </p>
      <div className="heatmap-table-wrap">
        <table className="data-table heatmap-table">
          <thead>
            <tr>
              <th>Field</th>
              {MODES.map((m) => (
                <th key={m}>{m.replace(/_/g, " ")}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.rawField}>
                <td>{r.field}</td>
                {MODES.map((m) => {
                  const n = r.byMode[m] ?? 0;
                  const intensity = n / max;
                  return (
                    <td
                      key={m}
                      className="heatmap-cell"
                      style={{ background: n ? `rgba(37, 99, 235, ${0.12 + intensity * 0.55})` : undefined }}
                    >
                      {n || "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
