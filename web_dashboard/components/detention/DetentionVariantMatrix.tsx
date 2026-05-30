"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/Card";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { formatCount, str } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export function DetentionVariantMatrix({
  bundle,
  baseCaseId,
  onSelectVariant,
}: {
  bundle: DetentionDashboardBundle;
  baseCaseId?: string;
  onSelectVariant?: (caseId: string, variantId: string) => void;
}) {
  const groups = useMemo(() => {
    const byBase = new Map<string, JsonRecord[]>();
    for (const row of bundle.pairwise) {
      const base = str(row.case_id);
      if (!base) continue;
      if (!byBase.has(base)) byBase.set(base, []);
      byBase.get(base)!.push(row);
    }
    return [...byBase.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [bundle.pairwise]);

  const [activeBase, setActiveBase] = useState(baseCaseId ?? groups[0]?.[0] ?? "");
  const rows = groups.find(([id]) => id === activeBase)?.[1] ?? [];

  return (
    <section className="section-card variant-matrix-panel">
      <h3>Base-case variant matrix</h3>
      <p className="muted section-intro">All counterfactual variants for a base scenario — useful for spotting patterns across presentation changes.</p>
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
            return (
              <Card key={str(row.variant_id)} title={str(row.variant_type).replace(/_/g, " ")}>
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
