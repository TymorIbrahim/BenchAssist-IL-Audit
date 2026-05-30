"use client";

import { useState } from "react";
import type { FilterState } from "@/lib/filters";
import { activeFilterChips, getFilterOptions, hasActiveFilters, resetFilters } from "@/lib/filters";
import type { JsonRecord } from "@/lib/types";

export function FilterPanel({
  filters,
  onChange,
  groupRows,
  pairwiseRows,
  showMetric = false,
  showCaseId = false,
  showReviewPriority = false,
  showIssueTag = false,
  showHighPriorityOnly = false,
  resultCount,
  collapsible = true,
}: {
  filters: FilterState;
  onChange: (next: FilterState) => void;
  groupRows: JsonRecord[];
  pairwiseRows: JsonRecord[];
  showMetric?: boolean;
  showCaseId?: boolean;
  showReviewPriority?: boolean;
  showIssueTag?: boolean;
  showHighPriorityOnly?: boolean;
  resultCount?: number;
  collapsible?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const source = pairwiseRows.length ? pairwiseRows : groupRows;
  const variantTypes = getFilterOptions(groupRows.length ? groupRows : source, "variant_type");
  const cues = getFilterOptions(groupRows.length ? groupRows : source, "demographic_cue");
  const validity = getFilterOptions(pairwiseRows, "validity_category");
  const caseIds = getFilterOptions(pairwiseRows, "case_id");
  const promptModes = getFilterOptions(pairwiseRows, "prompt_mode");
  const chips = activeFilterChips(filters);

  const set = (patch: Partial<FilterState>) => onChange({ ...filters, ...patch });

  const panel = (
    <>
      <p className="filter-hint muted">Filters affect the tables and case lists below. They do not change the underlying audit results.</p>
      <div className="filter-row">
        <label>
          Search
          <input
            type="search"
            value={filters.search}
            onChange={(e) => set({ search: e.target.value })}
            placeholder="Case ID, variant, text…"
            aria-label="Search rows"
          />
        </label>
        {showCaseId ? (
          <label>
            Case ID
            <select value={filters.caseId} onChange={(e) => set({ caseId: e.target.value })} aria-label="Filter by case ID">
              <option value="">All cases</option>
              {caseIds.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </label>
        ) : null}
        <label>
          Variant type
          <select value={filters.variantType} onChange={(e) => set({ variantType: e.target.value })} aria-label="Filter by variant type">
            <option value="">All variants</option>
            {variantTypes.filter((v) => v !== "neutral_he").map((v) => (
              <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
            ))}
          </select>
        </label>
        <label>
          Demographic cue
          <select value={filters.demographicCue} onChange={(e) => set({ demographicCue: e.target.value })} aria-label="Filter by demographic cue">
            <option value="">All cues</option>
            {cues.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
        {validity.length > 0 ? (
          <label>
            Validity
            <select value={filters.validityCategory} onChange={(e) => set({ validityCategory: e.target.value })} aria-label="Filter by validity">
              <option value="">All categories</option>
              {validity.map((v) => (
                <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
              ))}
            </select>
          </label>
        ) : null}
        {promptModes.length > 0 ? (
          <label>
            Prompt mode
            <select value={filters.promptMode} onChange={(e) => set({ promptMode: e.target.value })} aria-label="Filter by prompt mode">
              <option value="">All modes</option>
              {promptModes.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </label>
        ) : null}
        {showReviewPriority ? (
          <label>
            Review priority
            <select value={filters.reviewPriority} onChange={(e) => set({ reviewPriority: e.target.value })} aria-label="Filter by review priority">
              <option value="">All priorities</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </label>
        ) : null}
        {showHighPriorityOnly ? (
          <label className="checkbox-label">
            <input type="checkbox" checked={filters.highPriorityOnly} onChange={(e) => set({ highPriorityOnly: e.target.checked, reviewPriority: e.target.checked ? "High" : "" })} />
            High priority only
          </label>
        ) : null}
        {showIssueTag ? (
          <label>
            Issue / concern
            <select value={filters.issueTag} onChange={(e) => set({ issueTag: e.target.value })} aria-label="Filter by issue tag">
              <option value="">All concerns</option>
              <option value="weaker_remedy">Weaker remedy</option>
              <option value="higher_evidence_burden">Higher evidence burden</option>
              <option value="skeptical_credibility">Skeptical credibility</option>
              <option value="weaker_rights_framing">Weaker rights framing</option>
              <option value="identity_leakage">Identity leakage</option>
              <option value="unsupported_identity">Unsupported identity</option>
              <option value="hallucination_risk">Hallucination risk</option>
            </select>
          </label>
        ) : null}
        {showMetric ? (
          <label>
            Chart metric
            <select value={filters.metricKey} onChange={(e) => set({ metricKey: e.target.value })} aria-label="Select chart metric">
              <option value="legal_framing_bias_flag_rate">Legal framing signal</option>
              <option value="action_type_flip_rate">Action changed</option>
              <option value="remedy_weaker_rate">Weaker remedy</option>
              <option value="evidence_burden_higher_rate">More evidence requested</option>
              <option value="credibility_more_skeptical_rate">More skeptical credibility</option>
              <option value="rights_orientation_weaker_rate">Weaker rights framing</option>
            </select>
          </label>
        ) : null}
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={filters.flaggedOnly}
            onChange={(e) => set({ flaggedOnly: e.target.checked })}
            aria-label="Show flagged only"
          />
          Flagged only
        </label>
        <button type="button" className="btn btn-ghost" onClick={() => onChange(resetFilters())} disabled={!hasActiveFilters(filters)}>
          Reset all filters
        </button>
      </div>
      <div className="filter-meta">
        {typeof resultCount === "number" ? (
          <span className="result-count" aria-live="polite">{resultCount.toLocaleString()} result{resultCount === 1 ? "" : "s"} after filtering</span>
        ) : null}
        {chips.length ? (
          <div className="filter-chips" aria-label="Active filters">
            {chips.map((chip) => (
              <span key={chip.key} className="filter-chip">{chip.label}</span>
            ))}
          </div>
        ) : null}
      </div>
    </>
  );

  if (!collapsible) {
    return <div className="filter-panel" role="search">{panel}</div>;
  }

  return (
    <div className="filter-panel" role="search">
      <button type="button" className="filter-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? "Hide filters" : "Show filters"} {hasActiveFilters(filters) ? `(${chips.length} active)` : ""}
      </button>
      {open ? panel : null}
    </div>
  );
}
