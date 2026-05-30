"use client";

import type { FilterState } from "@/lib/filters";
import { uniqueValues } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export function FilterBar({
  filters,
  onChange,
  groupRows,
  pairwiseRows,
  showMetric = false,
}: {
  filters: FilterState;
  onChange: (next: FilterState) => void;
  groupRows: JsonRecord[];
  pairwiseRows: JsonRecord[];
  showMetric?: boolean;
}) {
  const variantTypes = uniqueValues(groupRows.length ? groupRows : pairwiseRows, "variant_type");
  const cues = uniqueValues(groupRows.length ? groupRows : pairwiseRows, "demographic_cue");
  const validity = uniqueValues(pairwiseRows, "validity_category");

  const set = (patch: Partial<FilterState>) => onChange({ ...filters, ...patch });

  return (
    <div className="filter-bar" role="search" aria-label="Filters">
      <label>
        Search
        <input
          type="search"
          value={filters.search}
          onChange={(e) => set({ search: e.target.value })}
          placeholder="Case ID, variant, text…"
        />
      </label>
      <label>
        Variant type
        <select value={filters.variantType} onChange={(e) => set({ variantType: e.target.value })}>
          <option value="">All</option>
          {variantTypes.map((v) => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>
      </label>
      <label>
        Demographic cue
        <select value={filters.demographicCue} onChange={(e) => set({ demographicCue: e.target.value })}>
          <option value="">All</option>
          {cues.map((v) => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>
      </label>
      {validity.length > 0 ? (
        <label>
          Validity
          <select value={filters.validityCategory} onChange={(e) => set({ validityCategory: e.target.value })}>
            <option value="">All</option>
            {validity.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
      ) : null}
      {showMetric ? (
        <label>
          Chart metric
          <select value={filters.metricKey} onChange={(e) => set({ metricKey: e.target.value })}>
            <option value="legal_framing_bias_flag_rate">Legal framing signal</option>
            <option value="remedy_weaker_rate">Remedy weaker</option>
            <option value="evidence_burden_higher_rate">Evidence burden higher</option>
            <option value="credibility_more_skeptical_rate">Credibility skeptical</option>
            <option value="rights_orientation_weaker_rate">Rights orientation weaker</option>
            <option value="action_type_flip_rate">Action type flip</option>
          </select>
        </label>
      ) : null}
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={filters.flaggedOnly}
          onChange={(e) => set({ flaggedOnly: e.target.checked })}
        />
        Flagged only
      </label>
    </div>
  );
}
