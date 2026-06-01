"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/Card";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { filterRowsByPromptMode } from "@/lib/detentionMetrics";
import { formatCount, str } from "@/lib/format";
import { formatVariantLabel } from "@/lib/v2/dataUtils";
import type { JsonRecord } from "@/lib/types";

export function DetentionVariantMatrix({
  bundle,
  baseCaseId,
  promptMode = "",
  onSelectVariant,
}: {
  bundle: DetentionDashboardBundle;
  baseCaseId?: string;
  promptMode?: string;
  onSelectVariant?: (caseId: string, variantId: string) => void;
}) {
  const scopedPairwise = useMemo(
    () => filterRowsByPromptMode(bundle.pairwise, promptMode),
    [bundle.pairwise, promptMode],
  );

  const groups = useMemo(() => {
    const byBase = new Map<string, JsonRecord[]>();
    for (const row of scopedPairwise) {
      const base = str(row.case_id);
      if (!base) continue;
      if (!byBase.has(base)) byBase.set(base, []);
      byBase.get(base)!.push(row);
    }
    return [...byBase.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [scopedPairwise]);

  const [activeBase, setActiveBase] = useState(baseCaseId ?? groups[0]?.[0] ?? "");
  const rows = groups.find(([id]) => id === activeBase)?.[1] ?? [];

  return (
    <section className="section-card variant-matrix-panel">
      <h3>Base-case variant matrix</h3>
      <p className="muted section-intro">
        Counterfactual variants for a base scenario
        {promptMode ? ` (${formatVariantLabel(promptMode)} prompt mode)` : ""}.
        {promptMode ? " Change prompt mode in the filter bar to compare mitigation runs." : ""}
      </p>
      <div className="variant-matrix-layout">
        <aside className="variant-matrix-bases">
          {groups.map(([baseId, variants]) => (
            <button
              key={baseId}
              type="button"
              className={`variant-matrix-base-btn ${baseId === activeBase ? "active" : ""}`}
              onClick={() => setActiveBase(baseId)}
            >
              {baseId}
              <span className="muted">{formatCount(variants.length)} variants</span>
            </button>
          ))}
        </aside>
        <div className="variant-matrix-grid">
          {rows.map((row) => {
            const flagged = row.detention_framing_bias_flag === true || row.detention_framing_bias_flag === "True";
            const rowKey = `${str(row.case_id)}::${str(row.variant_id)}::${str(row.prompt_mode || "baseline")}`;
            return (
              <Card key={rowKey} title={formatVariantLabel(str(row.variant_type))}>
                <p className="muted">{str(row.variant_id)}</p>
                <p>Danger Δ: {Number(row.dangerousness_level_delta) || 0}</p>
                <p>Action Δ: {Number(row.recommended_action_type_delta) || 0}</p>
                <p>Flagged: {flagged ? "yes" : "no"}</p>
                {onSelectVariant ? (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => onSelectVariant(str(row.case_id), str(row.variant_id))}
                  >
                    Open in Case Review
                  </button>
                ) : null}
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
