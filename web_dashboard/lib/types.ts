export type JsonRecord = Record<string, unknown>;

export interface Manifest {
  timestamp: string;
  use_case?: string;
  run_label: string;
  experiment_token: string;
  selected_source_files: Record<string, string | null>;
  missing_optional_files: string[];
  row_counts: Record<string, number>;
  provider: string;
  model: string;
  prompt_mode: string;
  prompt_modes: string[];
  schema_versions: string[];
  schema_version?: string;
  expanded_run?: boolean;
  minimal_address_run?: boolean;
  cross_prompt_material_instability_count?: number;
  cross_prompt_wording_only_count?: number;
  base_cases: number | null;
  counterfactual_variants: number | null;
  flagged_cases: number | null;
  parse_error_rate: number | null;
  disclaimer: string;
  secrets_excluded: boolean;
  note: string;
  run_type?: string;
  data_status?: string;
  selected_primary_files?: string[];
  cross_prompt_comparisons_available?: boolean;
  cross_prompt_comparison_row_count?: number;
  prompt_modes_detected?: string[];
  output_files_by_prompt_mode?: Record<string, string>;
  missing_prompt_modes_for_comparison?: string[];
  dataset_modes_available?: string[];
  real_case_domains_available?: string[];
  real_case_row_count?: number;
  real_case_source_dataset?: string;
  real_case_limitations?: string;
  real_case_files_selected?: Record<string, string | null>;
  detention_pilot_corpus_available?: boolean;
  detention_pilot_row_count?: number;
  detention_synthetic_rows?: number;
  data_access_policy?: JsonRecord;
  full_text_export_warnings?: string[];
  export_provenance?: {
    git_commit?: string;
    export_git_sha?: string;
    parent_run_id?: string;
    corpus_version?: string;
    flagging_policy?: string;
    flagging_policy_doc?: string;
    dashboard_export_profile?: string;
    pairwise_unique_note?: string;
    headline_metrics_note?: string;
    case_review_split?: boolean;
  };
  export_completeness_score?: number;
  critical_exports_ok?: boolean;
  deploy_blocked?: boolean;
  missing_optional_files_detail?: Array<{ file: string; tabs_affected: string; effect: string }>;
}

export interface OverviewMetrics {
  total_outputs: number;
  total_flagged_cases: number;
  main_legal_framing_flag_rate: number | null;
  action_type_flip_rate: number | null;
  remedy_weaker_rate: number | null;
  evidence_burden_higher_rate: number | null;
  credibility_more_skeptical_rate: number | null;
  rights_orientation_weaker_rate: number | null;
  invalid_citation_rate: number | null;
  identity_leakage_rate: number | null;
  strict_counterfactual_variant_types: number;
  cautious_stress_test_variant_types: number;
  parse_error_rate: number | null;
  base_cases: number | null;
  counterfactual_variants: number | null;
}

export interface ReportEntry {
  report_name: string;
  title: string;
  source_path: string;
  markdown_text: string;
}

export interface DashboardData {
  manifest: Manifest;
  overview: OverviewMetrics;
  groupSummary: JsonRecord[];
  pairwise: JsonRecord[];
  flagged: JsonRecord[];
  validity: JsonRecord[];
  validitySummary: JsonRecord[];
  stereotypeGroup: JsonRecord[];
  stereotypeExamples: JsonRecord[];
  hallucinationGroup: JsonRecord[];
  hallucinationPer: JsonRecord[];
  statisticalEffects: JsonRecord[];
  statisticalTests: JsonRecord[];
  narrativeRobustness: JsonRecord[];
  qualitative: JsonRecord[];
  humanReview: JsonRecord[];
  mitigation: JsonRecord[];
  crossPromptComparisons: JsonRecord[];
  realCaseAuditSummary: JsonRecord[];
  realCaseAuditOutputs: JsonRecord[];
  realCaseDomainSummary: JsonRecord[];
  realCaseExamples: JsonRecord[];
  reports: ReportEntry[];
}

export interface NavSection {
  id: string;
  label: string;
  subtitle?: string;
}

export const NAV_SECTIONS: NavSection[] = [
  { id: "overview", label: "Overview", subtitle: "Executive summary" },
  { id: "audit-story", label: "How the audit works", subtitle: "Step-by-step story" },
  { id: "main-findings", label: "Main findings", subtitle: "Headline audit signals" },
  { id: "flagged-cases", label: "Flagged cases", subtitle: "Triage for legal review" },
  { id: "case-explorer", label: "Inspect a case", subtitle: "Neutral vs variant" },
  { id: "counterfactual-validity", label: "Validity checks", subtitle: "Fact preservation" },
  { id: "mitigation", label: "Mitigation", subtitle: "Prompt strategy comparison" },
  { id: "narrative-robustness", label: "Narrative robustness", subtitle: "Language style effects" },
  { id: "stereotype", label: "Stereotypes", subtitle: "Identity leakage" },
  { id: "hallucination", label: "Hallucination", subtitle: "Source grounding" },
  { id: "statistical", label: "Uncertainty", subtitle: "Confidence intervals" },
  { id: "human-review", label: "Human review", subtitle: "Reviewer workspace" },
  { id: "reports", label: "Reports", subtitle: "Downloads & write-ups" },
  { id: "methodology", label: "Limitations", subtitle: "Methods & caveats" },
];

export const METRIC_DEFINITIONS: Record<string, { label: string; meaning: string }> = {
  legal_framing_bias_flag_rate: {
    label: "Legal framing signal rate",
    meaning: "How often any important legal-framing difference was flagged between neutral and variant memos.",
  },
  action_type_flip_rate: {
    label: "Action changed rate",
    meaning: "How often the recommended action category changed (e.g., temporary relief vs request more evidence).",
  },
  remedy_weaker_rate: {
    label: "Weaker remedy rate",
    meaning: "How often the variant received a weaker remedy than the neutral case.",
  },
  evidence_burden_higher_rate: {
    label: "More evidence requested rate",
    meaning: "How often the variant was asked for more proof before acting.",
  },
  credibility_more_skeptical_rate: {
    label: "More skeptical credibility rate",
    meaning: "How often the variant framed the petitioner with more skepticism.",
  },
  rights_orientation_weaker_rate: {
    label: "Weaker rights framing rate",
    meaning: "How often the variant placed less emphasis on protective rights.",
  },
};

export const GLOSSARY: { term: string; definition: string }[] = [
  {
    term: "Legal framing flag",
    definition:
      "A screening signal that at least one structured legal dimension changed between neutral and variant outputs.",
  },
  {
    term: "Remedy weaker",
    definition: "The variant recommends a less protective or weaker remedy than the neutral memo.",
  },
  {
    term: "Evidence burden higher",
    definition: "The variant asks for more documentation or proof before acting.",
  },
  {
    term: "Credibility more skeptical",
    definition: "The variant frames the petitioner with more doubt or skepticism.",
  },
  {
    term: "Rights orientation weaker",
    definition: "The variant gives less weight to protective or rights-based considerations.",
  },
  {
    term: "Counterfactual validity",
    definition:
      "Whether a variant preserved the same legal facts as the neutral case, or added/changed facts.",
  },
  {
    term: "Identity leakage",
    definition:
      "When demographic identity appears in model reasoning where it is not legally relevant.",
  },
  {
    term: "Hallucination risk",
    definition:
      "When the model cites sources not provided or makes unsupported legal claims in grounded mode.",
  },
  {
    term: "Mitigation mode",
    definition:
      "Prompt strategy (baseline, fairness-aware, demographic-blind) intended to reduce concerning differences.",
  },
  {
    term: "Confidence interval",
    definition:
      "A range estimating where a true rate might fall; wider intervals mean more uncertainty.",
  },
];
