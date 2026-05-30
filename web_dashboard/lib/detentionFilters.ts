import type { JsonRecord } from "./types";
import { str, toBool } from "./format";

export interface DetentionFilterState {
  promptMode: string;
  variantType: string;
  protectedAttribute: string;
  baseScenario: string;
  issueType: string;
  reviewPriority: string;
  caseStage: string;
  realVsSynthetic: string;
  strictFairnessOnly: boolean;
  fullTextRealCases: boolean;
  search: string;
}

export const DEFAULT_DETENTION_FILTERS: DetentionFilterState = {
  promptMode: "",
  variantType: "",
  protectedAttribute: "",
  baseScenario: "",
  issueType: "",
  reviewPriority: "",
  caseStage: "",
  realVsSynthetic: "",
  strictFairnessOnly: false,
  fullTextRealCases: false,
  search: "",
};

function matchesSearch(row: JsonRecord, q: string): boolean {
  if (!q.trim()) return true;
  const hay = JSON.stringify(row).toLowerCase();
  return hay.includes(q.toLowerCase());
}

export function filterDetentionRows(rows: JsonRecord[], filters: DetentionFilterState): JsonRecord[] {
  return rows.filter((row) => {
    if (filters.promptMode && str(row.prompt_mode) !== filters.promptMode) return false;
    if (filters.variantType && str(row.variant_type) !== filters.variantType) return false;
    if (filters.protectedAttribute && str(row.protected_attribute_tested) !== filters.protectedAttribute) return false;
    if (filters.baseScenario && str(row.case_id) !== filters.baseScenario && str(row.base_scenario_id) !== filters.baseScenario) return false;
    if (filters.issueType && !str(row.issue_type).includes(filters.issueType) && !str(row.review_label).includes(filters.issueType)) return false;
    if (filters.reviewPriority && str(row.review_priority) !== filters.reviewPriority) return false;
    if (filters.caseStage && str(row.likely_case_stage) !== filters.caseStage && str(row.detention_subtype) !== filters.caseStage) return false;
    if (filters.realVsSynthetic === "real") {
      const isReal = toBool(row.exclude_from_strict_bias_rates) || str(row.dataset_mode) === "real_case_inspired";
      if (!isReal) return false;
    }
    if (filters.realVsSynthetic === "synthetic") {
      const isReal = toBool(row.exclude_from_strict_bias_rates) || str(row.dataset_mode) === "real_case_inspired";
      if (isReal) return false;
    }
    if (filters.strictFairnessOnly && toBool(row.exclude_from_strict_bias_rates)) return false;
    if (!matchesSearch(row, filters.search)) return false;
    return true;
  });
}

export function filterDetentionRealCases(rows: JsonRecord[], filters: DetentionFilterState): JsonRecord[] {
  return rows.filter((row) => {
    if (filters.caseStage && str(row.likely_case_stage) !== filters.caseStage) return false;
    if (filters.fullTextRealCases && !row.full_text && !row.text) return false;
    if (!matchesSearch(row, filters.search)) return false;
    return true;
  });
}

export function detentionFiltersFromUrl(params: URLSearchParams): Partial<DetentionFilterState> & { tab?: string } {
  const out: Partial<DetentionFilterState> & { tab?: string } = {};
  const set = (key: keyof DetentionFilterState, urlKey: string) => {
    const v = params.get(urlKey);
    if (v) (out as DetentionFilterState)[key] = v as never;
  };
  set("promptMode", "prompt_mode");
  set("variantType", "variant_type");
  set("protectedAttribute", "protected_attribute");
  set("baseScenario", "base_scenario");
  set("issueType", "issue_type");
  set("reviewPriority", "review_priority");
  set("caseStage", "case_stage");
  set("realVsSynthetic", "real_vs_synthetic");
  set("search", "search");
  if (params.get("strict_only") === "1") out.strictFairnessOnly = true;
  if (params.get("fulltext") === "1") out.fullTextRealCases = true;
  const tab = params.get("tab");
  if (tab) out.tab = tab;
  return out;
}

export function detentionFiltersToUrl(
  filters: DetentionFilterState,
  opts?: { caseId?: string; variantId?: string; reviewId?: string; tab?: string },
): string {
  const qs = new URLSearchParams();
  if (opts?.tab) qs.set("tab", opts.tab);
  if (opts?.caseId) qs.set("case_id", opts.caseId);
  if (opts?.variantId) qs.set("variant_id", opts.variantId);
  if (opts?.reviewId) qs.set("review_id", opts.reviewId);
  if (filters.promptMode) qs.set("prompt_mode", filters.promptMode);
  if (filters.variantType) qs.set("variant_type", filters.variantType);
  if (filters.protectedAttribute) qs.set("protected_attribute", filters.protectedAttribute);
  if (filters.baseScenario) qs.set("base_scenario", filters.baseScenario);
  if (filters.issueType) qs.set("issue_type", filters.issueType);
  if (filters.reviewPriority) qs.set("review_priority", filters.reviewPriority);
  if (filters.caseStage) qs.set("case_stage", filters.caseStage);
  if (filters.realVsSynthetic) qs.set("real_vs_synthetic", filters.realVsSynthetic);
  if (filters.search) qs.set("search", filters.search);
  if (filters.strictFairnessOnly) qs.set("strict_only", "1");
  if (filters.fullTextRealCases) qs.set("fulltext", "1");
  return qs.toString();
}

export function uniqueDetentionValues(rows: JsonRecord[], key: string): string[] {
  const set = new Set<string>();
  for (const row of rows) {
    const v = str(row[key]);
    if (v) set.add(v);
  }
  return Array.from(set).sort();
}
