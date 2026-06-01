import type { DashboardData, JsonRecord, Manifest, OverviewMetrics, ReportEntry } from "./types";
import { enrichRows } from "./derive";

const DATA_FILES = [
  "manifest.json",
  "overview_metrics.json",
  "group_summary.json",
  "pairwise_comparison.json",
  "flagged_cases.json",
  "counterfactual_validity.json",
  "counterfactual_validity_summary.json",
  "stereotype_group_summary.json",
  "stereotype_flagged_examples.json",
  "hallucination_group_summary.json",
  "hallucination_per_output.json",
  "statistical_group_effects.json",
  "statistical_pairwise_tests.json",
  "narrative_robustness_summary.json",
  "qualitative_case_studies.json",
  "human_review_template.json",
  "mitigation_comparison.json",
  "cross_prompt_comparisons.json",
  "real_case_audit_summary.json",
  "real_case_audit_outputs.json",
  "real_case_domain_summary.json",
  "real_case_examples.json",
  "reports.json",
] as const;

async function fetchJson<T>(filename: string, fallback: T): Promise<T> {
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

const EMPTY_MANIFEST: Manifest = {
  timestamp: "",
  run_label: "empty",
  experiment_token: "",
  selected_source_files: {},
  missing_optional_files: [],
  row_counts: {},
  provider: "unknown",
  model: "unknown",
  prompt_mode: "baseline",
  prompt_modes: [],
  schema_versions: [],
  base_cases: null,
  counterfactual_variants: null,
  flagged_cases: null,
  parse_error_rate: null,
  disclaimer:
    "Research audit interface only. Not legal advice. Not an AI judge. Human legal review required.",
  secrets_excluded: true,
  note: "",
};

const EMPTY_OVERVIEW: OverviewMetrics = {
  total_outputs: 0,
  total_flagged_cases: 0,
  main_legal_framing_flag_rate: null,
  action_type_flip_rate: null,
  remedy_weaker_rate: null,
  evidence_burden_higher_rate: null,
  credibility_more_skeptical_rate: null,
  rights_orientation_weaker_rate: null,
  invalid_citation_rate: null,
  identity_leakage_rate: null,
  strict_counterfactual_variant_types: 0,
  cautious_stress_test_variant_types: 0,
  parse_error_rate: null,
  base_cases: null,
  counterfactual_variants: null,
};

export async function fetchManifest(): Promise<Manifest> {
  return fetchJson<Manifest>("manifest.json", EMPTY_MANIFEST);
}

export async function loadDashboardData(options?: { skipHousingPayload?: boolean; manifest?: Manifest }): Promise<DashboardData> {
  const manifest = options?.manifest ?? (await fetchManifest());
  const isDetention =
    String(manifest.use_case || "").toLowerCase() === "detention" ||
    Boolean(manifest.detention_pilot_corpus_available);

  if (options?.skipHousingPayload || isDetention) {
    const reports = await fetchJson<ReportEntry[]>("reports.json", []);
    return {
      manifest,
      overview: EMPTY_OVERVIEW,
      groupSummary: [],
      pairwise: [],
      flagged: [],
      validity: [],
      validitySummary: [],
      stereotypeGroup: [],
      stereotypeExamples: [],
      hallucinationGroup: [],
      hallucinationPer: [],
      statisticalEffects: [],
      statisticalTests: [],
      narrativeRobustness: [],
      qualitative: [],
      humanReview: [],
      mitigation: [],
      crossPromptComparisons: [],
      realCaseAuditSummary: [],
      realCaseAuditOutputs: [],
      realCaseDomainSummary: [],
      realCaseExamples: [],
      reports,
    };
  }

  return loadHousingDashboardData(manifest);
}

async function loadHousingDashboardData(manifest: Manifest): Promise<DashboardData> {
  const [
    overview,
    groupSummary,
    pairwise,
    flagged,
    validity,
    validitySummary,
    stereotypeGroup,
    stereotypeExamples,
    hallucinationGroup,
    hallucinationPer,
    statisticalEffects,
    statisticalTests,
    narrativeRobustness,
    qualitative,
    humanReview,
    mitigation,
    crossPromptComparisons,
    realCaseAuditSummary,
    realCaseAuditOutputs,
    realCaseDomainSummary,
    realCaseExamples,
    reports,
  ] = await Promise.all([
    fetchJson<OverviewMetrics>("overview_metrics.json", EMPTY_OVERVIEW),
    fetchJson<JsonRecord[]>("group_summary.json", []),
    fetchJson<JsonRecord[]>("pairwise_comparison.json", []),
    fetchJson<JsonRecord[]>("flagged_cases.json", []),
    fetchJson<JsonRecord[]>("counterfactual_validity.json", []),
    fetchJson<JsonRecord[]>("counterfactual_validity_summary.json", []),
    fetchJson<JsonRecord[]>("stereotype_group_summary.json", []),
    fetchJson<JsonRecord[]>("stereotype_flagged_examples.json", []),
    fetchJson<JsonRecord[]>("hallucination_group_summary.json", []),
    fetchJson<JsonRecord[]>("hallucination_per_output.json", []),
    fetchJson<JsonRecord[]>("statistical_group_effects.json", []),
    fetchJson<JsonRecord[]>("statistical_pairwise_tests.json", []),
    fetchJson<JsonRecord[]>("narrative_robustness_summary.json", []),
    fetchJson<JsonRecord[]>("qualitative_case_studies.json", []),
    fetchJson<JsonRecord[]>("human_review_template.json", []),
    fetchJson<JsonRecord[]>("mitigation_comparison.json", []),
    fetchJson<JsonRecord[]>("cross_prompt_comparisons.json", []),
    fetchJson<JsonRecord[]>("real_case_audit_summary.json", []),
    fetchJson<JsonRecord[]>("real_case_audit_outputs.json", []),
    fetchJson<JsonRecord[]>("real_case_domain_summary.json", []),
    fetchJson<JsonRecord[]>("real_case_examples.json", []),
    fetchJson<ReportEntry[]>("reports.json", []),
  ]);

  return {
    manifest,
    overview,
    groupSummary,
    pairwise: enrichRows(pairwise),
    flagged: enrichRows(flagged),
    validity,
    validitySummary,
    stereotypeGroup,
    stereotypeExamples,
    hallucinationGroup,
    hallucinationPer,
    statisticalEffects,
    statisticalTests,
    narrativeRobustness,
    qualitative,
    humanReview,
    mitigation,
    crossPromptComparisons,
    realCaseAuditSummary,
    realCaseAuditOutputs,
    realCaseDomainSummary,
    realCaseExamples,
    reports,
  };
}

export function hasData(rows: JsonRecord[] | undefined): boolean {
  return Array.isArray(rows) && rows.length > 0;
}

export { DATA_FILES };
