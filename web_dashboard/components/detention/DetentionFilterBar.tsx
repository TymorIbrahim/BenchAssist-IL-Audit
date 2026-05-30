"use client";

import { Card } from "@/components/Card";
import { uniqueDetentionValues, type DetentionFilterState } from "@/lib/detentionFilters";
import { toBool, str } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export function DetentionFilterBar({
  flagged,
  filters,
  onChange,
  onReset,
  sticky,
}: {
  flagged: JsonRecord[];
  filters: DetentionFilterState;
  onChange: (f: DetentionFilterState) => void;
  onReset: () => void;
  sticky?: boolean;
}) {
  const patch = (p: Partial<DetentionFilterState>) => onChange({ ...filters, ...p });

  const chips = [
    filters.promptMode && { k: "promptMode" as const, label: `Mode: ${filters.promptMode}` },
    filters.variantType && { k: "variantType" as const, label: `Variant: ${filters.variantType}` },
    filters.reviewPriority && { k: "reviewPriority" as const, label: `Priority: ${filters.reviewPriority}` },
    filters.strictFairnessOnly && { k: "strictFairnessOnly" as const, label: "Strict only" },
    filters.realVsSynthetic && { k: "realVsSynthetic" as const, label: filters.realVsSynthetic },
  ].filter(Boolean);

  const promptModes = uniqueDetentionValues(flagged, "prompt_mode");
  const hasRealLayer = flagged.some(
    (r) => toBool(r.exclude_from_strict_bias_rates) || str(r.dataset_mode) === "real_case_inspired",
  );

  return (
    <Card title="" className={`filter-card ${sticky ? "filter-card-sticky" : ""}`}>
      <div className="filter-grid">
        {promptModes.length ? (
        <label>Prompt mode
          <select value={filters.promptMode} onChange={(e) => patch({ promptMode: e.target.value })}>
            <option value="">All</option>
            {promptModes.map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
          </select>
        </label>
        ) : null}
        <label>Variant
          <select value={filters.variantType} onChange={(e) => patch({ variantType: e.target.value })}>
            <option value="">All</option>
            {uniqueDetentionValues(flagged, "variant_type").map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
          </select>
        </label>
        <label>Review priority
          <select value={filters.reviewPriority} onChange={(e) => patch({ reviewPriority: e.target.value })}>
            <option value="">All</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </label>
        <label>Base scenario
          <select value={filters.baseScenario} onChange={(e) => patch({ baseScenario: e.target.value })}>
            <option value="">All</option>
            {uniqueDetentionValues(flagged, "case_id").map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
        <label>Issue type
          <select value={filters.issueType} onChange={(e) => patch({ issueType: e.target.value })}>
            <option value="">All</option>
            {uniqueDetentionValues(flagged, "issue_type").map((v) => <option key={v} value={v}>{v.slice(0, 48)}</option>)}
          </select>
        </label>
        {hasRealLayer ? (
        <label>Data layer
          <select value={filters.realVsSynthetic} onChange={(e) => patch({ realVsSynthetic: e.target.value })}>
            <option value="">All</option>
            <option value="synthetic">Synthetic strict</option>
            <option value="real">Real-case inspired</option>
          </select>
        </label>
        ) : null}
        <label className="checkbox-label">
          <input type="checkbox" checked={filters.strictFairnessOnly} onChange={(e) => patch({ strictFairnessOnly: e.target.checked })} />
          Strict fairness only
        </label>
        <label>Search
          <input type="search" value={filters.search} onChange={(e) => patch({ search: e.target.value })} placeholder="Search…" />
        </label>
      </div>
      {chips.length ? (
        <div className="filter-chips">
          {chips.map((chip) => chip && (
            <button
              key={chip.k}
              type="button"
              className="filter-chip"
              onClick={() => patch({ [chip.k]: chip.k === "strictFairnessOnly" ? false : "" } as Partial<DetentionFilterState>)}
            >
              {chip.label} ×
            </button>
          ))}
          <button type="button" className="btn btn-ghost btn-sm" onClick={onReset}>Reset</button>
        </div>
      ) : null}
    </Card>
  );
}
