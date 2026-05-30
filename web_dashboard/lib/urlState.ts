import type { FilterState } from "./filters";
import { DEFAULT_FILTERS } from "./filters";

export interface UrlDashboardState {
  section?: string;
  caseId?: string;
  variantId?: string;
  variantType?: string;
  demographicCue?: string;
  promptMode?: string;
  metric?: string;
  flaggedOnly?: boolean;
  reviewPriority?: string;
  search?: string;
  comparisonMode?: string;
}

export function parseUrlState(search: string): UrlDashboardState {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const flagged = params.get("flagged_only");
  return {
    section: params.get("section") || undefined,
    caseId: params.get("case_id") || undefined,
    variantId: params.get("variant_id") || undefined,
    variantType: params.get("variant_type") || undefined,
    demographicCue: params.get("demographic_cue") || undefined,
    promptMode: params.get("prompt_mode") || undefined,
    metric: params.get("metric") || undefined,
    reviewPriority: params.get("review_priority") || undefined,
    search: params.get("search") || undefined,
    flaggedOnly: flagged === "1" || flagged === "true" ? true : flagged === "0" || flagged === "false" ? false : undefined,
    comparisonMode: params.get("comparison_mode") || undefined,
  };
}

export function serializeUrlState(state: UrlDashboardState): string {
  const params = new URLSearchParams();
  if (state.section) params.set("section", state.section);
  if (state.caseId) params.set("case_id", state.caseId);
  if (state.variantId) params.set("variant_id", state.variantId);
  if (state.variantType) params.set("variant_type", state.variantType);
  if (state.demographicCue) params.set("demographic_cue", state.demographicCue);
  if (state.promptMode) params.set("prompt_mode", state.promptMode);
  if (state.metric) params.set("metric", state.metric);
  if (state.reviewPriority) params.set("review_priority", state.reviewPriority);
  if (state.search) params.set("search", state.search);
  if (state.comparisonMode) params.set("comparison_mode", state.comparisonMode);
  if (state.flaggedOnly) params.set("flagged_only", "1");
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function buildShareUrl(state: UrlDashboardState, origin?: string): string {
  const base = origin ?? (typeof window !== "undefined" ? window.location.origin + window.location.pathname : "/");
  return `${base}${serializeUrlState(state)}`;
}

export function filtersFromUrl(url: UrlDashboardState): FilterState {
  return {
    ...DEFAULT_FILTERS,
    caseId: url.caseId ?? "",
    variantType: url.variantType ?? "",
    demographicCue: url.demographicCue ?? "",
    promptMode: url.promptMode ?? "",
    metricKey: url.metric ?? DEFAULT_FILTERS.metricKey,
    reviewPriority: url.reviewPriority ?? "",
    search: url.search ?? "",
    flaggedOnly: url.flaggedOnly ?? false,
  };
}

export function urlFromAppState(args: {
  section?: string;
  filters: FilterState;
  caseId?: string;
  variantId?: string;
  comparisonMode?: string;
}): UrlDashboardState {
  return {
    section: args.section,
    caseId: args.caseId || args.filters.caseId || undefined,
    variantId: args.variantId || undefined,
    variantType: args.filters.variantType || undefined,
    demographicCue: args.filters.demographicCue || undefined,
    promptMode: args.filters.promptMode || undefined,
    metric: args.filters.metricKey || undefined,
    reviewPriority: args.filters.reviewPriority || undefined,
    search: args.filters.search || undefined,
    flaggedOnly: args.filters.flaggedOnly || undefined,
    comparisonMode: args.comparisonMode || undefined,
  };
}

export async function copyShareLink(state: UrlDashboardState): Promise<boolean> {
  const url = buildShareUrl(state);
  try {
    await navigator.clipboard.writeText(url);
    return true;
  } catch {
    return false;
  }
}
