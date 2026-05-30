"use client";

import { useCallback, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { ComparisonMode } from "@/components/CaseComparison";
import type { FilterState } from "./filters";
import { filtersFromUrl, parseUrlState, urlFromAppState } from "./urlState";

const VALID_MODES: ComparisonMode[] = [
  "neutral_vs_variant",
  "baseline_vs_fairness",
  "baseline_vs_blind",
  "fairness_vs_blind",
  "variant_to_variant",
];

export function useDashboardUrlState(args: {
  filters: FilterState;
  setFilters: (f: FilterState | ((prev: FilterState) => FilterState)) => void;
  caseId?: string;
  variantId?: string;
  comparisonMode?: ComparisonMode;
  onCaseSelect?: (caseId: string, variantId: string) => void;
  onComparisonMode?: (mode: ComparisonMode) => void;
  enabled?: boolean;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const hydrated = useRef(false);

  useEffect(() => {
    if (!args.enabled || hydrated.current) return;
    const url = parseUrlState(searchParams.toString());
    if (Object.keys(url).length) {
      args.setFilters((prev) => ({ ...prev, ...filtersFromUrl(url) }));
      if (url.caseId && args.onCaseSelect) {
        args.onCaseSelect(url.caseId, url.variantId ?? "");
      }
      if (url.comparisonMode && args.onComparisonMode && VALID_MODES.includes(url.comparisonMode as ComparisonMode)) {
        args.onComparisonMode(url.comparisonMode as ComparisonMode);
      }
    }
    hydrated.current = true;
  }, [args, searchParams]);

  const syncUrl = useCallback(
    (patch: {
      caseId?: string;
      variantId?: string;
      filters?: FilterState;
      comparisonMode?: ComparisonMode;
    }) => {
      if (!args.enabled) return;
      const state = urlFromAppState({
        filters: patch.filters ?? args.filters,
        caseId: patch.caseId ?? args.caseId,
        variantId: patch.variantId ?? args.variantId,
        comparisonMode: patch.comparisonMode ?? args.comparisonMode,
      });
      const qs = new URLSearchParams();
      if (state.caseId) qs.set("case_id", state.caseId);
      if (state.variantId) qs.set("variant_id", state.variantId);
      if (state.variantType) qs.set("variant_type", state.variantType);
      if (state.demographicCue) qs.set("demographic_cue", state.demographicCue);
      if (state.promptMode) qs.set("prompt_mode", state.promptMode);
      if (state.metric) qs.set("metric", state.metric);
      if (state.reviewPriority) qs.set("review_priority", state.reviewPriority);
      if (state.search) qs.set("search", state.search);
      if (state.comparisonMode) qs.set("comparison_mode", state.comparisonMode);
      if (state.flaggedOnly) qs.set("flagged_only", "1");
      const next = qs.toString();
      router.replace(next ? `?${next}` : "/", { scroll: false });
    },
    [args, router],
  );

  return { syncUrl, parseUrlState: () => parseUrlState(searchParams.toString()) };
}
