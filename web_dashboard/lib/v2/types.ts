/**
 * v2 Types — aligned with detention_minimal_dangerousness_v2 schema.
 * Only fields that actually exist in the exported JSON are typed here.
 */

/* ------------------------------------------------------------------ */
/*  Overview Metrics                                                   */
/* ------------------------------------------------------------------ */

export interface OverviewMetrics {
  use_case: string;
  project_name: string;
  mock_mode: boolean;
  data_status: string;
  expanded_run: boolean;
  minimal_address_run: boolean;
  address_proxy_in_strict_rates: boolean;
  n_pairwise_comparisons_all_modes: number;
  n_flagged_comparisons_all_modes: number;
  n_strict_excluded_review_outputs: number;
  n_address_proxy_review_outputs: number;
  n_real_case_inspired_review_outputs: number;
  parse_success_rate: number;
  n_outputs_total: number;
  n_parse_success: number;
  n_strict_eligible_synthetic: number;
  n_strict_eligible_synthetic_per_prompt_mode: number;
  n_strict_excluded_synthetic: number;
  n_address_proxy_outputs: number;
  n_address_proxy_pairwise_comparisons: number;
  n_real_case_inspired_qualitative: number;
  n_pairwise_comparisons_baseline: number;
  n_flagged_comparisons_baseline: number;
  n_pairwise_comparisons: number;
  n_flagged_comparisons: number;
  n_cross_prompt_comparisons: number;
  n_cross_prompt_instability_flags: number;
  n_cross_prompt_material_instability_flags: number;
  n_cross_prompt_wording_only_changes: number;
  n_synthetic_counterfactual_rows: number;
  disclaimers: string[];
  methodology_note: string;
  schema_version?: string;
}

/* ------------------------------------------------------------------ */
/*  Pairwise Comparison                                                */
/* ------------------------------------------------------------------ */

export interface PairwiseComparison {
  case_id: string;
  variant_id: string;
  variant_type: string;
  protected_attribute_tested: string;
  prompt_mode: string;
  schema_version: string;
  analysis_bucket: string | null;
  dangerousness_level_delta: number;
  dangerousness_escalation_flag: boolean;
  dangerousness_deescalation_flag: boolean;
  insufficient_information_shift: boolean;
  identity_or_proxy_mention_in_reasoning: boolean;
  identity_leakage_flag: boolean;
  identity_leakage_signals: string[];
  address_mention_in_reasoning: boolean;
  reasoning_length_delta: number;
  unsupported_dangerousness_inference_flag: boolean;
  unsupported_risk_inference_flag: boolean;
  dangerousness_level_changed_flag: boolean;
  detention_audit_flags: string[];
  detention_framing_bias_flag: boolean;
  review_label: string | null;
  /* strict demographic fields — may not exist on address proxy rows */
  validity_category?: string;
  fact_preservation_score?: number;
  direct_bias_analysis_eligible?: boolean;
  exclude_from_strict_bias_rates?: boolean;
  reviewer_note?: string;
  /* derived at load time */
  display_variant?: string;
  review_priority?: string;
  issue_type?: string;
}

/* ------------------------------------------------------------------ */
/*  Group Summary                                                      */
/* ------------------------------------------------------------------ */

export interface GroupSummary {
  variant_type: string;
  prompt_mode: string;
  n_comparisons: number;
  mean_dangerousness_delta: number;
  dangerousness_escalation_rate: number;
  insufficient_information_shift_rate: number;
  identity_or_proxy_mention_rate: number;
  address_mention_rate: number;
  identity_leakage_rate: number;
  unsupported_inference_rate: number;
  dangerousness_change_rate: number;
  flagged_rate: number;
  protected_attribute_tested: string;
}

/* ------------------------------------------------------------------ */
/*  Case Review Index Entry                                            */
/* ------------------------------------------------------------------ */

export interface CaseReviewIndexEntry {
  review_record_id: string;
  record_path: string;
  base_case_id: string;
  base_case_title: string;
  variant_id: string;
  variant_type: string;
  variant_label: string;
  prompt_mode: string;
  review_priority: string;
  is_flagged: boolean;
  issue_types: string[];
  protected_attribute_tested: string;
  analysis_bucket: string;
  why_flagged_short: string;
  search_blob: string;
  issue_flags: {
    dangerousness: boolean;
    obstruction: boolean;
    recommended_action: boolean;
    duration: boolean;
    alternatives: boolean;
    safeguards: boolean;
    identity: boolean;
    unsupported: boolean;
  };
}

/* ------------------------------------------------------------------ */
/*  Case Review Record (individual file)                               */
/* ------------------------------------------------------------------ */

export interface CaseReviewRecord {
  review_record_id: string;
  use_case: string;
  data_status: string;
  base_case_id: string;
  base_case_title: string;
  variant_id: string;
  prompt_mode: string;
  dataset_mode: string;
  counterfactual_strength: string;
  use_for_strict_bias_rates: boolean;
  review_priority: string;
  is_flagged: boolean;
  issue_types: string[];
  variant_type: string;
  protected_attribute_tested: string;
  analysis_bucket: string;
  schema_version: string;
  base_case: {
    case_id: string;
    title: string;
    full_case_text: string;
    structured_facts: Record<string, unknown>;
    prompt_input: string;
    full_prompt_sent_to_model?: string;
  };
  variant_case?: {
    case_id?: string;
    title?: string;
    full_case_text: string;
    structured_facts?: Record<string, unknown>;
    prompt_input?: string;
    full_prompt_sent_to_model?: string;
    prompt_mode?: string;
    variant_id?: string;
    variant_label: string;
    what_changed_from_base?: string[] | string;
    legally_relevant_facts_preserved?: boolean;
    facts_preservation_notes?: string;
  };
  neutral_output?: {
    case_summary?: string;
    dangerousness_level?: string;
    reasoning_text?: string;
    [key: string]: unknown;
  };
  variant_output?: {
    case_summary?: string;
    dangerousness_level?: string;
    reasoning_text?: string;
    [key: string]: unknown;
  };
  diff?: {
    dangerousness_shift?: string;
    diff_summary?: string;
    [key: string]: unknown;
  };
  cross_prompt?: {
    modes_available?: string[];
    variant_outputs_by_mode?: Record<string, {
      case_summary?: string;
      dangerousness_level?: string;
      reasoning_text?: string;
      full_memo_text?: string;
    }>;
    cross_prompt_instability?: Array<{
      comparison_mode: string;
      fields_changed: string[];
      n_fields_changed: number;
      cross_prompt_instability_flag: boolean;
      review_note?: string;
    }>;
  };
  review_guidance?: {
    why_flagged?: string;
    plain_language_summary?: string;
    legal_review_questions?: string[];
    caution_note?: string;
  };
}

/* ------------------------------------------------------------------ */
/*  Cross-Prompt Comparison                                            */
/* ------------------------------------------------------------------ */

export interface CrossPromptComparison {
  case_id: string;
  variant_id: string;
  variant_type: string;
  baseline_mode: string;
  comparison_mode: string;
  fields_changed: string[];
  n_fields_changed: number;
  material_fields_changed: string;
  n_material_fields_changed: number;
  reasoning_only_change: boolean;
  cross_prompt_instability_flag: boolean;
  dataset_mode: string;
  exclude_from_strict_bias_rates: boolean;
  review_note: string;
}

export interface CrossPromptModeSummary {
  by_comparison_mode: Record<string, {
    material_instability: number;
    wording_only: number;
    total: number;
  }>;
  note: string;
}

/* ------------------------------------------------------------------ */
/*  Run Manifest                                                       */
/* ------------------------------------------------------------------ */

export interface RunManifest {
  generated_at: string;
  config_path: string;
  run_type: string;
  schema_version: string;
  model: string;
  prompt_modes: string[];
  stats: {
    started_at: string;
    total_planned: number;
    completed: number;
    skipped_resume: number;
    parse_success: number;
    parse_errors: number;
    finished_at: string;
    parse_success_rate: number;
  };
  methodology: {
    strict_fairness_source: string;
    real_cases_in_strict_rates: boolean;
  };
  caution: string;
}

/* ------------------------------------------------------------------ */
/*  Full Metric Summary                                                */
/* ------------------------------------------------------------------ */

export interface FullMetricSummary {
  generated_at: string;
  run_type: string;
  schema_version: string;
  minimal_dangerousness_schema: boolean;
  legacy_metrics_status: string;
  evidence_level: string;
  parse_success_rate: number;
  n_outputs_total: number;
  n_parse_success: number;
  n_strict_eligible_synthetic: number;
  n_strict_eligible_synthetic_per_prompt_mode: number;
  n_strict_excluded_synthetic: number;
  n_address_proxy_outputs: number;
  n_address_proxy_pairwise_comparisons: number;
  address_proxy_in_strict_rates: boolean;
  n_real_case_inspired_qualitative: number;
  per_prompt_mode: Record<string, {
    n_outputs: number;
    n_strict_eligible: number;
    n_strict_excluded: number;
    n_real_case_inspired: number;
  }>;
  n_pairwise_comparisons: number;
  n_pairwise_comparisons_baseline: number;
  n_flagged_comparisons: number;
  n_flagged_comparisons_baseline: number;
  n_cross_prompt_comparisons: number;
  n_cross_prompt_instability_flags: number;
  n_cross_prompt_material_instability_flags: number;
  n_cross_prompt_wording_only_changes: number;
  methodology_note: string;
}

/* ------------------------------------------------------------------ */
/*  Statistical Tests                                                  */
/* ------------------------------------------------------------------ */

export interface StatisticalTest {
  variant_type: string;
  prompt_mode: string;
  n_comparisons: number;
  n_flagged: number;
  flagged_rate: number;
  flagged_rate_ci_low: number;
  flagged_rate_ci_high: number;
  metric: string;
  exploratory_p_value: number;
  fdr_adjusted_p_value: number;
  fdr_significant_at_0_10: boolean;
  interpretation: string;
  sample_size_note: string;
  interpretation_note: string;
}

/* ------------------------------------------------------------------ */
/*  Dashboard Tab                                                      */
/* ------------------------------------------------------------------ */

export type DashboardTab =
  | "overview"
  | "fairness"
  | "mitigation"
  | "bias-analysis"
  | "case-explorer"
  | "agent-audit"
  | "run-metadata";

export interface TabDef {
  id: DashboardTab;
  label: string;
  subtitle: string;
  icon: string;
}

export const DASHBOARD_TABS: TabDef[] = [
  { id: "overview", label: "Overview", subtitle: "Executive summary", icon: "◎" },
  { id: "fairness", label: "Fairness Screening", subtitle: "Demographic & proxy analysis", icon: "◈" },
  { id: "mitigation", label: "Prompt Mitigation", subtitle: "Mode comparison", icon: "◐" },
  { id: "bias-analysis", label: "Bias Analysis", subtitle: "Deep-dive findings", icon: "◉" },
  { id: "case-explorer", label: "Case Explorer", subtitle: "Side-by-side review", icon: "◫" },
  { id: "agent-audit", label: "Agent Audit", subtitle: "Agentic RAG results", icon: "🤖" },
  { id: "run-metadata", label: "Run Metadata", subtitle: "Data quality", icon: "◇" },
];

/* ------------------------------------------------------------------ */
/*  Filter State                                                       */
/* ------------------------------------------------------------------ */

export interface FilterState {
  promptMode: string;
  variantType: string;
  flaggedOnly: boolean;
  shiftDirection: "" | "escalation" | "deescalation" | "unchanged";
  baseCaseId: string;
  search: string;
  analysisBucket: "" | "strict_demographic" | "address_proxy";
}

export const DEFAULT_FILTERS: FilterState = {
  promptMode: "baseline",
  variantType: "",
  flaggedOnly: false,
  shiftDirection: "",
  baseCaseId: "",
  search: "",
  analysisBucket: "",
};

/* ------------------------------------------------------------------ */
/*  Shift Direction                                                    */
/* ------------------------------------------------------------------ */

export type ShiftDirection = "escalation" | "deescalation" | "unchanged";

export interface ShiftCounts {
  escalation: number;
  deescalation: number;
  unchanged: number;
  total: number;
}
