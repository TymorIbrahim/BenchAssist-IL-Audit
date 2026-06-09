/**
 * v2 Data Utilities — grouping, filtering, metric computation.
 * All functions operate on the typed interfaces from ./types.
 */

import type {
  PairwiseComparison,
  GroupSummary,
  CaseReviewIndexEntry,
  FilterState,
  ShiftCounts,
  ShiftDirection,
  OverviewMetrics,
  FullMetricSummary,
  RunManifest,
  CrossPromptModeSummary,
  StatisticalTest,
  CrossPromptComparison,
} from "./types";

/* ------------------------------------------------------------------ */
/*  Safe JSON fetcher (with NaN/Infinity scrubbing)                    */
/* ------------------------------------------------------------------ */

export async function fetchJson<T>(filename: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`/data/${filename}`);
    if (!res.ok) return fallback;
    const text = await res.text();
    const sanitized = text.replace(/\bNaN\b/g, "null").replace(/\bInfinity\b/g, "null");
    return JSON.parse(sanitized) as T;
  } catch {
    return fallback;
  }
}

/* ------------------------------------------------------------------ */
/*  Data Bundle                                                        */
/* ------------------------------------------------------------------ */

export interface DashboardBundle {
  overview: OverviewMetrics;
  pairwise: PairwiseComparison[];
  addressProxy: PairwiseComparison[];
  combinedPairwise: PairwiseComparison[];
  groupSummary: GroupSummary[];
  combinedGroupSummary: GroupSummary[];
  flagged: PairwiseComparison[];
  addressProxyFlagged: PairwiseComparison[];
  combinedFlagged: PairwiseComparison[];
  caseReviewIndex: CaseReviewIndexEntry[];
  caseReviewIndexCount: number;
  crossPromptComparisons: CrossPromptComparison[];
  crossPromptModeSummary: CrossPromptModeSummary | null;
  statisticalTests: StatisticalTest[];
  runManifest: RunManifest | null;
  fullMetricSummary: FullMetricSummary | null;
  promptModes: string[];
  variantTypes: string[];
  addressVariantTypes: string[];
  combinedVariantTypes: string[];
  baseCaseIds: string[];
  dataStatus: string;
  isMock: boolean;
}

function firstOfArray<T>(arr: T[] | T | null | undefined): T | null {
  if (!arr) return null;
  if (Array.isArray(arr)) return arr[0] ?? null;
  return arr as T;
}

function normalizePairwise(row: Record<string, unknown>): PairwiseComparison {
  const flags = coerceStringList(row.detention_audit_flags);
  return {
    case_id: str(row.case_id),
    variant_id: str(row.variant_id),
    variant_type: str(row.variant_type),
    protected_attribute_tested: str(row.protected_attribute_tested),
    prompt_mode: str(row.prompt_mode || "baseline"),
    schema_version: str(row.schema_version),
    analysis_bucket: row.analysis_bucket as string | null,
    dangerousness_level_delta: num(row.dangerousness_level_delta),
    dangerousness_escalation_flag: bool(row.dangerousness_escalation_flag),
    dangerousness_deescalation_flag: bool(row.dangerousness_deescalation_flag),
    insufficient_information_shift: bool(row.insufficient_information_shift),
    identity_or_proxy_mention_in_reasoning: bool(row.identity_or_proxy_mention_in_reasoning),
    identity_leakage_flag: bool(row.identity_leakage_flag),
    identity_leakage_signals: coerceStringList(row.identity_leakage_signals),
    address_mention_in_reasoning: bool(row.address_mention_in_reasoning),
    reasoning_length_delta: num(row.reasoning_length_delta),
    unsupported_dangerousness_inference_flag: bool(row.unsupported_dangerousness_inference_flag),
    unsupported_risk_inference_flag: bool(row.unsupported_risk_inference_flag),
    dangerousness_level_changed_flag: bool(row.dangerousness_level_changed_flag),
    detention_audit_flags: flags,
    detention_framing_bias_flag: bool(row.detention_framing_bias_flag),
    review_label: row.review_label as string | null,
    validity_category: row.validity_category as string | undefined,
    fact_preservation_score: row.fact_preservation_score != null ? num(row.fact_preservation_score) : undefined,
    direct_bias_analysis_eligible: row.direct_bias_analysis_eligible != null ? bool(row.direct_bias_analysis_eligible) : undefined,
    exclude_from_strict_bias_rates: row.exclude_from_strict_bias_rates != null ? bool(row.exclude_from_strict_bias_rates) : undefined,
    reviewer_note: row.reviewer_note as string | undefined,
    display_variant: str(row.variant_type).replace(/_/g, " "),
    review_priority: computeReviewPriority(row),
    issue_type: flags[0] ?? str(row.review_label) ?? "Audit signal",
  };
}

/* ------------------------------------------------------------------ */
/*  Load all dashboard data                                            */
/* ------------------------------------------------------------------ */

export async function loadDashboardBundle(): Promise<DashboardBundle> {
  const [
    overviewArr,
    pairwiseRaw,
    addressProxyRaw,
    combinedRaw,
    groupSummaryRaw,
    flaggedRaw,
    crossPromptRaw,
    crossPromptModeSummaryRaw,
    statisticalRaw,
    runManifestArr,
    fullMetricArr,
    caseReviewIndexPayload,
  ] = await Promise.all([
    fetchJson<Record<string, unknown>[]>("detention_overview_metrics.json", []),
    fetchJson<Record<string, unknown>[]>("detention_pairwise_comparison.json", []),
    fetchJson<Record<string, unknown>[]>("detention_address_proxy_pairwise_comparison.json", []),
    fetchJson<Record<string, unknown>[]>("detention_combined_pairwise_comparison.json", []),
    fetchJson<Record<string, unknown>[]>("detention_group_summary.json", []),
    fetchJson<Record<string, unknown>[]>("detention_flagged_cases.json", []),
    fetchJson<Record<string, unknown>[]>("detention_cross_prompt_comparisons.json", []),
    fetchJson<CrossPromptModeSummary | Record<string, unknown>[]>("detention_cross_prompt_mode_summary.json", [] as Record<string, unknown>[]),
    fetchJson<Record<string, unknown>[]>("detention_statistical_tests.json", []),
    fetchJson<Record<string, unknown>[]>("detention_full_run_manifest.json", []),
    fetchJson<Record<string, unknown>[]>("detention_full_metric_summary.json", []),
    fetchJson<{
      record_count?: number;
      records_index?: CaseReviewIndexEntry[];
      records_split?: boolean;
      flagged_count?: number;
      prompt_modes?: string[];
    }>("detention_case_review_index.json", {}),
  ]);

  const overview = (firstOfArray(overviewArr) ?? {}) as unknown as OverviewMetrics;
  const pairwise = pairwiseRaw.map(normalizePairwise);
  const addressProxy = addressProxyRaw.map(normalizePairwise);
  const combinedPairwise = combinedRaw.map(normalizePairwise);
  const flagged = flaggedRaw.length
    ? flaggedRaw.map(normalizePairwise)
    : pairwise.filter((r) => r.detention_framing_bias_flag);
  const addressProxyFlagged = addressProxy.filter((r) => r.detention_framing_bias_flag);
  const combinedFlagged = combinedPairwise.filter((r) => r.detention_framing_bias_flag);
  const groupSummary = groupSummaryRaw as unknown as GroupSummary[];

  // Build combined group summary from combined pairwise data
  const combinedGroupSummary = buildGroupSummaryFromPairwise(combinedPairwise);

  // Cross-prompt mode summary can be object or array
  let crossPromptModeSummary: CrossPromptModeSummary | null = null;
  if (crossPromptModeSummaryRaw && !Array.isArray(crossPromptModeSummaryRaw) && "by_comparison_mode" in crossPromptModeSummaryRaw) {
    crossPromptModeSummary = crossPromptModeSummaryRaw as CrossPromptModeSummary;
  } else if (Array.isArray(crossPromptModeSummaryRaw) && crossPromptModeSummaryRaw.length) {
    crossPromptModeSummary = crossPromptModeSummaryRaw[0] as unknown as CrossPromptModeSummary;
  }

  const crossPromptComparisons = crossPromptRaw as unknown as CrossPromptComparison[];
  const statisticalTests = statisticalRaw as unknown as StatisticalTest[];
  const runManifest = firstOfArray(runManifestArr) as unknown as RunManifest | null;
  const fullMetricSummary = firstOfArray(fullMetricArr) as unknown as FullMetricSummary | null;
  const caseReviewIndex = caseReviewIndexPayload.records_index ?? [];
  const caseReviewIndexCount = caseReviewIndexPayload.record_count ?? caseReviewIndex.length;

  const promptModes = uniqueValues(pairwise, "prompt_mode");
  const variantTypes = uniqueValues(pairwise, "variant_type");
  const addressVariantTypes = uniqueValues(addressProxy, "variant_type");
  const combinedVariantTypes = uniqueValues(combinedPairwise, "variant_type");
  const baseCaseIds = uniqueValues([...pairwise, ...addressProxy, ...combinedPairwise], "case_id");

  const dataStatus = str(overview.data_status || "");
  const isMock = dataStatus === "mock" || overview.mock_mode === true;

  return {
    overview,
    pairwise,
    addressProxy,
    combinedPairwise,
    groupSummary,
    combinedGroupSummary,
    flagged,
    addressProxyFlagged,
    combinedFlagged,
    caseReviewIndex,
    caseReviewIndexCount,
    crossPromptComparisons,
    crossPromptModeSummary,
    statisticalTests,
    runManifest,
    fullMetricSummary,
    promptModes,
    variantTypes,
    addressVariantTypes,
    combinedVariantTypes,
    baseCaseIds,
    dataStatus,
    isMock,
  };
}

/* ------------------------------------------------------------------ */
/*  Grouping helpers                                                   */
/* ------------------------------------------------------------------ */

function buildGroupSummaryFromPairwise(rows: PairwiseComparison[]): GroupSummary[] {
  if (!rows.length) return [];
  const groups: Record<string, PairwiseComparison[]> = {};
  for (const row of rows) {
    const key = `${row.variant_type}||${row.prompt_mode}`;
    (groups[key] ??= []).push(row);
  }
  return Object.entries(groups).map(([key, items]) => {
    const [variant_type, prompt_mode] = key.split("||");
    const flaggedCount = items.filter(r => r.detention_framing_bias_flag).length;
    const escalations = items.filter(r => r.dangerousness_escalation_flag).length;
    const changeCount = items.filter(r => r.dangerousness_level_changed_flag).length;
    const deltaSum = items.reduce((s, r) => s + (r.dangerousness_level_delta || 0), 0);
    return {
      variant_type,
      prompt_mode: prompt_mode || "baseline",
      n_comparisons: items.length,
      flagged_rate: items.length > 0 ? flaggedCount / items.length : 0,
      mean_dangerousness_delta: items.length > 0 ? deltaSum / items.length : 0,
      dangerousness_escalation_rate: items.length > 0 ? escalations / items.length : 0,
      dangerousness_change_rate: items.length > 0 ? changeCount / items.length : 0,
      identity_leakage_rate: 0,
      identity_or_proxy_mention_rate: 0,
      address_mention_rate: 0,
      insufficient_information_shift_rate: 0,
      unsupported_inference_rate: 0,
      protected_attribute_tested: items[0]?.protected_attribute_tested || "",
    } as GroupSummary;
  }).sort((a, b) => b.flagged_rate - a.flagged_rate);
}

export function groupByPromptMode<T extends { prompt_mode: string }>(rows: T[]): Record<string, T[]> {
  const result: Record<string, T[]> = {};
  for (const row of rows) {
    const key = row.prompt_mode || "baseline";
    (result[key] ??= []).push(row);
  }
  return result;
}

export function groupByVariantType<T extends { variant_type: string }>(rows: T[]): Record<string, T[]> {
  const result: Record<string, T[]> = {};
  for (const row of rows) {
    (result[row.variant_type] ??= []).push(row);
  }
  return result;
}

export function separateDemographicFromProxy(rows: PairwiseComparison[]): {
  demographic: PairwiseComparison[];
  addressProxy: PairwiseComparison[];
} {
  const demographic: PairwiseComparison[] = [];
  const addressProxy: PairwiseComparison[] = [];
  for (const row of rows) {
    if (row.protected_attribute_tested === "address_proxy" || row.analysis_bucket === "address_proxy_audit") {
      addressProxy.push(row);
    } else {
      demographic.push(row);
    }
  }
  return { demographic, addressProxy };
}

/* ------------------------------------------------------------------ */
/*  Metric computation                                                 */
/* ------------------------------------------------------------------ */

export function computeFlaggedRate(rows: PairwiseComparison[]): number {
  if (!rows.length) return 0;
  const flagged = rows.filter((r) => r.detention_framing_bias_flag).length;
  return flagged / rows.length;
}

export function computeShiftDirections(rows: PairwiseComparison[]): ShiftCounts {
  let escalation = 0;
  let deescalation = 0;
  let unchanged = 0;
  for (const row of rows) {
    if (row.dangerousness_level_delta > 0 || row.dangerousness_escalation_flag) {
      escalation++;
    } else if (row.dangerousness_level_delta < 0 || row.dangerousness_deescalation_flag) {
      deescalation++;
    } else {
      unchanged++;
    }
  }
  return { escalation, deescalation, unchanged, total: rows.length };
}

export function getShiftDirection(row: PairwiseComparison): ShiftDirection {
  if (row.dangerousness_level_delta > 0 || row.dangerousness_escalation_flag) return "escalation";
  if (row.dangerousness_level_delta < 0 || row.dangerousness_deescalation_flag) return "deescalation";
  return "unchanged";
}

/* ------------------------------------------------------------------ */
/*  Filter logic                                                       */
/* ------------------------------------------------------------------ */

export function filterRows(rows: PairwiseComparison[], filters: FilterState): PairwiseComparison[] {
  return rows.filter((row) => {
    if (filters.promptMode && row.prompt_mode !== filters.promptMode) return false;
    if (filters.variantType && row.variant_type !== filters.variantType) return false;
    if (filters.flaggedOnly && !row.detention_framing_bias_flag) return false;
    if (filters.baseCaseId && row.case_id !== filters.baseCaseId) return false;
    if (filters.shiftDirection === "escalation" && !(row.dangerousness_level_delta > 0 || row.dangerousness_escalation_flag)) return false;
    if (filters.shiftDirection === "deescalation" && !(row.dangerousness_level_delta < 0 || row.dangerousness_deescalation_flag)) return false;
    if (filters.shiftDirection === "unchanged" && row.dangerousness_level_delta !== 0) return false;
    if (filters.analysisBucket === "strict_demographic" && row.protected_attribute_tested === "address_proxy") return false;
    if (filters.analysisBucket === "address_proxy" && row.protected_attribute_tested !== "address_proxy") return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      const searchable = `${row.case_id} ${row.variant_id} ${row.variant_type} ${row.review_label ?? ""}`.toLowerCase();
      if (!searchable.includes(q)) return false;
    }
    return true;
  });
}

export function filterGroupSummary(rows: GroupSummary[], promptMode: string): GroupSummary[] {
  if (!promptMode) return rows;
  return rows.filter((r) => r.prompt_mode === promptMode);
}

export function filterCaseReviewIndex(
  index: CaseReviewIndexEntry[],
  filters: FilterState,
): CaseReviewIndexEntry[] {
  return index.filter((entry) => {
    if (filters.promptMode && entry.prompt_mode !== filters.promptMode) return false;
    if (filters.variantType && entry.variant_type !== filters.variantType) return false;
    if (filters.flaggedOnly && !entry.is_flagged) return false;
    if (filters.baseCaseId && entry.base_case_id !== filters.baseCaseId) return false;
    if (filters.analysisBucket === "strict_demographic" && entry.analysis_bucket !== "strict_demographic") return false;
    if (filters.analysisBucket === "address_proxy" && entry.analysis_bucket !== "address_proxy") return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      if (!entry.search_blob.toLowerCase().includes(q) && !entry.review_record_id.toLowerCase().includes(q)) return false;
    }
    return true;
  });
}

/* ------------------------------------------------------------------ */
/*  Headline metrics                                                   */
/* ------------------------------------------------------------------ */

export interface HeadlineMetrics {
  totalBaseCases: number;
  totalVariants: number;
  totalComparisons: number;
  baselineComparisons: number;
  totalFlagged: number;
  baselineFlagged: number;
  strictDemographicRate: number;
  addressProxyRate: number;
  parseSuccessRate: number;
  perModeMetrics: Record<string, { comparisons: number; flagged: number; flaggedRate: number }>;
}

export function computeHeadlineMetrics(bundle: DashboardBundle): HeadlineMetrics {
  const { overview, pairwise, flagged, addressProxy, addressProxyFlagged, fullMetricSummary } = bundle;

  const totalBaseCases = num(overview.n_synthetic_counterfactual_rows) || 30;
  const totalVariants = num(overview.n_outputs_total) || pairwise.length;
  const totalComparisons = num(overview.n_pairwise_comparisons_all_modes) || pairwise.length;
  const baselineComparisons = num(overview.n_pairwise_comparisons_baseline) || num(overview.n_pairwise_comparisons) || 0;
  const totalFlagged = num(overview.n_flagged_comparisons_all_modes) || flagged.length;
  const baselineFlagged = num(overview.n_flagged_comparisons_baseline) || num(overview.n_flagged_comparisons) || 0;

  const strictDemographicRate = baselineComparisons > 0 ? baselineFlagged / baselineComparisons : 0;
  const addressProxyRate = addressProxy.length > 0 ? addressProxyFlagged.length / addressProxy.length : 0;
  const parseSuccessRate = num(overview.parse_success_rate) || 0;

  // Per-mode metrics
  const perModeMetrics: Record<string, { comparisons: number; flagged: number; flaggedRate: number }> = {};
  if (fullMetricSummary?.per_prompt_mode) {
    for (const [mode, data] of Object.entries(fullMetricSummary.per_prompt_mode)) {
      const modeRows = pairwise.filter((r) => r.prompt_mode === mode);
      const modeFlagged = modeRows.filter((r) => r.detention_framing_bias_flag).length;
      perModeMetrics[mode] = {
        comparisons: data.n_strict_eligible || modeRows.length,
        flagged: modeFlagged,
        flaggedRate: modeRows.length > 0 ? modeFlagged / modeRows.length : 0,
      };
    }
  } else {
    for (const mode of bundle.promptModes) {
      const modeRows = pairwise.filter((r) => r.prompt_mode === mode);
      const modeFlagged = modeRows.filter((r) => r.detention_framing_bias_flag).length;
      perModeMetrics[mode] = {
        comparisons: modeRows.length,
        flagged: modeFlagged,
        flaggedRate: modeRows.length > 0 ? modeFlagged / modeRows.length : 0,
      };
    }
  }

  return {
    totalBaseCases,
    totalVariants,
    totalComparisons,
    baselineComparisons,
    totalFlagged,
    baselineFlagged,
    strictDemographicRate,
    addressProxyRate,
    parseSuccessRate,
    perModeMetrics,
  };
}

/* ------------------------------------------------------------------ */
/*  Formatting                                                         */
/* ------------------------------------------------------------------ */

export function formatRate(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function formatCount(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toLocaleString();
}

export function formatDelta(v: number): string {
  if (v > 0) return `+${v}`;
  return String(v);
}

const VARIANT_DISPLAY_LABELS: Record<string, string> = {
  /* Tier 1: Demographic */
  neutral_he: "Neutral Baseline",
  jewish_name_he: "Jewish Name (David Cohen)",
  arab_name_he: "Arab Name (Ahmed Mansour)",
  ethiopian_israeli_he: "Ethiopian Israeli",
  russian_immigrant_he: "Russian Immigrant",
  female_suspect_he: "Female Suspect",
  druze_name_he: "Druze Name (Salman Abu Saleh)",
  mizrahi_name_he: "Mizrahi Name (Moshe Abitbul)",
  asylum_seeker_he: "Eritrean Asylum Seeker",
  arab_woman_he: "Arab Woman (Fatima Khalil)",
  ethiopian_woman_he: "Ethiopian Israeli Woman",
  mizrahi_woman_he: "Mizrahi Woman (Rachel Malul)",
  /* Tier 2: Address */
  address_affluent_center_jewish_majority: "Affluent Center — Tel Aviv",
  address_arab_locality_north: "Arab Locality — Nazareth",
  address_arab_locality_triangle: "Arab Locality — Triangle Region",
  address_development_town_periphery: "Development Town — Sderot",
  address_lower_ses_jewish_periphery: "Lower SES Periphery — Dimona",
  address_mixed_city_arab_neighborhood: "Mixed City — Haifa (Arab Neighborhood)",
  address_mixed_city_jewish_neighborhood: "Mixed City — Haifa (Jewish Neighborhood)",
  address_neutral_large_city_center: "Neutral City Center — Rishon LeZion",
  address_haredi_area: "Haredi Area — Jerusalem",
  address_ethiopian_israeli_concentration_area: "Ethiopian-Israeli Area — Kiryat Gat",
  address_bedouin_locality_south: "Bedouin Locality — Negev",
  address_kibbutz_or_moshav: "Rural Cooperative — Jezreel Valley",
  /* Tier 3: Combined */
  arab_name_nazareth: "Arab Name + Nazareth",
  jewish_name_tel_aviv: "Jewish Name + Tel Aviv",
  jewish_name_dimona: "Jewish Name + Dimona",
  ethiopian_netanya: "Ethiopian Israeli + Netanya",
  russian_ashdod: "Russian Immigrant + Ashdod",
  mizrahi_beer_sheva: "Mizrahi Name + Be'er Sheva",
  arab_name_haifa: "Arab Name + Haifa",
  arab_name_tel_aviv: "Arab Name + Tel Aviv (control)",
  jewish_name_nazareth: "Jewish Name + Nazareth (control)",
  ethiopian_tel_aviv: "Ethiopian Israeli + Tel Aviv (control)",
  /* Stress tests */
  skeptical_police_framing: "Skeptical Police Framing",
  defense_framing: "Defense Framing",
  /* Prompt modes */
  baseline: "Baseline",
  fairness_aware: "Fairness-Aware",
  demographic_blind: "Demographic-Blind",
  /* Rachel Pretrial Detention Variants */
  control: "Control (Baseline)",
  ethnicity_proxy: "Ethnicity Proxy",
  neighborhood_proxy: "Neighborhood Proxy",
  age_proxy: "Age Proxy",
  employment_proxy: "Employment Proxy",
  family_status_proxy: "Family Status Proxy",
};

export function formatVariantLabel(v: string): string {
  return VARIANT_DISPLAY_LABELS[v] ?? v.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatPromptMode(v: string): string {
  return v.replace(/_/g, "-").replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ------------------------------------------------------------------ */
/*  Primitive helpers                                                  */
/* ------------------------------------------------------------------ */

function str(v: unknown): string {
  if (v == null || v === "null" || (typeof v === "number" && Number.isNaN(v))) return "";
  return String(v);
}

function num(v: unknown): number {
  const n = Number(v);
  return Number.isNaN(n) ? 0 : n;
}

function bool(v: unknown): boolean {
  return v === true || v === "True" || v === "true" || v === 1;
}

function coerceStringList(v: unknown): string[] {
  if (Array.isArray(v)) return v.map(String);
  if (typeof v === "string") {
    try {
      const parsed = JSON.parse(v.replace(/'/g, '"'));
      if (Array.isArray(parsed)) return parsed.map(String);
    } catch { /* ignore */ }
  }
  return [];
}

function uniqueValues(rows: any[], key: string): string[] { // eslint-disable-line
  const s = new Set<string>();
  for (const row of rows) {
    const v = str(row[key]);
    if (v) s.add(v);
  }
  return [...s].sort();
}

function computeReviewPriority(row: Record<string, unknown>): string {
  if (bool(row.identity_leakage_flag)) return "High";
  if (bool(row.unsupported_risk_inference_flag)) return "High";
  const danger = num(row.dangerousness_level_delta);
  if (Math.abs(danger) >= 2) return "High";
  if (bool(row.detention_framing_bias_flag)) return "Medium";
  if (danger !== 0) return "Medium";
  return "Low";
}
