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

/**
 * Line-by-line diff: splits both texts by newline, aligns lines by their
 * field label (text before the colon), and marks a line as changed only
 * when the *value* portion differs between base and variant.
 */
function highlightDiffs(
  baseText: string,
  variantText: string,
): {
  baseParts: Array<{ text: string; changed: boolean }>;
  variantParts: Array<{ text: string; changed: boolean }>;
} {
  const baseLines = baseText.split("\n").map((l) => l.trim()).filter(Boolean);
  const variantLines = variantText.split("\n").map((l) => l.trim()).filter(Boolean);

  // Build a map: fieldLabel → value for the variant
  const variantByLabel = new Map<string, string>();
  for (const line of variantLines) {
    const colonIdx = line.indexOf(":");
    if (colonIdx > 0) {
      variantByLabel.set(line.slice(0, colonIdx).trim(), line.slice(colonIdx + 1).trim());
    } else {
      variantByLabel.set(line, line);
    }
  }
  const baseByLabel = new Map<string, string>();
  for (const line of baseLines) {
    const colonIdx = line.indexOf(":");
    if (colonIdx > 0) {
      baseByLabel.set(line.slice(0, colonIdx).trim(), line.slice(colonIdx + 1).trim());
    } else {
      baseByLabel.set(line, line);
    }
  }

  const baseParts = baseLines.map((line) => {
    const colonIdx = line.indexOf(":");
    const label = colonIdx > 0 ? line.slice(0, colonIdx).trim() : line;
    const baseVal = colonIdx > 0 ? line.slice(colonIdx + 1).trim() : line;
    const variantVal = variantByLabel.get(label);
    return { text: line, changed: variantVal !== undefined && variantVal !== baseVal };
  });

  const variantParts = variantLines.map((line) => {
    const colonIdx = line.indexOf(":");
    const label = colonIdx > 0 ? line.slice(0, colonIdx).trim() : line;
    const varVal = colonIdx > 0 ? line.slice(colonIdx + 1).trim() : line;
    const baseVal = baseByLabel.get(label);
    return { text: line, changed: baseVal !== undefined && baseVal !== varVal };
  });

  return { baseParts, variantParts };
}

function DiffText({ parts }: { parts: Array<{ text: string; changed: boolean }> }) {
  return (
    <div className="v2-case-explorer__field-text">
      {parts.map((p, i) => (
        <div
          key={i}
          className={p.changed ? "v2-diff-line v2-diff-highlight" : "v2-diff-line"}
        >
          {p.text}
        </div>
      ))}
    </div>
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
  // Collapsible sections
  const [sectionOpen, setSectionOpen] = useState<Record<string, boolean>>({
    input: true,
    output: true,
    reasoning: false,
    crossPrompt: false,
    diff: false,
  });
  const toggleSection = (key: string) => setSectionOpen((s) => ({ ...s, [key]: !s[key] }));

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
            const priorityColor = entry.is_flagged
              ? (entry.review_priority === "high" ? "var(--v2-danger, #dc2626)" : "var(--v2-warning, #d97706)")
              : undefined;
            return (
              <button
                key={entry.review_record_id}
                type="button"
                className={`v2-case-explorer__card${isSelected ? " v2-case-explorer__card--selected" : ""}`}
                style={priorityColor ? { borderLeft: `3px solid ${priorityColor}` } : undefined}
                onClick={() => handleSelectEntry(entry)}
                aria-pressed={isSelected}
              >
                <div className="v2-case-explorer__card-top">
                  <span className="v2-case-explorer__case-id">{entry.base_case_id}</span>
                  <span style={{ display: "flex", gap: "0.3rem", alignItems: "center" }}>
                    {entry.is_flagged && (
                      <span style={{
                        display: "inline-block", padding: "0.1rem 0.4rem", borderRadius: "999px",
                        fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.03em",
                        background: entry.review_priority === "high" ? "hsl(0 75% 92%)" : "hsl(35 80% 92%)",
                        color: entry.review_priority === "high" ? "hsl(0 70% 40%)" : "hsl(35 70% 35%)",
                      }}>
                        {entry.review_priority === "high" ? "⚠ HIGH" : "⚡ FLAGGED"}
                      </span>
                    )}
                    {!entry.is_flagged && (
                      <span style={{
                        display: "inline-block", padding: "0.1rem 0.4rem", borderRadius: "999px",
                        fontSize: "0.65rem", fontWeight: 600, background: "hsl(220 15% 94%)", color: "hsl(220 10% 60%)",
                      }}>OK</span>
                    )}
                  </span>
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

              {/* ---- SECTION 1: Input Case Comparison (Collapsible) ---- */}
              <div className="section-card" style={{ marginBottom: "1.25rem" }}>
                <button type="button" onClick={() => toggleSection('input')} style={{ all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%' }}>
                  <span style={{ fontSize: '0.8rem', transition: 'transform 0.2s', transform: sectionOpen.input ? 'rotate(90deg)' : 'rotate(0)' }}>▶</span>
                  <h3 style={{ margin: 0 }}><IconDocument /> Input Case — Neutral vs Variant</h3>
                </button>
                {sectionOpen.input && (
                  <>
                    <p className="muted" style={{ marginBottom: "0.75rem", marginTop: "0.5rem" }}>
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
                        <div className="v2-case-explorer__input-text" dir="auto" style={{ whiteSpace: "pre-wrap" }}>
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
                        <div className="v2-case-explorer__input-text" dir="auto" style={{ whiteSpace: "pre-wrap" }}>
                          {inputDiff ? (
                            <DiffText parts={inputDiff.variantParts} />
                          ) : (
                            <p className="v2-case-explorer__field-text">{variantCaseText ?? "N/A"}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </>
                )}
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

              {/* ---- SECTION 2: Model Output Comparison (Collapsible, default open) ---- */}
              <div className="section-card" style={{ marginBottom: "1.25rem" }}>
                <button type="button" onClick={() => toggleSection('output')} style={{ all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%' }}>
                  <span style={{ fontSize: '0.8rem', transition: 'transform 0.2s', transform: sectionOpen.output ? 'rotate(90deg)' : 'rotate(0)' }}>▶</span>
                  <h3 style={{ margin: 0 }}><IconScale /> Model Output Comparison</h3>
                </button>
                {sectionOpen.output && (
                  <>
                    <p className="muted" style={{ marginBottom: "0.75rem", marginTop: "0.5rem", fontSize: "var(--v2-fs-sm, 0.85rem)" }}>
                      All fields the model produced. Differences between neutral and variant are highlighted.
                    </p>
                    <div className="v2-output-table-wrap">
                      <table className="v2-output-table">
                        <thead>
                          <tr>
                            <th>Field</th>
                            <th>Neutral Baseline</th>
                            <th>Variant: {variantLabel}</th>
                            <th className="v2-output-table__status">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(() => {
                            const n = loadedRecord.neutral_output ?? {} as Record<string, unknown>;
                            const v = loadedRecord.variant_output ?? {} as Record<string, unknown>;
                            const fields: Array<{ label: string; key: string; format?: (val: unknown) => string }> = [
                              { label: "Recommendation", key: "recommendation", format: (x) => String(x ?? "").replace(/_/g, " ") },
                              { label: "Public Safety Risk", key: "public_safety_risk" },
                              { label: "Obstruction Risk", key: "obstruction_risk" },
                              { label: "Recidivism Risk", key: "recidivism_risk" },
                            ];
                            return fields.map(({ label, key, format }) => {
                              const nVal = (n as Record<string, unknown>)[key];
                              const vVal = (v as Record<string, unknown>)[key];
                              const fmt = format ?? ((x: unknown) => String(x ?? "N/A"));
                              const changed = String(nVal) !== String(vVal);
                              return (
                                <tr key={key} className={changed ? "v2-output-table__row--changed" : ""}>
                                  <td className="v2-output-table__field">{label}</td>
                                  <td className="v2-output-table__val">{fmt(nVal)}</td>
                                  <td className={`v2-output-table__val${changed ? " v2-output-table__val--diff" : ""}`}>{fmt(vVal)}</td>
                                  <td className="v2-output-table__status">{changed ? <span className="v2-output-badge v2-output-badge--changed">Changed</span> : <span className="v2-output-badge v2-output-badge--same">Same</span>}</td>
                                </tr>
                              );
                            });
                          })()}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>

              {/* ---- SECTION 3: Model Reasoning (Collapsible, default closed) ---- */}
              <div className="section-card" style={{ marginBottom: "1.25rem" }}>
                <button type="button" onClick={() => toggleSection('reasoning')} style={{ all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%' }}>
                  <span style={{ fontSize: '0.8rem', transition: 'transform 0.2s', transform: sectionOpen.reasoning ? 'rotate(90deg)' : 'rotate(0)' }}>▶</span>
                  <h3 style={{ margin: 0 }}><IconRobot /> Model Reasoning</h3>
                </button>
                {sectionOpen.reasoning && (
                  <div style={{ marginTop: "0.75rem" }}>
                    <p className="muted" style={{ marginBottom: "0.75rem", fontSize: "var(--v2-fs-sm)" }}>
                      The model&apos;s legal-style reasoning for each version. Compare how the justification changes when demographic details differ.
                    </p>
                    <div className="v2-case-explorer__comparison">
                      {/* Neutral reasoning */}
                      <div className="v2-case-explorer__column">
                        <h4 className="v2-case-explorer__column-title">Neutral Baseline</h4>
                        <div className="v2-case-explorer__reasoning-scroll" dir="auto" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-secondary)", background: "var(--v2-bg-surface, hsl(220 15% 97%))", padding: "0.75rem", borderRadius: "6px", border: "1px solid var(--v2-border-subtle, hsl(220 15% 94%))" }}>
                          {loadedRecord.neutral_output?.reasoning_text ?? "N/A"}
                        </div>
                      </div>
                      {/* Variant reasoning */}
                      <div className="v2-case-explorer__column">
                        <h4 className="v2-case-explorer__column-title">Variant: {variantLabel}</h4>
                        <div className="v2-case-explorer__reasoning-scroll" dir="auto" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: "var(--v2-fs-sm)", color: "var(--v2-text-secondary)", background: "var(--v2-bg-surface, hsl(220 15% 97%))", padding: "0.75rem", borderRadius: "6px", border: "1px solid var(--v2-border-subtle, hsl(220 15% 94%))" }}>
                          {loadedRecord.variant_output?.reasoning_text ?? "N/A"}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* ---- SECTION 4: Cross-prompt comparison (Collapsible) ---- */}
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
