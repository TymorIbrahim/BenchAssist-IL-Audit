import { coerceStringList, str, textDir, toBool } from "./format";
import type { JsonRecord } from "./types";

export function normalizeIssueTypes(value: unknown): string[] {
  return coerceStringList(value).filter((s) => s && !["nan", "none"].includes(s.toLowerCase()));
}

export function normalizeCaseReviewRecord(record: CaseReviewRecord): CaseReviewRecord {
  const whyFlagged = sanitizeReviewText(record.review_guidance?.why_flagged ?? "");
  const issueTypes = normalizeIssueTypes(record.issue_types);
  const resolvedIssues =
    issueTypes.length > 0
      ? issueTypes
      : record.is_flagged
        ? deriveIssueTypesFromDiff(record.diff)
        : [];
  return {
    ...record,
    issue_types: resolvedIssues,
    review_guidance: {
      ...record.review_guidance,
      why_flagged: whyFlagged || defaultWhyFlagged(record),
    },
    cross_prompt: record.cross_prompt
      ? {
          ...record.cross_prompt,
          cross_prompt_instability: (record.cross_prompt.cross_prompt_instability ?? []).map((item) => ({
            ...item,
            fields_changed: normalizeIssueTypes(item.fields_changed),
          })),
        }
      : record.cross_prompt,
  };
}

/** Deduplicate review records that share the same review_record_id (legacy export bug). */
export function dedupeCaseReviewRecords(records: CaseReviewRecord[]): CaseReviewRecord[] {
  const byId = new Map<string, CaseReviewRecord>();
  for (const raw of records) {
    const record = normalizeCaseReviewRecord(raw);
    const id = caseReviewKey(record);
    const existing = byId.get(id);
    if (!existing) {
      byId.set(id, record);
      continue;
    }
    const mergedIssues = [...new Set([...existing.issue_types, ...record.issue_types])];
    byId.set(id, {
      ...existing,
      is_flagged: existing.is_flagged || record.is_flagged,
      issue_types: mergedIssues,
      review_priority:
        existing.review_priority === "high" || record.review_priority === "high"
          ? "high"
          : existing.review_priority === "medium" || record.review_priority === "medium"
            ? "medium"
            : existing.review_priority,
    });
  }
  return Array.from(byId.values());
}

export type ReviewPriority = "low" | "medium" | "high";
export type ReviewDecision =
  | "not_reviewed"
  | "no_concern"
  | "possible_concern"
  | "include_in_report"
  | "needs_discussion";

export interface CaseReviewSide {
  case_id?: string;
  variant_id?: string;
  title?: string;
  full_case_text?: string;
  structured_facts?: JsonRecord;
  prompt_input?: string;
  full_prompt_sent_to_model?: string;
  prompt_reconstruction_status?: string;
  prompt_mode?: string;
  variant_label?: string;
  protected_attribute_tested?: string;
  language_or_framing_condition?: string;
  what_changed_from_base?: string[];
  legally_relevant_facts_preserved?: boolean | null;
  facts_preservation_notes?: string;
}

export interface ModelOutputBlock {
  case_summary?: string | null;
  legal_area?: string | null;
  dangerousness_level?: string | null;
  obstruction_risk_level?: string | null;
  reasonable_suspicion_assessment?: string | null;
  investigative_necessity?: string | null;
  recommended_action_type?: string | null;
  recommended_duration_days?: number | null;
  less_restrictive_alternatives_considered?: string[];
  evidence_burden_level?: string | null;
  suspect_credibility_framing?: string | null;
  rights_orientation?: string | null;
  procedural_safeguards_mentioned?: string[];
  reasoning_text?: string | null;
  evidence_needed?: string[];
  risk_flags?: string[];
  confidence?: number | null;
  limitations?: string[];
  full_memo_text?: string | null;
}

export interface CaseReviewDiff {
  changed_fields?: string[];
  dangerousness_shift?: string | null;
  obstruction_risk_shift?: string | null;
  recommended_action_shift?: string | null;
  duration_shift?: string | null;
  credibility_framing_shift?: string | null;
  rights_orientation_shift?: string | null;
  alternatives_omitted?: boolean;
  procedural_safeguards_omitted?: boolean;
  identity_leakage_flag?: boolean;
  unsupported_risk_inference_flag?: boolean;
  diff_summary?: string;
}

export interface CrossPromptBlock {
  modes_available?: string[];
  variant_outputs_by_mode?: Record<string, ModelOutputBlock>;
  neutral_outputs_by_mode?: Record<string, ModelOutputBlock>;
  cross_prompt_instability?: {
    comparison_mode?: string;
    fields_changed?: string[];
    n_fields_changed?: number;
    cross_prompt_instability_flag?: boolean;
    review_note?: string;
  }[];
}

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
  review_priority: ReviewPriority;
  is_flagged: boolean;
  issue_types: string[];
  variant_type: string;
  protected_attribute_tested: string;
  base_case: CaseReviewSide;
  variant_case: CaseReviewSide;
  neutral_output: ModelOutputBlock;
  variant_output: ModelOutputBlock;
  diff: CaseReviewDiff;
  cross_prompt?: CrossPromptBlock;
  review_guidance: {
    why_flagged: string;
    plain_language_summary: string;
    legal_review_questions: string[];
    caution_note: string;
  };
}

export interface CaseReviewIndexEntry {
  review_record_id: string;
  record_path?: string;
  base_case_id: string;
  base_case_title: string;
  variant_id: string;
  variant_type: string;
  variant_label?: string;
  prompt_mode: string;
  review_priority: ReviewPriority;
  is_flagged: boolean;
  issue_types: string[];
  protected_attribute_tested?: string;
  why_flagged_short?: string;
  search_blob?: string;
  issue_flags?: {
    dangerousness?: boolean;
    obstruction?: boolean;
    recommended_action?: boolean;
    duration?: boolean;
    alternatives?: boolean;
    safeguards?: boolean;
    identity?: boolean;
    unsupported?: boolean;
  };
}

export interface CaseReviewPayload {
  exported_at: string;
  data_status: string;
  prompt_mode: string;
  prompt_reconstruction_note: string;
  record_count: number;
  flagged_count: number;
  records_split?: boolean;
  records_dir?: string;
  records: CaseReviewRecord[];
}

export interface CaseReviewFilters {
  search: string;
  reviewPriority: string;
  issueType: string;
  promptMode: string;
  variantType: string;
  baseCaseId: string;
  protectedAttribute: string;
  strictEligible: string;
  identityLeakage: string;
  unsupportedInference: string;
  localReview: "all" | "reviewed" | "unreviewed";
  focusMode: boolean;
  flaggedOnly: boolean;
  decision: string;
}

export const DEFAULT_CASE_REVIEW_FILTERS: CaseReviewFilters = {
  search: "",
  reviewPriority: "",
  issueType: "",
  promptMode: "",
  variantType: "",
  baseCaseId: "",
  protectedAttribute: "",
  strictEligible: "",
  identityLeakage: "",
  unsupportedInference: "",
  localReview: "all",
  focusMode: false,
  flaggedOnly: false,
  decision: "",
};

export const REVIEW_DECISION_OPTIONS: { value: ReviewDecision; label: string }[] = [
  { value: "not_reviewed", label: "Not reviewed" },
  { value: "no_concern", label: "Reviewed — no concern" },
  { value: "possible_concern", label: "Reviewed — possible concern" },
  { value: "include_in_report", label: "Reviewed — include in report" },
  { value: "needs_discussion", label: "Needs discussion with legal team" },
];

export const OUTPUT_COMPARISON_ROWS: { key: keyof ModelOutputBlock; label: string; list?: boolean }[] = [
  { key: "case_summary", label: "Case summary" },
  { key: "legal_area", label: "Legal area" },
  { key: "dangerousness_level", label: "Dangerousness level" },
  { key: "obstruction_risk_level", label: "Obstruction risk level" },
  { key: "reasonable_suspicion_assessment", label: "Reasonable suspicion" },
  { key: "investigative_necessity", label: "Investigative necessity" },
  { key: "recommended_action_type", label: "Recommended action" },
  { key: "recommended_duration_days", label: "Recommended duration (days)" },
  { key: "less_restrictive_alternatives_considered", label: "Less restrictive alternatives", list: true },
  { key: "procedural_safeguards_mentioned", label: "Procedural safeguards", list: true },
  { key: "evidence_burden_level", label: "Evidence burden level" },
  { key: "suspect_credibility_framing", label: "Credibility framing" },
  { key: "rights_orientation", label: "Rights orientation" },
  { key: "confidence", label: "Confidence" },
  { key: "risk_flags", label: "Risk flags", list: true },
  { key: "evidence_needed", label: "Evidence needed", list: true },
  { key: "limitations", label: "Limitations", list: true },
  { key: "reasoning_text", label: "Reasoning text" },
];

export const ISSUE_EXPLANATIONS: Record<string, string> = {
  dangerousness: "Shows whether the model assessed the variant as more dangerous than the neutral version under intended same legal facts.",
  obstruction: "Shows whether obstruction/contact risk was rated higher for the variant without an intended fact change.",
  recommended_action: "Shows whether the model moved toward stricter detention (extension) or away from release/conditions.",
  duration: "Shows whether recommended detention duration increased between neutral and variant.",
  alternatives: "Flags outputs where less restrictive alternatives appeared in one version but not the other.",
  safeguards: "Flags outputs where procedural safeguards appeared in one version but not the other.",
  identity: "Flags text where identity, language, nationality, or proxy traits may have entered the reasoning.",
  unsupported: "Flags possible risk inferences that may not be supported by the stated legal facts.",
};

export function caseReviewKey(record: CaseReviewRecord | JsonRecord): string {
  return str(record.review_record_id) || `${str(record.base_case_id)}::${str(record.variant_id)}::${str(record.prompt_mode) || "baseline"}`;
}

export function formatOutputValue(value: unknown, list?: boolean): string {
  if (value === null || value === undefined || value === "") return "Not specified";
  if (typeof value === "string" && ["nan", "none", "null"].includes(value.trim().toLowerCase())) return "Not specified";
  if (list || Array.isArray(value)) return coerceStringList(value).join("; ") || "Not specified";
  return String(value).replace(/_/g, " ");
}

function sanitizeReviewText(text: string): string {
  const cleaned = str(text).trim();
  if (!cleaned || cleaned.toLowerCase().includes(": nan") || cleaned.toLowerCase() === "nan") return "";
  return cleaned;
}

function deriveIssueTypesFromDiff(diff: CaseReviewDiff): string[] {
  const out: string[] = [];
  if (diff.dangerousness_shift) out.push(`Dangerousness shift: ${diff.dangerousness_shift}`);
  if (diff.obstruction_risk_shift) out.push(`Obstruction shift: ${diff.obstruction_risk_shift}`);
  if (diff.recommended_action_shift) out.push(`Action shift: ${diff.recommended_action_shift}`);
  if (diff.duration_shift) out.push(`Duration shift: ${diff.duration_shift}`);
  if (toBool(diff.alternatives_omitted)) out.push("Alternatives omitted in variant");
  if (toBool(diff.procedural_safeguards_omitted)) out.push("Safeguards omitted in variant");
  if (toBool(diff.identity_leakage_flag)) out.push("Possible identity/proxy language");
  if (toBool(diff.unsupported_risk_inference_flag)) out.push("Possible unsupported risk inference");
  return out;
}

export function defaultWhyFlagged(record: CaseReviewRecord): string {
  if (!record.is_flagged) return "Not flagged — included for controlled-comparison review.";
  if (record.diff.diff_summary && record.diff.diff_summary !== "No structured output field changes detected.") {
    return `Flagged because: ${record.diff.diff_summary}`;
  }
  return "Flagged for expert legal review.";
}

export function displayWhyFlagged(record: CaseReviewRecord): string {
  return record.review_guidance.why_flagged || defaultWhyFlagged(record);
}

export function outputDiffIndicator(
  field: keyof ModelOutputBlock,
  neutral: ModelOutputBlock,
  variant: ModelOutputBlock,
  diff: CaseReviewDiff,
): { changed: boolean; signal: string; tone: "neutral" | "changed" | "risk" | "omit" } {
  const n = formatOutputValue(neutral[field], OUTPUT_COMPARISON_ROWS.find((r) => r.key === field)?.list);
  const v = formatOutputValue(variant[field], OUTPUT_COMPARISON_ROWS.find((r) => r.key === field)?.list);
  const changedFields = diff.changed_fields ?? [];
  const fieldName = String(field);
  const changed = changedFields.includes(fieldName) || n !== v;

  if (!changed) return { changed: false, signal: "Unchanged", tone: "neutral" };

  if (field === "less_restrictive_alternatives_considered" && diff.alternatives_omitted) {
    return { changed: true, signal: "Omitted in variant", tone: "omit" };
  }
  if (field === "procedural_safeguards_mentioned" && diff.procedural_safeguards_omitted) {
    return { changed: true, signal: "Omitted in variant", tone: "omit" };
  }
  if (field === "dangerousness_level" && diff.dangerousness_shift === "increased") {
    return { changed: true, signal: "Increased risk", tone: "risk" };
  }
  if (field === "obstruction_risk_level" && diff.obstruction_risk_shift === "increased") {
    return { changed: true, signal: "Increased risk", tone: "risk" };
  }
  if (field === "recommended_action_type" && diff.recommended_action_shift === "stricter recommendation") {
    return { changed: true, signal: "Stricter recommendation", tone: "risk" };
  }
  if (field === "recommended_duration_days" && diff.duration_shift === "longer duration") {
    return { changed: true, signal: "Longer duration", tone: "risk" };
  }
  return { changed: true, signal: "Changed", tone: "changed" };
}

export function filterCaseReviewRecords(
  records: CaseReviewRecord[],
  filters: CaseReviewFilters,
  reviewState: Record<string, { reviewed?: boolean; decision?: ReviewDecision }>,
): CaseReviewRecord[] {
  let rows = [...records];
  if (filters.focusMode) {
    rows = rows.filter((r) => r.is_flagged && (r.review_priority === "high" || r.review_priority === "medium"));
  }
  if (filters.flaggedOnly) rows = rows.filter((r) => r.is_flagged);
  if (filters.reviewPriority) rows = rows.filter((r) => r.review_priority === filters.reviewPriority);
  if (filters.issueType) rows = rows.filter((r) => r.issue_types.some((t) => t.toLowerCase().includes(filters.issueType.toLowerCase())));
  if (filters.promptMode) rows = rows.filter((r) => r.prompt_mode === filters.promptMode);
  if (filters.variantType) rows = rows.filter((r) => r.variant_type === filters.variantType);
  if (filters.baseCaseId) rows = rows.filter((r) => r.base_case_id === filters.baseCaseId);
  if (filters.protectedAttribute) rows = rows.filter((r) => r.protected_attribute_tested === filters.protectedAttribute);
  if (filters.strictEligible === "yes") rows = rows.filter((r) => r.use_for_strict_bias_rates);
  if (filters.strictEligible === "no") rows = rows.filter((r) => !r.use_for_strict_bias_rates);
  if (filters.identityLeakage === "yes") rows = rows.filter((r) => toBool(r.diff.identity_leakage_flag));
  if (filters.identityLeakage === "no") rows = rows.filter((r) => !toBool(r.diff.identity_leakage_flag));
  if (filters.unsupportedInference === "yes") rows = rows.filter((r) => toBool(r.diff.unsupported_risk_inference_flag));
  if (filters.unsupportedInference === "no") rows = rows.filter((r) => !toBool(r.diff.unsupported_risk_inference_flag));
  if (filters.localReview === "reviewed") rows = rows.filter((r) => reviewState[caseReviewKey(r)]?.reviewed);
  if (filters.localReview === "unreviewed") rows = rows.filter((r) => !reviewState[caseReviewKey(r)]?.reviewed);
  if (filters.decision) rows = rows.filter((r) => (reviewState[caseReviewKey(r)]?.decision ?? "not_reviewed") === filters.decision);
  if (filters.search.trim()) {
    const q = filters.search.toLowerCase();
    rows = rows.filter((r) => {
      const memoBlob = [
        r.neutral_output.full_memo_text,
        r.variant_output.full_memo_text,
        r.neutral_output.reasoning_text,
        r.variant_output.reasoning_text,
      ]
        .filter(Boolean)
        .join(" ");
      return [r.base_case_title, r.base_case_id, r.variant_id, r.variant_type, r.review_guidance.plain_language_summary, ...r.issue_types, memoBlob]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }
  return rows;
}

export function groupRecordsByIssue(records: CaseReviewRecord[]): { key: string; label: string; explanation: string; records: CaseReviewRecord[] }[] {
  const groups: { key: string; label: string; explanation: string; match: (r: CaseReviewRecord) => boolean }[] = [
    { key: "dangerousness", label: "Dangerousness shifts", explanation: ISSUE_EXPLANATIONS.dangerousness, match: (r) => Boolean(r.diff.dangerousness_shift) },
    { key: "obstruction", label: "Obstruction-risk shifts", explanation: ISSUE_EXPLANATIONS.obstruction, match: (r) => Boolean(r.diff.obstruction_risk_shift) },
    { key: "recommended_action", label: "Recommended-action shifts", explanation: ISSUE_EXPLANATIONS.recommended_action, match: (r) => Boolean(r.diff.recommended_action_shift) },
    { key: "duration", label: "Detention-duration shifts", explanation: ISSUE_EXPLANATIONS.duration, match: (r) => Boolean(r.diff.duration_shift) },
    { key: "alternatives", label: "Omitted alternatives", explanation: ISSUE_EXPLANATIONS.alternatives, match: (r) => toBool(r.diff.alternatives_omitted) },
    { key: "safeguards", label: "Omitted safeguards", explanation: ISSUE_EXPLANATIONS.safeguards, match: (r) => toBool(r.diff.procedural_safeguards_omitted) },
    { key: "identity", label: "Identity/proxy leakage", explanation: ISSUE_EXPLANATIONS.identity, match: (r) => toBool(r.diff.identity_leakage_flag) },
    { key: "unsupported", label: "Unsupported risk inference", explanation: ISSUE_EXPLANATIONS.unsupported, match: (r) => toBool(r.diff.unsupported_risk_inference_flag) },
  ];
  return groups
    .map((g) => ({ key: g.key, label: g.label, explanation: g.explanation, records: records.filter((r) => r.is_flagged && g.match(r)) }))
    .filter((g) => g.records.length > 0);
}

export function dirForText(text: string): "rtl" | "ltr" {
  return textDir(text || "");
}

export function exampleReviewRecord(records: CaseReviewRecord[]): CaseReviewRecord | null {
  return records.find((r) => r.is_flagged) ?? records[0] ?? null;
}
