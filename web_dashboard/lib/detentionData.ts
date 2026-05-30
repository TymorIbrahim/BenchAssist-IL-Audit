import type { DashboardData, JsonRecord, Manifest, ReportEntry } from "./types";
import type { CaseReviewIndexEntry, CaseReviewPayload, CaseReviewRecord } from "./detentionCaseReview";
import { dedupeCaseReviewRecords, normalizeCaseReviewRecord } from "./detentionCaseReview";
import { isDetentionUseCase as isDetentionUseCaseLabel } from "./detentionLabels";
import { coerceStringList } from "./format";

export type DetentionDataStatus = "mock" | "pilot" | "gemini" | "gemini_full" | "final" | "empty";

export interface DetentionDashboardBundle {
  manifest: Manifest;
  dataAccessPolicy: JsonRecord;
  overview: JsonRecord;
  pairwise: JsonRecord[];
  groupSummary: JsonRecord[];
  flagged: JsonRecord[];
  realCaseExamples: JsonRecord[];
  realCaseQuality: JsonRecord | null;
  sourceManifest: JsonRecord | null;
  syntheticQa: JsonRecord | null;
  mockRunSummary: JsonRecord | null;
  reports: ReportEntry[];
  crossPromptComparisons: JsonRecord[];
  mitigation: JsonRecord[];
  statisticalEffects: JsonRecord[];
  statisticalTests: JsonRecord[];
  hallucinationGroup: JsonRecord[];
  hallucinationPer: JsonRecord[];
  caseReviewRecords: CaseReviewRecord[];
  caseReviewIndex: CaseReviewIndexEntry[];
  caseReviewMeta: CaseReviewPayload | null;
  caseReviewIndexCount: number;
  caseReviewLoaded: boolean;
  caseReviewSplit: boolean;
  dataStatus: DetentionDataStatus;
  hasFullText: boolean;
  missingFiles: string[];
  isMock: boolean;
  strictEligibleCount: number;
  highPriorityCount: number;
}

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

export async function fetchCaseReviewRecord(recordPath: string): Promise<CaseReviewRecord | null> {
  try {
    const res = await fetch(`/data/${recordPath}`);
    if (!res.ok) return null;
    const record = (await res.json()) as CaseReviewRecord;
    return normalizeCaseReviewRecord(record);
  } catch {
    return null;
  }
}

export async function fetchSplitCaseReviewRecords(
  index: CaseReviewIndexEntry[],
  batchSize = 20,
): Promise<{ records: CaseReviewRecord[]; meta: CaseReviewPayload | null }> {
  const meta = await fetchJson<CaseReviewPayload | null>("detention_case_review_records.json", null);
  const records: CaseReviewRecord[] = [];
  for (let i = 0; i < index.length; i += batchSize) {
    const batch = index.slice(i, i + batchSize);
    const loaded = await Promise.all(
      batch.map((entry) => fetchCaseReviewRecord(entry.record_path || `detention_case_review_records/${entry.review_record_id.replace(/::/g, "__")}.json`)),
    );
    for (const rec of loaded) {
      if (rec) records.push(rec);
    }
  }
  return { records: dedupeCaseReviewRecords(records), meta: meta && typeof meta === "object" ? meta : null };
}

export async function fetchFullCaseReviewRecords(): Promise<{
  records: CaseReviewRecord[];
  meta: CaseReviewPayload | null;
}> {
  const indexPayload = await fetchJson<{
    records_index?: CaseReviewIndexEntry[];
    records_split?: boolean;
    record_count?: number;
  }>("detention_case_review_index.json", {});

  if (indexPayload.records_split && indexPayload.records_index?.length) {
    return fetchSplitCaseReviewRecords(indexPayload.records_index);
  }

  const payload = await fetchJson<CaseReviewPayload | CaseReviewRecord[]>("detention_case_review_records.json", []);
  let records: CaseReviewRecord[] = [];
  let meta: CaseReviewPayload | null = null;
  if (Array.isArray(payload)) {
    records = payload as CaseReviewRecord[];
  } else if (payload && typeof payload === "object" && "records" in payload) {
    meta = payload as CaseReviewPayload;
    if (payload.records_split && indexPayload.records_index?.length) {
      return fetchSplitCaseReviewRecords(indexPayload.records_index);
    }
    records = meta.records ?? [];
  }
  return { records: dedupeCaseReviewRecords(records), meta };
}

function firstRecord(rows: JsonRecord[] | JsonRecord | null | undefined): JsonRecord {
  if (!rows) return {};
  if (Array.isArray(rows)) return rows[0] ?? {};
  return rows as JsonRecord;
}

function normalizePairwiseRow(row: JsonRecord): JsonRecord {
  const parsedFlags = coerceStringList(row.detention_audit_flags);
  return {
    ...row,
    detention_audit_flags_list: parsedFlags,
    review_priority: detentionReviewPriority(row),
    issue_type: parsedFlags[0] ?? str(row.review_label) ?? "Audit signal",
    display_variant: str(row.variant_type).replace(/_/g, " "),
  };
}

function normalizeCrossPromptRow(row: JsonRecord): JsonRecord {
  const fieldsChanged = coerceStringList(row.fields_changed);
  return {
    ...row,
    fields_changed: fieldsChanged,
    fields_changed_list: fieldsChanged,
    n_fields_changed: fieldsChanged.length || Number(row.n_fields_changed) || 0,
  };
}

function str(v: unknown): string {
  if (v == null || v === "null" || (typeof v === "number" && Number.isNaN(v))) return "";
  return String(v);
}

export function detentionReviewPriority(row: JsonRecord): "High" | "Medium" | "Low" {
  if (row.identity_leakage_flag === true || row.identity_leakage_flag === "True") return "High";
  if (row.unsupported_risk_inference_flag === true || row.unsupported_risk_inference_flag === "True") return "High";
  const danger = Number(row.dangerousness_level_delta) || 0;
  const action = Number(row.recommended_action_type_delta) || 0;
  const cred = Number(row.suspect_credibility_framing_shift) || 0;
  if (danger >= 2 || action >= 2 || cred >= 2) return "High";
  if (row.detention_framing_bias_flag === true || row.detention_framing_bias_flag === "True") return "Medium";
  if (danger > 0 || action > 0 || cred > 0) return "Medium";
  return "Low";
}

function inferDataStatus(manifest: Manifest, mockSummary: JsonRecord | null, overview: JsonRecord): DetentionDataStatus {
  const explicit = str(manifest.data_status || overview.data_status).toLowerCase();
  if (explicit === "gemini_full") return "gemini_full";
  if (explicit === "gemini_pilot") return "gemini";

  const run = str(manifest.run_label).toLowerCase();
  if (run.includes("final")) return "final";
  if (run.includes("gemini") && run.includes("full")) return "gemini_full";
  if (run.includes("gemini")) return "gemini";
  if (manifest.detention_pilot_corpus_available) return "pilot";

  // Explicit mock only when not already tagged as a Gemini export.
  if (overview.mock_mode === true || (mockSummary && !explicit)) return "mock";

  // Fallback: infer from overview metrics when metadata fields are missing/stale.
  const nOutputs = Number(overview.n_outputs_total ?? overview.n_parse_success ?? 0);
  if (nOutputs >= 300) return "gemini_full";
  if (nOutputs >= 30) return "gemini";

  return "empty";
}

export async function loadDetentionDashboardData(base: DashboardData): Promise<DetentionDashboardBundle> {
  const [
    overviewArr,
    pairwise,
    groupSummary,
    flagged,
    realCaseExamples,
    realCaseQualityArr,
    sourceManifestArr,
    syntheticQaArr,
    mockRunSummaryArr,
    dataAccessPolicy,
    crossPromptDetention,
    statisticalDetention,
    caseReviewIndexPayload,
  ] = await Promise.all([
    fetchJson<JsonRecord[]>("detention_overview_metrics.json", []),
    fetchJson<JsonRecord[]>("detention_pairwise_comparison.json", []),
    fetchJson<JsonRecord[]>("detention_group_summary.json", []),
    fetchJson<JsonRecord[]>("detention_flagged_cases.json", []),
    fetchJson<JsonRecord[]>("detention_real_case_examples_fulltext.json", []),
    fetchJson<JsonRecord[]>("detention_real_case_quality_report.json", []),
    fetchJson<JsonRecord[]>("detention_source_manifest.json", []),
    fetchJson<JsonRecord[]>("detention_synthetic_data_qa.json", []),
    fetchJson<JsonRecord[]>("detention_mock_run_summary.json", []),
    fetchJson<JsonRecord>("data_access_policy.json", {}),
    fetchJson<JsonRecord[]>("detention_cross_prompt_comparisons.json", []),
    fetchJson<JsonRecord[]>("detention_statistical_tests.json", []),
    fetchJson<{
      record_count?: number;
      flagged_count?: number;
      records_index?: CaseReviewIndexEntry[];
      records_split?: boolean;
    }>("detention_case_review_index.json", {}),
  ]);

  const overview = firstRecord(overviewArr);
  const mockRunSummary = mockRunSummaryArr.length ? mockRunSummaryArr[0] : null;
  const missingFiles = base.manifest.missing_optional_files?.filter((f) => f.startsWith("detention")) ?? [];

  let caseReviewMeta: CaseReviewPayload | null = null;
  const caseReviewRecords: CaseReviewRecord[] = [];
  const caseReviewIndex = caseReviewIndexPayload.records_index ?? [];
  const caseReviewIndexCount =
    Number(caseReviewIndexPayload.record_count) || caseReviewIndex.length || 0;
  const caseReviewSplit = Boolean(caseReviewIndexPayload.records_split);

  const normalizedPairwise = (pairwise.length ? pairwise : flagged).map(normalizePairwiseRow);
  const normalizedFlagged = (flagged.length ? flagged : normalizedPairwise.filter((r) => r.detention_framing_bias_flag)).map(
    normalizePairwiseRow,
  );

  const policy = dataAccessPolicy as JsonRecord;
  const indicators = (policy.detention_fulltext_indicators ?? {}) as JsonRecord;
  const hasFullText =
    Boolean(indicators.contains_unredacted_public_legal_text) ||
    Boolean(policy.contains_unredacted_public_legal_text) ||
    realCaseExamples.length > 0;

  const dataStatus = inferDataStatus(base.manifest, mockRunSummary, overview);
  const isMock = dataStatus === "mock";

  const highPriorityCount = normalizedFlagged.filter((r) => r.review_priority === "High").length;
  const strictEligibleCount = Number(overview.n_pairwise_comparisons) || normalizedPairwise.length;

  return {
    manifest: base.manifest,
    dataAccessPolicy: policy,
    overview,
    pairwise: normalizedPairwise,
    groupSummary,
    flagged: normalizedFlagged,
    realCaseExamples,
    realCaseQuality: realCaseQualityArr.length ? realCaseQualityArr[0] : null,
    sourceManifest: sourceManifestArr.length ? sourceManifestArr[0] : null,
    syntheticQa: syntheticQaArr.length ? syntheticQaArr[0] : null,
    mockRunSummary,
    reports: base.reports.filter(
      (r) => /detention/i.test(r.report_name) || /detention/i.test(r.title),
    ),
    crossPromptComparisons: (crossPromptDetention.length ? crossPromptDetention : (base.crossPromptComparisons ?? [])).map(
      normalizeCrossPromptRow,
    ),
    mitigation: base.mitigation ?? [],
    statisticalEffects: base.statisticalEffects ?? [],
    statisticalTests: statisticalDetention.length ? statisticalDetention : (base.statisticalTests ?? []),
    hallucinationGroup: [],
    hallucinationPer: [],
    caseReviewRecords,
    caseReviewIndex,
    caseReviewMeta,
    caseReviewIndexCount,
    caseReviewLoaded: caseReviewRecords.length > 0,
    caseReviewSplit,
    dataStatus,
    hasFullText,
    missingFiles,
    isMock,
    strictEligibleCount,
    highPriorityCount,
  };
}

export function isDetentionUseCase(manifest: Manifest): boolean {
  const uc = str(manifest.use_case);
  return isDetentionUseCaseLabel(uc) || Boolean(manifest.detention_pilot_corpus_available);
}

export function avgMetric(rows: JsonRecord[], key: string): number | null {
  if (!rows.length) return null;
  const vals = rows.map((r) => Number(r[key])).filter((n) => !Number.isNaN(n));
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}
