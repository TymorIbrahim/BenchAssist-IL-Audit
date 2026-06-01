"use client";

import { useCallback } from "react";
import type { FilterState } from "@/lib/v2/types";
import { DEFAULT_FILTERS } from "@/lib/v2/types";
import { formatVariantLabel, formatPromptMode } from "@/lib/v2/dataUtils";

interface FilterBarProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  promptModes: string[];
  variantTypes: string[];
  baseCaseIds: string[];
  showAnalysisBucket?: boolean;
  totalCount?: number;
  filteredCount?: number;
}

export function FilterBar({
  filters,
  onChange,
  promptModes,
  variantTypes,
  baseCaseIds,
  showAnalysisBucket = false,
  totalCount,
  filteredCount,
}: FilterBarProps) {
  const update = useCallback(
    (patch: Partial<FilterState>) => {
      onChange({ ...filters, ...patch });
    },
    [filters, onChange],
  );

  const reset = useCallback(() => {
    onChange({ ...DEFAULT_FILTERS });
  }, [onChange]);

  const hasActiveFilters =
    filters.promptMode !== DEFAULT_FILTERS.promptMode ||
    filters.variantType !== DEFAULT_FILTERS.variantType ||
    filters.flaggedOnly !== DEFAULT_FILTERS.flaggedOnly ||
    filters.shiftDirection !== DEFAULT_FILTERS.shiftDirection ||
    filters.baseCaseId !== DEFAULT_FILTERS.baseCaseId ||
    filters.search !== DEFAULT_FILTERS.search ||
    filters.analysisBucket !== DEFAULT_FILTERS.analysisBucket;

  return (
    <div className="v2-filter-bar">
      <div className="v2-filter-bar__controls">
        {/* Prompt Mode */}
        <label className="v2-filter-bar__field">
          <span className="v2-filter-bar__label">Prompt Mode</span>
          <select
            className="v2-filter-bar__select"
            value={filters.promptMode}
            onChange={(e) => update({ promptMode: e.target.value })}
          >
            <option value="">All modes</option>
            {promptModes.map((m) => (
              <option key={m} value={m}>
                {formatPromptMode(m)}
              </option>
            ))}
          </select>
        </label>

        {/* Variant Type */}
        <label className="v2-filter-bar__field">
          <span className="v2-filter-bar__label">Variant Type</span>
          <select
            className="v2-filter-bar__select"
            value={filters.variantType}
            onChange={(e) => update({ variantType: e.target.value })}
          >
            <option value="">All variants</option>
            {variantTypes.map((v) => (
              <option key={v} value={v}>
                {formatVariantLabel(v)}
              </option>
            ))}
          </select>
        </label>

        {/* Base Case */}
        <label className="v2-filter-bar__field">
          <span className="v2-filter-bar__label">Base Case</span>
          <select
            className="v2-filter-bar__select"
            value={filters.baseCaseId}
            onChange={(e) => update({ baseCaseId: e.target.value })}
          >
            <option value="">All cases</option>
            {baseCaseIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>

        {/* Shift Direction */}
        <label className="v2-filter-bar__field">
          <span className="v2-filter-bar__label">Shift Direction</span>
          <select
            className="v2-filter-bar__select"
            value={filters.shiftDirection}
            onChange={(e) =>
              update({
                shiftDirection: e.target.value as FilterState["shiftDirection"],
              })
            }
          >
            <option value="">Any</option>
            <option value="escalation">Escalation ↑</option>
            <option value="deescalation">De-escalation ↓</option>
            <option value="unchanged">Unchanged —</option>
          </select>
        </label>

        {/* Analysis Bucket */}
        {showAnalysisBucket && (
          <label className="v2-filter-bar__field">
            <span className="v2-filter-bar__label">Analysis Bucket</span>
            <select
              className="v2-filter-bar__select"
              value={filters.analysisBucket}
              onChange={(e) =>
                update({
                  analysisBucket: e.target
                    .value as FilterState["analysisBucket"],
                })
              }
            >
              <option value="">All</option>
              <option value="strict_demographic">Strict Demographic</option>
              <option value="address_proxy">Address Proxy</option>
            </select>
          </label>
        )}

        {/* Flagged Only */}
        <label className="v2-filter-bar__field v2-filter-bar__field--checkbox">
          <input
            type="checkbox"
            className="v2-filter-bar__checkbox"
            checked={filters.flaggedOnly}
            onChange={(e) => update({ flaggedOnly: e.target.checked })}
          />
          <span className="v2-filter-bar__label">Flagged only</span>
        </label>
      </div>

      <div className="v2-filter-bar__actions">
        {/* Search */}
        <input
          type="search"
          className="v2-filter-bar__search"
          placeholder="Search cases…"
          value={filters.search}
          onChange={(e) => update({ search: e.target.value })}
        />

        {/* Reset */}
        {hasActiveFilters && (
          <button
            type="button"
            className="v2-filter-bar__reset"
            onClick={reset}
          >
            Reset
          </button>
        )}

        {/* Result Count */}
        {filteredCount != null && totalCount != null && (
          <span className="v2-filter-bar__count">
            {filteredCount === totalCount
              ? `${totalCount} results`
              : `${filteredCount} of ${totalCount}`}
          </span>
        )}
      </div>
    </div>
  );
}
