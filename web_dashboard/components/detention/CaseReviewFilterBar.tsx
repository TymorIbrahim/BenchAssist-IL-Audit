"use client";

import { useState } from "react";
import { DEFAULT_CASE_REVIEW_FILTERS, type CaseReviewFilters } from "@/lib/detentionCaseReview";
import { CASE_REVIEW_FILTER_PRESETS } from "@/lib/caseReviewPresets";

export function CaseReviewFilterBar({
  filters,
  filterOptions,
  minimalSchema,
  onChange,
  activePresetId,
  onApplyPreset,
}: {
  filters: CaseReviewFilters;
  filterOptions: {
    variants: string[];
    bases: string[];
    promptModes: string[];
    issues?: string[];
  };
  minimalSchema: boolean;
  onChange: (patch: Partial<CaseReviewFilters>) => void;
  activePresetId?: string | null;
  onApplyPreset?: (presetId: string) => void;
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const activeCount = [
    filters.promptMode,
    filters.reviewPriority,
    filters.variantType,
    filters.baseCaseId,
    filters.analysisBucket,
    filters.localReview !== "all" ? filters.localReview : "",
  ].filter(Boolean).length;

  const resetFilters = () => {
    onChange({
      ...DEFAULT_CASE_REVIEW_FILTERS,
      flaggedOnly: filters.flaggedOnly,
      focusMode: filters.focusMode,
      search: filters.search,
    });
  };

  return (
    <div className="case-review-filter-bar">
      <div className="case-review-quick-filters">
        {CASE_REVIEW_FILTER_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className={`quick-filter-chip ${activePresetId === preset.id ? "active" : ""}`}
            onClick={() => onApplyPreset?.(preset.id)}
          >
            {preset.label}
          </button>
        ))}
        <button
          type="button"
          className={`quick-filter-chip ${filters.flaggedOnly ? "active" : ""}`}
          onClick={() => onChange({ flaggedOnly: !filters.flaggedOnly })}
        >
          Flagged only
        </button>
        <button
          type="button"
          className={`quick-filter-chip ${filters.reviewPriority === "high" ? "active" : ""}`}
          onClick={() => onChange({ reviewPriority: filters.reviewPriority === "high" ? "" : "high" })}
        >
          High priority
        </button>
        <button
          type="button"
          className={`quick-filter-chip ${filters.analysisBucket === "strict_demographic" ? "active" : ""}`}
          onClick={() =>
            onChange({
              analysisBucket: filters.analysisBucket === "strict_demographic" ? "" : "strict_demographic",
            })
          }
        >
          Strict demographic
        </button>
        <button
          type="button"
          className={`quick-filter-chip ${filters.analysisBucket === "address_proxy" ? "active" : ""}`}
          onClick={() =>
            onChange({
              analysisBucket: filters.analysisBucket === "address_proxy" ? "" : "address_proxy",
            })
          }
        >
          Address proxy
        </button>
        <button
          type="button"
          className={`quick-filter-chip ${filters.localReview === "unreviewed" ? "active" : ""}`}
          onClick={() =>
            onChange({ localReview: filters.localReview === "unreviewed" ? "all" : "unreviewed" })
          }
        >
          Unreviewed locally
        </button>
        {activeCount ? (
          <button type="button" className="quick-filter-chip quick-filter-reset" onClick={resetFilters}>
            Clear filters ({activeCount})
          </button>
        ) : null}
      </div>

      <button
        type="button"
        className="case-review-advanced-toggle"
        onClick={() => setAdvancedOpen((v) => !v)}
        aria-expanded={advancedOpen}
      >
        {advancedOpen ? "Hide filters" : "More filters"}
        {activeCount && !advancedOpen ? ` (${activeCount})` : ""}
      </button>

      {advancedOpen ? (
        <div className="review-filter-grid">
          {filterOptions.promptModes.length > 1 ? (
            <select value={filters.promptMode} onChange={(e) => onChange({ promptMode: e.target.value })} aria-label="Prompt mode">
              <option value="">All prompt modes</option>
              {filterOptions.promptModes.map((mode) => (
                <option key={mode} value={mode}>{mode.replace(/_/g, " ")}</option>
              ))}
            </select>
          ) : null}
          <select value={filters.reviewPriority} onChange={(e) => onChange({ reviewPriority: e.target.value })} aria-label="Review priority">
            <option value="">All priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select value={filters.variantType} onChange={(e) => onChange({ variantType: e.target.value })} aria-label="Variant type">
            <option value="">All variants</option>
            {filterOptions.variants.map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
          </select>
          <select value={filters.baseCaseId} onChange={(e) => onChange({ baseCaseId: e.target.value })} aria-label="Base scenario">
            <option value="">All base scenarios</option>
            {filterOptions.bases.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
          <select
            value={filters.analysisBucket}
            onChange={(e) => onChange({ analysisBucket: e.target.value as CaseReviewFilters["analysisBucket"] })}
            aria-label="Analysis bucket"
          >
            <option value="">All analysis buckets</option>
            <option value="strict_demographic">Strict demographic</option>
            <option value="address_proxy">Address proxy</option>
          </select>
          <select
            value={filters.localReview}
            onChange={(e) => onChange({ localReview: e.target.value as CaseReviewFilters["localReview"] })}
            aria-label="Local review state"
          >
            <option value="all">All review states</option>
            <option value="unreviewed">Unreviewed locally</option>
            <option value="reviewed">Reviewed locally</option>
          </select>
          {!minimalSchema ? (
            <>
              <select value={filters.identityLeakage} onChange={(e) => onChange({ identityLeakage: e.target.value })} aria-label="Identity leakage">
                <option value="">Identity leakage: any</option>
                <option value="yes">Identity leakage: yes</option>
                <option value="no">Identity leakage: no</option>
              </select>
              <select value={filters.issueType} onChange={(e) => onChange({ issueType: e.target.value })} aria-label="Issue type">
                <option value="">All issue types</option>
                {(filterOptions.issues ?? []).map((issue) => (
                  <option key={issue} value={issue}>{issue.slice(0, 40)}</option>
                ))}
              </select>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
