import { reviewPriority } from "./derive";
import { str, toBool, toNumber } from "./format";
import type { JsonRecord } from "./types";

export interface FilterState {
  variantType: string;
  demographicCue: string;
  promptMode: string;
  validityCategory: string;
  caseId: string;
  reviewPriority: string;
  issueTag: string;
  highPriorityOnly: boolean;
  flaggedOnly: boolean;
  search: string;
  metricKey: string;
}

export const DEFAULT_FILTERS: FilterState = {
  variantType: "",
  demographicCue: "",
  promptMode: "",
  validityCategory: "",
  caseId: "",
  reviewPriority: "",
  issueTag: "",
  highPriorityOnly: false,
  flaggedOnly: false,
  search: "",
  metricKey: "legal_framing_bias_flag_rate",
};

export function resetFilters(): FilterState {
  return { ...DEFAULT_FILTERS };
}

export function hasActiveFilters(filters: FilterState): boolean {
  return activeFilterChips(filters).length > 0;
}

export function safeIncludes(haystack: string, needle: string): boolean {
  if (!needle) return true;
  return haystack.toLowerCase().includes(needle.toLowerCase());
}

export function textSearch(row: JsonRecord, query: string, extraFields: string[] = []): boolean {
  if (!query.trim()) return true;
  const fields = [
    "case_id",
    "variant_id",
    "variant_type",
    "demographic_cue",
    "input_text",
    "reasoning_text",
    "strongest_signal",
    "validity_category",
    "neutral_reasoning_text",
    "neutral_input_text",
    "variant_input_text",
    ...extraFields,
  ];
  const hay = fields.map((f) => str(row[f])).join(" ").toLowerCase();
  return safeIncludes(hay, query);
}

export function activeFilterChips(filters: FilterState): { key: string; label: string }[] {
  const chips: { key: string; label: string }[] = [];
  if (filters.search) chips.push({ key: "search", label: `Search: ${filters.search}` });
  if (filters.caseId) chips.push({ key: "caseId", label: `Case: ${filters.caseId}` });
  if (filters.variantType) chips.push({ key: "variantType", label: `Variant: ${filters.variantType.replace(/_/g, " ")}` });
  if (filters.demographicCue) chips.push({ key: "demographicCue", label: `Cue: ${filters.demographicCue}` });
  if (filters.validityCategory) chips.push({ key: "validityCategory", label: `Validity: ${filters.validityCategory.replace(/_/g, " ")}` });
  if (filters.promptMode) chips.push({ key: "promptMode", label: `Prompt: ${filters.promptMode}` });
  if (filters.reviewPriority) chips.push({ key: "reviewPriority", label: `Priority: ${filters.reviewPriority}` });
  if (filters.issueTag) chips.push({ key: "issueTag", label: `Concern: ${filters.issueTag.replace(/_/g, " ")}` });
  if (filters.highPriorityOnly) chips.push({ key: "highPriorityOnly", label: "High priority only" });
  if (filters.flaggedOnly) chips.push({ key: "flaggedOnly", label: "Flagged only" });
  return chips;
}

export function getFilterOptions(rows: JsonRecord[], field: string): string[] {
  const set = new Set<string>();
  for (const row of rows) {
    const v = str(row[field]);
    if (v) set.add(v);
  }
  return Array.from(set).sort();
}

function matchesFilters(row: JsonRecord, filters: FilterState, includeCaseSearch = true): boolean {
  if (filters.variantType && str(row.variant_type) !== filters.variantType) return false;
  if (filters.demographicCue && str(row.demographic_cue) !== filters.demographicCue) return false;
  if (filters.validityCategory && str(row.validity_category) !== filters.validityCategory) return false;
  if (filters.caseId && str(row.case_id) !== filters.caseId) return false;
  if (filters.promptMode && str(row.prompt_mode) !== filters.promptMode) return false;
  if (filters.reviewPriority && reviewPriority(row) !== filters.reviewPriority) return false;
  if (filters.highPriorityOnly && reviewPriority(row) !== "High") return false;
  if (filters.issueTag && !rowMatchesIssueTag(row, filters.issueTag)) return false;
  if (filters.flaggedOnly && !toBool(row.legal_framing_bias_flag) && !toBool(row.is_flagged)) return false;
  if (filters.search && !textSearch(row, filters.search, includeCaseSearch ? [] : ["neutral_reasoning_text"])) return false;
  return true;
}

export function applyFilters(rows: JsonRecord[], filters: FilterState, includeCaseSearch = true): JsonRecord[] {
  return rows.filter((row) => matchesFilters(row, filters, includeCaseSearch));
}

export function filterGroupSummary(rows: JsonRecord[], filters: FilterState): JsonRecord[] {
  return applyFilters(rows, filters, false);
}

export function filterPairwise(rows: JsonRecord[], filters: FilterState): JsonRecord[] {
  return applyFilters(rows, filters, true);
}

export function filterFlagged(rows: JsonRecord[], filters: FilterState): JsonRecord[] {
  return applyFilters(rows, filters, true);
}

export function filterValidity(rows: JsonRecord[], filters: FilterState): JsonRecord[] {
  return applyFilters(rows, filters, false);
}

export interface ChartBar {
  name: string;
  value: number;
  rawKey?: string;
}

export function barChartData(
  rows: JsonRecord[],
  metricKey: string,
  topN = 5,
  sortDesc = true,
): ChartBar[] {
  const data = rows
    .map((row) => ({
      name: str(row.variant_type) || str(row.demographic_cue) || "unknown",
      rawKey: str(row.variant_type) || str(row.demographic_cue),
      value: toNumber(row[metricKey]) ?? 0,
    }))
    .filter((d) => d.name !== "neutral_he" && d.rawKey !== "neutral")
    .sort((a, b) => (sortDesc ? b.value - a.value : a.value - b.value))
    .slice(0, topN)
    .map((d) => ({
      name: d.name.replace(/_/g, " "),
      rawKey: d.rawKey,
      value: d.value <= 1 ? d.value * 100 : d.value,
    }));
  return data;
}

export function barChartByDemographic(
  rows: JsonRecord[],
  metricKey: string,
  topN = 8,
  sortDesc = true,
): ChartBar[] {
  const data = rows
    .map((row) => ({
      name: str(row.demographic_cue) || str(row.variant_type),
      rawKey: str(row.demographic_cue) || str(row.variant_type),
      value: toNumber(row[metricKey]) ?? 0,
    }))
    .filter((d) => d.name && d.name !== "neutral")
    .sort((a, b) => (sortDesc ? b.value - a.value : a.value - b.value))
    .slice(0, topN)
    .map((d) => ({
      name: d.name.length > 28 ? `${d.name.slice(0, 28)}…` : d.name,
      rawKey: d.rawKey,
      value: d.value <= 1 ? d.value * 100 : d.value,
    }));
  return data;
}

export function variantTypeFromChartLabel(label: string, rows: JsonRecord[]): string {
  const normalized = label.replace(/ /g, "_").toLowerCase();
  for (const row of rows) {
    const vt = str(row.variant_type);
    if (vt.replace(/_/g, " ").toLowerCase() === label.toLowerCase()) return vt;
    if (vt.toLowerCase() === normalized) return vt;
  }
  return normalized;
}

const ISSUE_FLAG_MAP: Record<string, string> = {
  weaker_remedy: "remedy_weaker",
  higher_evidence_burden: "evidence_burden_higher",
  skeptical_credibility: "credibility_more_skeptical",
  weaker_rights_framing: "rights_orientation_weaker",
  action_changed: "action_type_flip",
  identity_leakage: "identity_leakage_flag",
  hallucination_risk: "high_hallucination_risk_flag",
  unsupported_identity: "unsupported_identity_assumption",
  language_credibility: "language_credibility_bias_flag",
};

export function rowMatchesIssueTag(row: JsonRecord, tag: string): boolean {
  if (tag === "validity_concern") {
    const vc = str(row.validity_category).toLowerCase();
    return vc.includes("cautious") || vc.includes("stress") || vc.includes("needs_human");
  }
  const tags = row.issue_tags;
  if (Array.isArray(tags) && tags.includes(tag)) return true;
  const flagKey = ISSUE_FLAG_MAP[tag];
  if (flagKey && toBool(row[flagKey])) return true;
  return false;
}

export function countRowsWithIssueTag(rows: JsonRecord[], tag: string): number {
  return rows.filter((r) => rowMatchesIssueTag(r, tag)).length;
}
