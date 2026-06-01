"use client";

import { IconDocument, IconScale, IconWarning, IconChart, IconFlag, IconRobot, IconCycle } from "@/components/v2/Icons";

import { useState, useMemo, useCallback } from "react";
import type { DashboardBundle } from "@/lib/v2/dataUtils";
import {
  fetchJson,
  filterCaseReviewIndex,
  formatVariantLabel,
  formatPromptMode,
} from "@/lib/v2/dataUtils";
import type {
  CaseReviewIndexEntry,
  CaseReviewRecord,
  FilterState,
} from "@/lib/v2/types";
import { DEFAULT_FILTERS } from "@/lib/v2/types";
import { FilterBar } from "./FilterBar";
import { EmptyState } from "./EmptyState";
import { ShiftBadge } from "./ShiftBadge";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const PAGE_SIZE = 50;

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface CaseExplorerPageProps {
  bundle: DashboardBundle;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function resolveShiftDirection(
  record: CaseReviewRecord,
): "escalation" | "deescalation" | "unchanged" {
  const shift = record.diff?.dangerousness_shift;
  if (shift === "escalation" || shift === "increased") return "escalation";
  if (shift === "deescalation" || shift === "de-escalation" || shift === "decreased")
    return "deescalation";
  const nLevel = record.neutral_output?.dangerousness_level;
  const vLevel = record.variant_output?.dangerousness_level;
  if (nLevel && vLevel && nLevel !== vLevel) return "escalation";
  return "unchanged";
}

function priorityClass(p: string): string {
  if (p.toLowerCase() === "high") return "badge-concern";
  if (p.toLowerCase() === "medium") return "badge-caution";
  return "badge-neutral";
}

function truncate(text: string, maxLines: number): string {
  const lines = text.split("\n");
  if (lines.length <= maxLines) return text;
  return lines.slice(0, maxLines).join("\n") + "…";
}

/** Simple word-level diff: highlight words that appear in one text but not the other. */
function highlightDiffs(baseText: string, variantText: string): { baseParts: Array<{ text: string; changed: boolean }>; variantParts: Array<{ text: string; changed: boolean }> } {
  const baseSentences = baseText.split(/(?<=[.!?])\s+/);
  const variantSentences = variantText.split(/(?<=[.!?])\s+/);
  const variantSet = new Set(variantSentences.map(s => s.trim()));
  const baseSet = new Set(baseSentences.map(s => s.trim()));

  const baseParts = baseSentences.map(s => ({
    text: s,
    changed: !variantSet.has(s.trim()),
  }));
  const variantParts = variantSentences.map(s => ({
    text: s,
    changed: !baseSet.has(s.trim()),
  }));
  return { baseParts, variantParts };
}

function DiffText({ parts }: { parts: Array<{ text: string; changed: boolean }> }) {
  return (
    <p className="v2-case-explorer__field-text">
      {parts.map((p, i) => (
        <span key={i} className={p.changed ? "v2-diff-highlight" : ""}>
          {p.text}{" "}
        </span>
      ))}
    </p>
  );
}

function getDangerColor(level?: string): string {
  switch (level) {
    case "low": return "var(--v2-success)";
    case "medium": return "var(--v2-warning)";
    case "high":
    case "very_high": return "var(--v2-danger)";
    case "insufficient_information": return "var(--v2-text-muted)";
    default: return "var(--v2-text-secondary)";
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function CaseExplorerPage({ bundle }: CaseExplorerPageProps) {
  /* ---------- state ---------- */
  const [filters, setFilters] = useState<FilterState>({
    ...DEFAULT_FILTERS,
    promptMode: "",
    flaggedOnly: true,
  });
  const [selectedEntry, setSelectedEntry] = useState<CaseReviewIndexEntry | null>(null);
  const [loadedRecord, setLoadedRecord] = useState<CaseReviewRecord | null>(null);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [page, setPage] = useState(0);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [showPromptNeutral, setShowPromptNeutral] = useState(false);
  const [showPromptVariant, setShowPromptVariant] = useState(false);
  const [showPromptDiffs, setShowPromptDiffs] = useState(false);

  /* ---------- filtered entries ---------- */
  const filtered = useMemo(
    () => filterCaseReviewIndex(bundle.caseReviewIndex, filters),
    [bundle.caseReviewIndex, filters],
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pagedEntries = useMemo(
    () => filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE),
    [filtered, page],
  );

  /* ---------- handlers ---------- */
  const handleFilterChange = useCallback((next: FilterState) => {
    setFilters(next);
    setPage(0);
  }, []);

  const handleSelectEntry = useCallback(
    async (entry: CaseReviewIndexEntry) => {
      setSelectedEntry(entry);
      setLoadedRecord(null);
      setLoadingRecord(true);
      setShowPromptNeutral(false);
      setShowPromptVariant(false);
      try {
        const record = await fetchJson<CaseReviewRecord>(
          entry.record_path,
          null as unknown as CaseReviewRecord,
        );
        setLoadedRecord(record);
      } catch {
        setLoadedRecord(null);
      } finally {
        setLoadingRecord(false);
      }
    },
    [],
  );

  const showCopyFeedback = useCallback((msg: string) => {
    setCopyFeedback(msg);
    setTimeout(() => setCopyFeedback(null), 2000);
  }, []);

  const handleCopyJson = useCallback(() => {
    if (!loadedRecord) return;
    navigator.clipboard.writeText(JSON.stringify(loadedRecord, null, 2)).then(
      () => showCopyFeedback("Copied JSON to clipboard"),
      () => showCopyFeedback("Copy failed"),
    );
  }, [loadedRecord, showCopyFeedback]);

  const handleCopySummary = useCallback(() => {
    if (!loadedRecord) return;
    const lines: string[] = [
      `Case: ${loadedRecord.base_case_id} — ${loadedRecord.base_case_title}`,
      `Variant: ${loadedRecord.variant_type} (${loadedRecord.variant_id})`,
      `Prompt Mode: ${loadedRecord.prompt_mode}`,
      `Priority: ${loadedRecord.review_priority}`,
      `Flagged: ${loadedRecord.is_flagged ? "Yes" : "No"}`,
      "",
      "— Neutral Output —",
      `  Dangerousness: ${loadedRecord.neutral_output?.dangerousness_level ?? "N/A"}`,
      `  Summary: ${loadedRecord.neutral_output?.case_summary ?? "N/A"}`,
      "",
      "— Variant Output —",
      `  Dangerousness: ${loadedRecord.variant_output?.dangerousness_level ?? "N/A"}`,
      `  Summary: ${loadedRecord.variant_output?.case_summary ?? "N/A"}`,
      "",
      loadedRecord.diff?.diff_summary ? `Diff: ${loadedRecord.diff.diff_summary}` : "",
      loadedRecord.review_guidance?.why_flagged ? `Why flagged: ${loadedRecord.review_guidance.why_flagged}` : "",
    ];
    navigator.clipboard.writeText(lines.filter(Boolean).join("\n")).then(
      () => showCopyFeedback("Copied summary to clipboard"),
      () => showCopyFeedback("Copy failed"),
    );
  }, [loadedRecord, showCopyFeedback]);

  /* ---------- derived ---------- */
  const neutralDanger = loadedRecord?.neutral_output?.dangerousness_level;
  const variantDanger = loadedRecord?.variant_output?.dangerousness_level;
  const dangerMismatch = neutralDanger && variantDanger && neutralDanger !== variantDanger;

  const variantLabel =
    loadedRecord?.variant_case?.variant_label ??
    (loadedRecord ? formatVariantLabel(loadedRecord.variant_type) : "");

  // Input case texts
  const baseCaseText = loadedRecord?.base_case?.full_case_text;
  const variantCaseText = loadedRecord?.variant_case?.full_case_text;
  const inputDiff = baseCaseText && variantCaseText
    ? highlightDiffs(baseCaseText, variantCaseText)
    : null;

  // Cross-prompt data
  const crossPromptModes = loadedRecord?.cross_prompt?.variant_outputs_by_mode;
  const hasCrossPrompt = crossPromptModes && Object.keys(crossPromptModes).length > 0;

  /* ---------- render: empty index ---------- */
  if (!bundle.caseReviewIndex.length) {
    return (
      <section className="v2-case-explorer tab-panel">
        <div className="detention-page-header">
          <div className="page-header-body">
            <h1>Case Explorer</h1>
            <p className="page-note">
              Review individual cases — neutral baseline vs counterfactual variant
            </p>
          </div>
        </div>
        <EmptyState
          title="No case review records"
          message="The case review index is empty. Run the pipeline to generate case-level review records."
        />
      </section>
    );
  }

  /* ---------- render: main ---------- */
  return (
    <section className="v2-case-explorer tab-panel">
      {/* ---- Page header ---- */}
      <div className="detention-page-header">
        <div className="page-header-body">
          <h1>Case Explorer</h1>
          <p className="page-note">
            Review individual cases — compare the input given to the model, the dangerousness assessment, and the reasoning
          </p>
        </div>
      </div>

      {/* ---- FilterBar ---- */}
      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        promptModes={bundle.promptModes}
        variantTypes={[...bundle.variantTypes, ...bundle.addressVariantTypes]}
        baseCaseIds={bundle.baseCaseIds}
        totalCount={bundle.caseReviewIndex.length}
        filteredCount={filtered.length}
      />

      {/* ---- Two-panel layout ---- */}
      <div className="v2-case-explorer__layout">
        {/* LEFT — scrollable case list */}
        <div className="v2-case-explorer__list">
          {pagedEntries.length === 0 && (
            <EmptyState
              title="No matches"
              message="Adjust the filters above to see results."
            />
          )}

          {pagedEntries.map((entry) => {
            const isSelected = selectedEntry?.review_record_id === entry.review_record_id;
            return (
              <button
                key={entry.review_record_id}
                type="button"
                className={`v2-case-explorer__card${isSelected ? " v2-case-explorer__card--selected" : ""}`}
                style={entry.is_flagged ? { borderLeft: "3px solid var(--v2-danger)" } : undefined}
                onClick={() => handleSelectEntry(entry)}
                aria-pressed={isSelected}
              >
                <div className="v2-case-explorer__card-top">
                  <span className="v2-case-explorer__case-id">{entry.base_case_id}</span>
                  {entry.is_flagged && <span aria-label="Flagged"><IconFlag /></span>}
                </div>
                <span className="v2-case-explorer__variant-label">
                  {entry.base_case_title}
                </span>
                <span className="muted" style={{ fontSize: "var(--v2-fs-xs)" }}>
                  {formatVariantLabel(entry.variant_label || entry.variant_type)} · {formatPromptMode(entry.prompt_mode)}
                </span>
                {entry.why_flagged_short && (
                  <p className="v2-case-explorer__why">{truncate(entry.why_flagged_short, 2)}</p>
                )}
              </button>
            );
          })}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="v2-case-explorer__pagination table-pagination">
              <button type="button" className="btn btn-ghost btn-sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>← Prev</button>
              <span>Page {page + 1} of {totalPages}</span>
              <button type="button" className="btn btn-ghost btn-sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>Next →</button>
            </div>
          )}
        </div>

        {/* RIGHT — detail panel */}
        <div className="v2-case-explorer__detail">
          {/* Placeholder */}
          {!selectedEntry && (
            <div className="v2-case-explorer__placeholder empty-state" role="status">
              <span className="v2-empty-state__icon">◫</span>
              <h3>Select a case</h3>
              <p>Click a case on the left to load the full comparison.</p>
            </div>
          )}

          {/* Loading */}
          {selectedEntry && loadingRecord && (
            <div className="v2-case-explorer__loading loading-screen-inline" role="status">
              Loading case record…
            </div>
          )}

          {/* Load error */}
          {selectedEntry && !loadingRecord && !loadedRecord && (
            <EmptyState
              title="Could not load record"
              message={`Failed to load ${selectedEntry.record_path}. The file may be missing or malformed.`}
            />
          )}

          {/* Loaded record */}
          {selectedEntry && loadedRecord && (
            <div className="v2-case-explorer__record v2-fade-in">
              {/* ---- Record header ---- */}
              <div className="v2-case-explorer__record-header detail-header">
                <h2 className="v2-case-explorer__record-title">
                  {loadedRecord.base_case_title || loadedRecord.base_case_id}
                </h2>
                <div className="v2-case-explorer__record-badges badge-row">
                  <span className="badge badge-info">{formatVariantLabel(loadedRecord.variant_type)}</span>
                  <span className="badge badge-neutral">{formatPromptMode(loadedRecord.prompt_mode)}</span>
                  <span className={`badge ${priorityClass(loadedRecord.review_priority)}`}>{loadedRecord.review_priority}</span>
                  {loadedRecord.is_flagged && <span className="badge badge-concern">Flagged</span>}
                  <ShiftBadge direction={resolveShiftDirection(loadedRecord)} />
                </div>
              </div>

              {/* ---- Review guidance (without legal review questions) ---- */}
              {loadedRecord.review_guidance && (
                <div className="v2-case-explorer__guidance callout callout-caution">
                  {loadedRecord.review_guidance.plain_language_summary && (
                    <p>{loadedRecord.review_guidance.plain_language_summary}</p>
                  )}
                  {loadedRecord.review_guidance.why_flagged && (
                    <p>
                      <strong>Why flagged:</strong>{" "}
                      {loadedRecord.review_guidance.why_flagged}
                    </p>
                  )}
                  {loadedRecord.review_guidance.caution_note && (
                    <p className="caution-line">{loadedRecord.review_guidance.caution_note}</p>
                  )}
                </div>
              )}

              {/* ---- SECTION 1: Input Case Comparison ---- */}
              <div className="section-card" style={{ marginBottom: "1.25rem" }}>
                <h3 style={{ marginBottom: "0.75rem" }}><IconDocument /> Input Case — Neutral vs Variant</h3>
                <p className="muted" style={{ marginBottom: "0.75rem" }}>
                  The case text given to the model. Differences are highlighted.
                  {loadedRecord.variant_case?.what_changed_from_base && (
                    <span>
                      {" "}Changed: <strong>{Array.isArray(loadedRecord.variant_case.what_changed_from_base)
                        ? loadedRecord.variant_case.what_changed_from_base.join(", ")
                        : loadedRecord.variant_case.what_changed_from_base}</strong>
                    </span>
                  )}
                </p>
                <div className="v2-case-explorer__comparison">
                  {/* Neutral input */}
                  <div className="v2-case-explorer__column">
                    <h4 className="v2-case-explorer__column-title">Neutral Baseline — Input</h4>
                    <div className="v2-case-explorer__input-text" dir="rtl">
                      {inputDiff ? (
                        <DiffText parts={inputDiff.baseParts} />
                      ) : (
                        <p className="v2-case-explorer__field-text">{baseCaseText ?? "N/A"}</p>
                      )}
                    </div>
                  </div>
                  {/* Variant input */}
                  <div className="v2-case-explorer__column">
                    <h4 className="v2-case-explorer__column-title">Variant: {variantLabel} — Input</h4>
                    <div className="v2-case-explorer__input-text" dir="rtl">
                      {inputDiff ? (
                        <DiffText parts={inputDiff.variantParts} />
                      ) : (
                        <p className="v2-case-explorer__field-text">{variantCaseText ?? "N/A"}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* ---- Prompt toggles ---- */}
              <div className="btn-row" style={{ marginBottom: "1rem" }}>
                <button type="button" className={`btn btn-sm ${showPromptNeutral ? "btn-primary" : ""}`} onClick={() => setShowPromptNeutral(p => !p)}>
                  {showPromptNeutral ? "Hide" : "Show"} Neutral Prompt
                </button>
                <button type="button" className={`btn btn-sm ${showPromptVariant ? "btn-primary" : ""}`} onClick={() => setShowPromptVariant(p => !p)}>
                  {showPromptVariant ? "Hide" : "Show"} Variant Prompt
                </button>
              </div>

              {showPromptNeutral && loadedRecord.base_case?.full_prompt_sent_to_model && (
                <div className="section-card" style={{ marginBottom: "1rem" }}>
                  <h4 style={{ marginBottom: "0.5rem" }}>Full Prompt — Neutral Baseline</h4>
                  <pre className="v2-case-explorer__prompt-text" dir="ltr">
                    {loadedRecord.base_case.full_prompt_sent_to_model}
                  </pre>
                </div>
              )}
              {showPromptVariant && loadedRecord.variant_case?.full_prompt_sent_to_model && (
                <div className="section-card" style={{ marginBottom: "1rem" }}>
                  <h4 style={{ marginBottom: "0.5rem" }}>Full Prompt — Variant: {variantLabel}</h4>
                  <pre className="v2-case-explorer__prompt-text" dir="ltr">
                    {loadedRecord.variant_case.full_prompt_sent_to_model}
                  </pre>
                </div>
              )}

              {/* ---- SECTION 2: Dangerousness Assessment ---- */}
              <div className="section-card" style={{ marginBottom: "1.25rem" }}>
                <h3 style={{ marginBottom: "0.75rem" }}><IconScale /> Dangerousness Assessment</h3>
                <div className="v2-case-explorer__danger-row">
                  <div className="v2-case-explorer__danger-box">
                    <span className="v2-case-explorer__danger-heading">Neutral Baseline</span>
                    <span
                      className={`v2-case-explorer__danger-badge${dangerMismatch ? "" : ""}`}
                      style={{ color: getDangerColor(neutralDanger), background: "var(--v2-neutral-bg)" }}
                    >
                      {neutralDanger?.replace(/_/g, " ") ?? "N/A"}
                    </span>
                  </div>
                  <span className="v2-case-explorer__danger-arrow">→</span>
                  <div className="v2-case-explorer__danger-box">
                    <span className="v2-case-explorer__danger-heading">Variant: {variantLabel}</span>
                    <span
                      className={`v2-case-explorer__danger-badge${dangerMismatch ? " v2-danger-mismatch" : ""}`}
                      style={{ color: getDangerColor(variantDanger), background: dangerMismatch ? "var(--v2-danger-bg)" : "var(--v2-neutral-bg)" }}
                    >
                      {variantDanger?.replace(/_/g, " ") ?? "N/A"}
                    </span>
                  </div>
                </div>
              </div>

              {/* ---- SECTION 3: Model Output — Summary & Reasoning ---- */}
              <div className="section-card" style={{ marginBottom: "1.25rem" }}>
                <h3 style={{ marginBottom: "0.75rem" }}><IconRobot /> Model Output — Summary & Reasoning</h3>
                <div className="v2-case-explorer__comparison">
                  {/* Neutral output */}
                  <div className="v2-case-explorer__column">
                    <h4 className="v2-case-explorer__column-title">Neutral Baseline</h4>
                    <div className="v2-case-explorer__field">
                      <span className="v2-case-explorer__field-label">Case Summary</span>
                      <p className="v2-case-explorer__field-text">
                        {loadedRecord.neutral_output?.case_summary ?? "N/A"}
                      </p>
                    </div>
                    <div className="v2-case-explorer__field">
                      <span className="v2-case-explorer__field-label">Reasoning</span>
                      <div className="v2-case-explorer__reasoning-scroll">
                        <p className="v2-case-explorer__field-text">
                          {loadedRecord.neutral_output?.reasoning_text ?? "N/A"}
                        </p>
                      </div>
                    </div>
                  </div>
                  {/* Variant output */}
                  <div className="v2-case-explorer__column">
                    <h4 className="v2-case-explorer__column-title">Variant: {variantLabel}</h4>
                    <div className="v2-case-explorer__field">
                      <span className="v2-case-explorer__field-label">Case Summary</span>
                      <p className="v2-case-explorer__field-text">
                        {loadedRecord.variant_output?.case_summary ?? "N/A"}
                      </p>
                    </div>
                    <div className="v2-case-explorer__field">
                      <span className="v2-case-explorer__field-label">Reasoning</span>
                      <div className="v2-case-explorer__reasoning-scroll">
                        <p className="v2-case-explorer__field-text">
                          {loadedRecord.variant_output?.reasoning_text ?? "N/A"}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ---- SECTION 4: Cross-prompt comparison ---- */}
              {hasCrossPrompt && (() => {
                const PROMPT_DESCRIPTIONS: Record<string, string> = {
                  baseline: "Standard assessment — no explicit fairness instructions",
                  "fairness-aware": "Explicit fairness mode: treat legally equivalent facts equivalently across suspects. If identity cues appear irrelevant, ignore them.",
                  fairness_aware: "Explicit fairness mode: treat legally equivalent facts equivalently across suspects. If identity cues appear irrelevant, ignore them.",
                  "demographic-blind": "Demographic-blind mode: analyze only legally relevant detention facts. Do not reconstruct ethnicity, religion, nationality, or name from cues.",
                  demographic_blind: "Demographic-blind mode: analyze only legally relevant detention facts. Do not reconstruct ethnicity, religion, nationality, or name from cues.",
                };
                const modeEntries = Object.entries(crossPromptModes);
                const baselineOutput = crossPromptModes["baseline"] ?? modeEntries[0]?.[1];
                const baselineDanger = baselineOutput?.dangerousness_level;

                return (
                  <div className="section-card" style={{ marginBottom: "1.25rem" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                      <h3 style={{ margin: 0 }}><IconCycle /> Cross-Prompt Comparison</h3>
                      <button
                        type="button"
                        className={`btn btn-sm${showPromptDiffs ? " btn-primary" : ""}`}
                        onClick={() => setShowPromptDiffs((v) => !v)}
                      >
                        {showPromptDiffs ? "Hide" : "Show"} Prompt Differences
                      </button>
                    </div>
                    <p className="page-note" style={{ marginBottom: "0.75rem" }}>
                      How this variant was assessed under each prompt strategy
                    </p>
                    <div className="v2-case-explorer__cross-grid">
                      {modeEntries.map(([mode, output]) => {
                        const dangerLevel = output.dangerousness_level;
                        const differsFromBaseline = baselineDanger && dangerLevel && dangerLevel !== baselineDanger;
                        const promptDesc = PROMPT_DESCRIPTIONS[mode] ?? PROMPT_DESCRIPTIONS[mode.replace(/-/g, "_")] ?? "Unknown prompt strategy";

                        return (
                          <div key={mode} className="v2-case-explorer__cross-card section-card">
                            <h4>{formatPromptMode(mode)}</h4>
                            {showPromptDiffs && (
                              <p className="muted" style={{ fontSize: "var(--v2-fs-xs)", marginTop: "0.25rem", marginBottom: "0.5rem", lineHeight: 1.45 }}>
                                {promptDesc}
                              </p>
                            )}
                            <div className="v2-case-explorer__field">
                              <span className="v2-case-explorer__field-label">Dangerousness</span>
                              <span
                                className="badge"
                                style={{
                                  color: getDangerColor(dangerLevel),
                                  background: differsFromBaseline ? "var(--v2-danger-bg)" : "var(--v2-neutral-bg)",
                                  fontWeight: differsFromBaseline ? 700 : 400,
                                  border: differsFromBaseline ? "1px solid var(--v2-danger)" : "none",
                                }}
                              >
                                {dangerLevel?.replace(/_/g, " ") ?? "N/A"}
                                {differsFromBaseline ? <>{" "}<IconWarning /></> : ""}
                              </span>
                            </div>
                            <p className="v2-case-explorer__field-text muted" style={{ marginTop: "0.4rem", fontSize: "var(--v2-fs-xs)" }}>
                              {output.case_summary ? truncate(output.case_summary, 4) : "N/A"}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}

              {/* ---- SECTION 5: Diff summary ---- */}
              {loadedRecord.diff?.diff_summary && (
                <div className="section-card v2-case-explorer__diff-summary">
                  <h3><IconChart /> Diff Summary</h3>
                  <p>{loadedRecord.diff.diff_summary}</p>
                  {loadedRecord.diff.dangerousness_shift && (
                    <p style={{ marginTop: "0.4rem" }}>
                      <strong>Dangerousness shift:</strong>{" "}
                      <ShiftBadge direction={resolveShiftDirection(loadedRecord)} />
                    </p>
                  )}
                </div>
              )}

              {/* ---- Action buttons ---- */}
              <div className="btn-row">
                <button type="button" className="btn btn-secondary btn-sm" onClick={handleCopyJson}>Copy JSON</button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={handleCopySummary}>Copy Summary</button>
              </div>
              {copyFeedback && (
                <p className="v2-case-explorer__copy-feedback muted" role="status">{copyFeedback}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
