"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/Card";
import { Callout } from "@/components/Callout";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/detention/PageHeader";
import { CaseTextDiff } from "@/components/detention/CaseTextDiff";
import { CaseReviewFilterBar } from "@/components/detention/CaseReviewFilterBar";
import { CrossPromptPanel } from "@/components/detention/CrossPromptPanel";
import { ValidityContextPanel } from "@/components/detention/ValidityContextPanel";
import { VirtualReviewQueue } from "@/components/detention/VirtualReviewQueue";
import { computeReviewProgress, ReviewProgressPanel } from "@/components/detention/ReviewProgressPanel";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import {
  caseReviewKey,
  DEFAULT_CASE_REVIEW_FILTERS,
  dirForText,
  displayWhyFlagged,
  filterCaseReviewRecords,
  filterCaseReviewIndex,
  formatOutputValue,
  outputComparisonRowsForSchema,
  isMinimalDetentionSchema,
  isAddressProxyVariant,
  outputDiffIndicator,
  dangerousnessPairLabel,
  analysisBucketLabel,
  type CaseReviewFilters,
  type CaseReviewIndexEntry,
  type CaseReviewRecord,
} from "@/lib/detentionCaseReview";
import { buildPacketSummaryRows, packetSummaryStats } from "@/lib/detentionPacketSummary";
import {
  EMPTY_CHECKLIST,
  exportReviewStateBackup,
  exportReviewStateEncryptedBackup,
  importReviewStateBackup,
  importReviewStateEncryptedBackup,
  REVIEW_DECISION_OPTIONS,
  checklistItemsForSchema,
  type ReviewRecord,
} from "@/lib/detentionReview";
import { str, formatCount } from "@/lib/format";
import { formatVariantLabel } from "@/lib/v2/dataUtils";

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  return (
    <button type="button" className="btn btn-ghost btn-sm" onClick={() => void navigator.clipboard.writeText(text)}>
      {label}
    </button>
  );
}

function StatusChip({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "warn" | "ok" }) {
  return <span className={`review-chip review-chip-${tone}`}>{children}</span>;
}

function StructuredFacts({ facts }: { facts: Record<string, unknown> | undefined }) {
  const entries = Object.entries(facts ?? {}).filter(([, v]) => {
    if (v === null || v === undefined) return false;
    if (typeof v === "string" && !v.trim()) return false;
    if (Array.isArray(v) && !v.length) return false;
    return true;
  });
  if (!entries.length) return <p className="muted">No structured facts parsed.</p>;
  return (
    <dl className="meta-dl meta-dl-stack compact-facts">
      {entries.map(([k, v]) => (
        <div key={k}>
          <dt>{formatVariantLabel(k)}</dt>
          <dd dir={dirForText(String(v))}>{Array.isArray(v) ? v.join("; ") : String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

function PromptCollapsible({ title, prompt, status }: { title: string; prompt: string; status?: string }) {
  const [open, setOpen] = useState(false);
  if (!prompt) return null;
  return (
    <details className="prompt-collapsible" open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary>{title}{status ? ` · ${formatVariantLabel(status)}` : ""}</summary>
      <div className="prompt-block">
        <CopyButton text={prompt} />
        <pre dir={dirForText(prompt)}>{prompt}</pre>
      </div>
    </details>
  );
}

function CaseFactsPanel({ record }: { record: CaseReviewRecord }) {
  const preserved = record.variant_case.legally_relevant_facts_preserved;
  const preservedLabel = preserved === true ? "Yes" : preserved === false ? "No" : "Needs review";

  return (
    <details className="review-section case-inputs-collapsible">
      <summary className="case-inputs-summary">
        <span>Case inputs</span>
        <span className="muted">Full neutral vs variant text and prompts</span>
      </summary>
      {(record.variant_case.what_changed_from_base ?? []).length ? (
        <Callout title="What changed?" variant="info">
          <ul>
            {record.variant_case.what_changed_from_base!.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p><strong>Legally relevant facts preserved:</strong> {preservedLabel}</p>
          {record.variant_case.facts_preservation_notes ? <p className="muted">{record.variant_case.facts_preservation_notes}</p> : null}
        </Callout>
      ) : null}
      <CaseTextDiff
        baseText={record.base_case.full_case_text || ""}
        variantText={record.variant_case.full_case_text || ""}
      />
      <div className="side-by-side-panels">
        <Card title="Neutral / base case">
          <p className="muted panel-sub">{record.base_case_id}</p>
          <StructuredFacts facts={record.base_case.structured_facts as Record<string, unknown>} />
          <div className="legal-text-block" dir={dirForText(record.base_case.full_case_text || "")}>
            <CopyButton text={record.base_case.full_case_text || ""} />
            <pre>{record.base_case.full_case_text || "—"}</pre>
          </div>
          <PromptCollapsible
            title="View full prompt sent to model (neutral)"
            prompt={record.base_case.full_prompt_sent_to_model || ""}
            status={record.base_case.prompt_reconstruction_status}
          />
        </Card>
        <Card title="Variant case">
          <p className="muted panel-sub">{record.variant_id} · {formatVariantLabel(record.protected_attribute_tested)}</p>
          <StructuredFacts facts={record.variant_case.structured_facts as Record<string, unknown>} />
          <div className="legal-text-block" dir={dirForText(record.variant_case.full_case_text || "")}>
            <CopyButton text={record.variant_case.full_case_text || ""} />
            <pre>{record.variant_case.full_case_text || "—"}</pre>
          </div>
          <PromptCollapsible
            title="View full prompt sent to model (variant)"
            prompt={record.variant_case.full_prompt_sent_to_model || ""}
            status={record.variant_case.prompt_reconstruction_status}
          />
        </Card>
      </div>
    </details>
  );
}

function OutputComparisonPanel({ record }: { record: CaseReviewRecord }) {
  const rows = outputComparisonRowsForSchema(record.schema_version);
  return (
    <section className="review-section">
      <h3>Structured outputs</h3>
      {isMinimalDetentionSchema(record.schema_version) ? (
        <p className="muted">Minimal schema — case summary, dangerousness level, and reasoning only.</p>
      ) : null}
      <div className="side-by-side-table-wrap">
        <table className="side-by-side-table output-compare-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Neutral output</th>
              <th>Variant output</th>
              <th>Signal</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ key, label, list }) => {
              const ind = outputDiffIndicator(key, record.neutral_output, record.variant_output, record.diff);
              return (
                <tr key={key} className={ind.changed ? `row-${ind.tone}` : ""}>
                  <td>{label}</td>
                  <td dir={dirForText(formatOutputValue(record.neutral_output[key], list))}>{formatOutputValue(record.neutral_output[key], list)}</td>
                  <td dir={dirForText(formatOutputValue(record.variant_output[key], list))}>{formatOutputValue(record.variant_output[key], list)}</td>
                  <td><span className={`diff-signal diff-${ind.tone}`}>{ind.signal}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DiffSummaryPanel({ record }: { record: CaseReviewRecord }) {
  const d = record.diff;
  const minimal = isMinimalDetentionSchema(record.schema_version);
  const lines = [
    d.dangerousness_shift ? `Dangerousness: ${d.dangerousness_shift}` : null,
    !minimal && d.obstruction_risk_shift ? `Obstruction risk: ${d.obstruction_risk_shift}` : null,
    !minimal && d.recommended_action_shift ? `Recommended action: ${d.recommended_action_shift}` : null,
    !minimal && d.duration_shift ? `Duration: ${d.duration_shift}` : null,
    !minimal && d.alternatives_omitted ? "Alternatives considered: present → omitted" : null,
    !minimal && d.procedural_safeguards_omitted ? "Procedural safeguards: present → omitted" : null,
    !minimal && d.credibility_framing_shift ? `Credibility framing: ${d.credibility_framing_shift}` : null,
    isAddressProxyVariant(record) ? "Address-proxy variant — analyze separately from strict demographic rates." : null,
  ].filter(Boolean);

  return (
    <section className="review-section audit-signal-panel">
      <h3>Audit signal</h3>
      <div className="comparison-hero">
        <div className="comparison-hero-stat">
          <span className="muted">Dangerousness (neutral → variant)</span>
          <strong className={record.is_flagged ? "danger-shift" : ""}>{dangerousnessPairLabel(record)}</strong>
        </div>
        {analysisBucketLabel(record.analysis_bucket) ? (
          <div className="comparison-hero-stat">
            <span className="muted">Analysis bucket</span>
            <strong>{analysisBucketLabel(record.analysis_bucket)}</strong>
          </div>
        ) : null}
        <div className="comparison-hero-stat">
          <span className="muted">Prompt mode</span>
          <strong>{formatVariantLabel(record.prompt_mode)}</strong>
        </div>
      </div>
      {!record.is_flagged ? (
        <p className="muted">No primary audit flag — dangerousness level unchanged under current flagging rule.</p>
      ) : (
        <Callout title="Why flagged" variant="caution">
          <p>{displayWhyFlagged(record)}</p>
          <p className="muted">{record.review_guidance.plain_language_summary}</p>
        </Callout>
      )}
      {record.variant_case.facts_preservation_notes ? (
        <Callout title="Validity / fact preservation" variant="info">
          <p>{record.variant_case.facts_preservation_notes}</p>
          {record.use_for_strict_bias_rates === false ? (
            <p className="muted">Excluded from strict demographic flagged rates — review in the address-proxy bucket if applicable.</p>
          ) : null}
        </Callout>
      ) : null}
      {record.diff.diff_summary ? <p className="muted">{record.diff.diff_summary}</p> : null}
      {lines.length ? (
        <ul className="diff-summary-list">
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      {record.review_guidance.legal_review_questions.length ? (
        <div className="legal-review-questions">
          <h4>Legal review questions</h4>
          <ul className="compact-list">
            {record.review_guidance.legal_review_questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function ExpertChecklistPanel({
  review,
  schemaVersion,
  onUpdate,
}: {
  review: ReviewRecord | undefined;
  schemaVersion?: string | null;
  onUpdate: (patch: Partial<ReviewRecord>) => void;
}) {
  const checklist = { ...EMPTY_CHECKLIST, ...(review?.checklist ?? {}) };
  const items = checklistItemsForSchema(schemaVersion);

  const updateChecklist = (key: keyof typeof checklist, value: boolean | null) => {
    onUpdate({ checklist: { ...checklist, [key]: value } });
  };

  return (
    <section className="review-section">
      <h3>Expert checklist</h3>
      <p className="muted local-storage-note">Stored in this browser only unless you export review state.</p>
      <ul className="checklist-list">
        {items.map((item) => (
          <li key={item.key}>
            <span>{item.label}</span>
            <div className="checklist-btns">
              <button type="button" className={`btn btn-sm ${checklist[item.key] === true ? "btn-primary" : "btn-ghost"}`} onClick={() => updateChecklist(item.key, true)}>Yes</button>
              <button type="button" className={`btn btn-sm ${checklist[item.key] === false ? "btn-primary" : "btn-ghost"}`} onClick={() => updateChecklist(item.key, false)}>No</button>
              <button type="button" className={`btn btn-sm ${checklist[item.key] === null ? "btn-secondary" : "btn-ghost"}`} onClick={() => updateChecklist(item.key, null)}>—</button>
            </div>
          </li>
        ))}
      </ul>
      <label className="field-label">Review decision
        <select
          value={review?.decision ?? "not_reviewed"}
          onChange={(e) => onUpdate({ decision: e.target.value as ReviewRecord["decision"], reviewed: e.target.value !== "not_reviewed", reviewedAt: new Date().toISOString() })}
        >
          {REVIEW_DECISION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </label>
      <label className="field-label">Local notes
        <textarea
          rows={5}
          value={review?.notes ?? ""}
          onChange={(e) => onUpdate({ notes: e.target.value })}
          placeholder="Legal expert notes…"
        />
      </label>
    </section>
  );
}

function ReasoningPanel({ record }: { record: CaseReviewRecord }) {
  const n = str(record.neutral_output.reasoning_text);
  const v = str(record.variant_output.reasoning_text);
  if (!n && !v) return null;
  return (
    <section className="review-section">
      <h3>Reasoning comparison</h3>
      <p className="muted">Side-by-side diff of model reasoning text — primary material for legal review under the minimal schema.</p>
      <CaseTextDiff baseText={n} variantText={v} />
    </section>
  );
}

function PacketPanel({
  count,
  packetRecords,
  reviewState,
  onSelectRecord,
  onRemove,
  onExportJson,
  onExportCsv,
  onCopyMd,
  onExportPdf,
  onBackupState,
  onImportState,
  onOpenSummary,
  onEncryptedBackup,
  onEncryptedImport,
}: {
  count: number;
  packetRecords: CaseReviewRecord[];
  reviewState: Record<string, ReviewRecord>;
  onSelectRecord?: (id: string) => void;
  onRemove: (id: string) => void;
  onExportJson: () => void;
  onExportCsv: () => void;
  onCopyMd: () => void;
  onExportPdf: () => void;
  onBackupState: () => void;
  onImportState: (file: File) => void;
  onOpenSummary?: () => void;
  onEncryptedBackup?: () => void;
  onEncryptedImport?: (file: File) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const encFileRef = useRef<HTMLInputElement>(null);
  const summaryRows = buildPacketSummaryRows(packetRecords, reviewState);
  const stats = packetSummaryStats(packetRecords);

  return (
    <Card title="Review packet">
      <p className="muted">{count} case{count === 1 ? "" : "s"} in packet</p>
      {count ? (
        <p className="muted packet-summary-stats">
          {stats.flagged} flagged · {stats.high} high priority
          {stats.addressProxy ? ` · ${stats.addressProxy} address-proxy` : ""}
        </p>
      ) : null}
      {summaryRows.length ? (
        <div className="packet-summary-table-wrap">
          <table className="data-table packet-summary-table">
            <thead>
              <tr>
                <th>Case</th>
                <th>Dangerousness</th>
                <th>Bucket</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {summaryRows.map((row) => (
                <tr key={row.id}>
                  <td>
                    {onSelectRecord ? (
                      <button type="button" className="link-btn" onClick={() => onSelectRecord(row.id)}>
                        {row.baseCaseId}
                      </button>
                    ) : (
                      row.baseCaseId
                    )}
                    <span className="muted"> · {row.variantLabel}</span>
                  </td>
                  <td>{row.dangerousness}</td>
                  <td>{row.bucket}</td>
                  <td>{formatVariantLabel(row.decision)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {packetRecords.length ? (
        <ul className="packet-list compact">
          {packetRecords.map((r) => (
            <li key={caseReviewKey(r)}>
              <span>{r.base_case_id} · {r.variant_case.variant_label}</span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => onRemove(caseReviewKey(r))}>Remove</button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="btn-row">
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onOpenSummary}>
          Packet summary page
        </button>
        {onEncryptedBackup ? (
          <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onEncryptedBackup}>
            Encrypted backup
          </button>
        ) : null}
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onExportJson}>Export JSON</button>
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onExportCsv}>Export CSV</button>
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onCopyMd}>Copy Markdown</button>
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onExportPdf}>Export PDF</button>
      </div>
      <div className="btn-row">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onBackupState}>Backup review state</button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => fileRef.current?.click()}>Import review state</button>
        {onEncryptedImport ? (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => encFileRef.current?.click()}>Import encrypted</button>
        ) : null}
        <input ref={fileRef} type="file" accept="application/json" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) onImportState(f); e.target.value = ""; }} />
        <input ref={encFileRef} type="file" accept="application/json" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f && onEncryptedImport) void onEncryptedImport(f); e.target.value = ""; }} />
      </div>
    </Card>
  );
}

export function DetentionCaseReviewWorkspace({
  bundle,
  reviewState,
  packetIds,
  selectedId,
  onSelectReviewId,
  onEnsureRecordLoaded,
  onPrefetchRecords,
  onUpdateReview,
  onTogglePacket,
  onRemoveFromPacket,
  onExportPacket,
  onImportReviewState,
  focusMode,
  onFocusModeChange,
  initialFilters,
  onFiltersChange,
  loading,
  loadStatus,
  detailLoadingId,
  activePresetId,
  onApplyFilterPreset,
}: {
  bundle: DetentionDashboardBundle;
  reviewState: Record<string, ReviewRecord>;
  packetIds: string[];
  selectedId: string | null;
  onSelectReviewId: (reviewId: string) => void;
  onEnsureRecordLoaded: (reviewId: string) => void;
  onPrefetchRecords?: (reviewIds: string[]) => void;
  onUpdateReview: (key: string, patch: Partial<ReviewRecord>) => void;
  onTogglePacket: (record: CaseReviewRecord) => void;
  onRemoveFromPacket: (id: string) => void;
  onExportPacket: (format: "json" | "csv" | "md" | "pdf") => void;
  onImportReviewState: (file: File) => void;
  focusMode: boolean;
  onFocusModeChange: (v: boolean) => void;
  initialFilters?: Partial<CaseReviewFilters>;
  onFiltersChange?: (filters: CaseReviewFilters) => void;
  loading?: boolean;
  loadStatus?: string;
  detailLoadingId?: string | null;
  activePresetId?: string | null;
  onApplyFilterPreset?: (presetId: string) => void;
}) {
  const [filters, setFilters] = useState<CaseReviewFilters>({ ...DEFAULT_CASE_REVIEW_FILTERS, ...initialFilters, focusMode });
  const [mobilePane, setMobilePane] = useState<"queue" | "detail" | "checklist">("queue");
  const [packetSummaryOpen, setPacketSummaryOpen] = useState(false);
  const queueRef = useRef<HTMLDivElement>(null);
  const mainPanelRef = useRef<HTMLDivElement>(null);

  const handleEncryptedBackup = useCallback(async () => {
    const pass = window.prompt("Passphrase for encrypted backup (8+ characters)");
    if (!pass || pass.length < 8) return;
    await exportReviewStateEncryptedBackup(reviewState, packetIds, pass);
  }, [reviewState, packetIds]);

  const handleEncryptedImport = useCallback(
    async (file: File) => {
      const pass = window.prompt("Passphrase for encrypted backup");
      if (!pass) return;
      try {
        const snap = await importReviewStateEncryptedBackup(file, pass);
        const blob = new Blob(
          [JSON.stringify({ review_state: snap.reviewState, packet_ids: snap.packetIds })],
          { type: "application/json" },
        );
        await onImportReviewState(new File([blob], "decrypted_review_backup.json", { type: "application/json" }));
      } catch (err) {
        window.alert(err instanceof Error ? err.message : "Could not decrypt backup");
      }
    },
    [onImportReviewState],
  );

  const packetPanelExtras = {
    onEncryptedBackup: handleEncryptedBackup,
    onEncryptedImport: handleEncryptedImport,
  };

  const patchFilters = (patch: Partial<CaseReviewFilters> | ((prev: CaseReviewFilters) => CaseReviewFilters)) => {
    setFilters((prev) => {
      const next = typeof patch === "function" ? patch(prev) : { ...prev, ...patch };
      onFiltersChange?.({ ...next, focusMode });
      return next;
    });
  };

  useEffect(() => {
    if (initialFilters && Object.keys(initialFilters).length) {
      setFilters((prev) => ({ ...prev, ...initialFilters, focusMode }));
    }
  }, [initialFilters, focusMode]);

  const records = bundle.caseReviewRecords;
  const recordsById = useMemo(() => {
    const map: Record<string, CaseReviewRecord> = {};
    for (const r of records) map[caseReviewKey(r)] = r;
    return map;
  }, [records]);
  const schemaVersion =
    str(bundle.manifest.schema_version) ||
    str(bundle.fullMetricSummary[0]?.schema_version) ||
    str(bundle.overview.schema_version) ||
    records[0]?.schema_version;
  const minimalSchema = isMinimalDetentionSchema(schemaVersion);
  const effectiveFilters = useMemo(() => ({ ...filters, focusMode }), [filters, focusMode]);

  const filteredIndex = useMemo(
    () => filterCaseReviewIndex(bundle.caseReviewIndex, effectiveFilters, reviewState),
    [bundle.caseReviewIndex, effectiveFilters, reviewState],
  );

  const selectedEntry = useMemo(() => {
    if (selectedId) {
      const inFiltered = filteredIndex.find((e) => e.review_record_id === selectedId);
      if (inFiltered) return inFiltered;
      const inAll = bundle.caseReviewIndex.find((e) => e.review_record_id === selectedId);
      if (inAll) return inAll;
    }
    return filteredIndex[0] ?? null;
  }, [filteredIndex, selectedId, bundle.caseReviewIndex]);

  const selected = selectedEntry ? recordsById[selectedEntry.review_record_id] ?? null : null;

  const handleSelectEntry = useCallback(
    (entry: CaseReviewIndexEntry) => {
      onSelectReviewId(entry.review_record_id);
      onEnsureRecordLoaded(entry.review_record_id);
      setMobilePane("detail");
    },
    [onSelectReviewId, onEnsureRecordLoaded],
  );

  useEffect(() => {
    if (!selectedEntry) return;
    onEnsureRecordLoaded(selectedEntry.review_record_id);
    if (selectedId && selectedId !== selectedEntry.review_record_id) {
      onSelectReviewId(selectedEntry.review_record_id);
    }
  }, [selectedEntry, selectedId, onSelectReviewId, onEnsureRecordLoaded]);

  useEffect(() => {
    if (!selectedEntry || !onPrefetchRecords || !filteredIndex.length) return;
    const idx = filteredIndex.findIndex((e) => e.review_record_id === selectedEntry.review_record_id);
    if (idx < 0) return;
    const ids: string[] = [];
    for (let offset = 1; offset <= 3; offset += 1) {
      const next = filteredIndex[idx + offset];
      const prev = filteredIndex[idx - offset];
      if (next) ids.push(next.review_record_id);
      if (prev) ids.push(prev.review_record_id);
    }
    if (ids.length) onPrefetchRecords(ids);
  }, [selectedEntry, filteredIndex, onPrefetchRecords]);

  const progress = useMemo(
    () =>
      computeReviewProgress(
        records.length ? records : [],
        reviewState,
        packetIds,
        bundle.caseReviewIndex.filter((e) => e.is_flagged).length,
      ),
    [records, reviewState, packetIds, bundle.caseReviewIndex],
  );

  const packetRecords = useMemo(
    () => records.filter((r) => packetIds.includes(caseReviewKey(r))),
    [records, packetIds],
  );

  useEffect(() => {
    if (selectedId && selectedEntry) setMobilePane("detail");
  }, [selectedId, selectedEntry]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!filteredIndex.length || e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      const idx = selectedEntry
        ? filteredIndex.findIndex((e) => e.review_record_id === selectedEntry.review_record_id)
        : -1;
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        const next = filteredIndex[Math.min(idx + 1, filteredIndex.length - 1)];
        if (next) handleSelectEntry(next);
      }
      if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        const prev = filteredIndex[Math.max(idx - 1, 0)];
        if (prev) handleSelectEntry(prev);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [filteredIndex, selectedEntry, handleSelectEntry]);

  const filterOptions = useMemo(() => ({
    variants: [...new Set(bundle.caseReviewIndex.map((e) => e.variant_type))].sort(),
    bases: [...new Set(bundle.caseReviewIndex.map((e) => e.base_case_id))].sort(),
    protected: [...new Set(bundle.caseReviewIndex.map((e) => e.protected_attribute_tested).filter(Boolean))].sort(),
    issues: [...new Set(bundle.caseReviewIndex.flatMap((e) => e.issue_types))].sort(),
    promptModes: [...new Set(bundle.caseReviewIndex.map((e) => e.prompt_mode).filter(Boolean))].sort(),
  }), [bundle.caseReviewIndex]);

  if (!bundle.caseReviewIndex.length && !bundle.caseReviewIndexCount) {
    return (
      <EmptyState
        title="Case review records not available"
        description="This file is required for the full side-by-side expert review workspace."
        command="python -m benchassist.detention_case_review_export --run-dir results/gemini/detention_expanded_full --all-prompt-modes --output web_dashboard/public/data"
      />
    );
  }

  return (
    <div className="case-review-workspace">
      <PageHeader
        title="Case Review Workspace"
        subtitle="Compare neutral vs variant outputs. Primary audit signal: dangerousness level change."
        note={bundle.caseReviewMeta?.prompt_reconstruction_note}
      />

      {loading && bundle.caseReviewLoaded ? (
        <div className="inline-load-banner" role="status" aria-live="polite">
          {loadStatus || "Loading remaining review records in background…"}
        </div>
      ) : null}

      <div className="review-status-chips">
        <StatusChip>{formatVariantLabel(bundle.dataStatus)}</StatusChip>
        <StatusChip>Synthetic comparison</StatusChip>
        <StatusChip tone="ok">Address-proxy bucket separate</StatusChip>
        {selected ? <StatusChip tone={selected.review_priority === "high" ? "warn" : "default"}>Priority: {selected.review_priority}</StatusChip> : null}
        <label className="focus-mode-toggle">
          <input type="checkbox" checked={focusMode} onChange={(e) => onFocusModeChange(e.target.checked)} />
          Focus review mode
        </label>
      </div>

      <ReviewProgressPanel progress={progress} />

      <div className="case-review-mobile-tabs" role="tablist" aria-label="Case review panels">
        {(["queue", "detail", "checklist"] as const).map((pane) => (
          <button
            key={pane}
            type="button"
            role="tab"
            aria-selected={mobilePane === pane}
            className={`case-review-mobile-tab ${mobilePane === pane ? "active" : ""}`}
            onClick={() => {
              setMobilePane(pane);
              if (pane === "detail") mainPanelRef.current?.focus();
            }}
          >
            {pane === "queue" ? "Queue" : pane === "detail" ? "Comparison" : "Checklist"}
          </button>
        ))}
      </div>

      {packetSummaryOpen ? (
        <section className="packet-summary-page section-card">
          <PageHeader
            title="Review packet summary"
            subtitle="Counsel readout — dangerousness pairs and local review decisions."
          />
          <PacketPanel
            count={packetIds.length}
            packetRecords={packetRecords}
            reviewState={reviewState}
            onSelectRecord={(id) => {
              setPacketSummaryOpen(false);
              onSelectReviewId(id);
            }}
            onRemove={onRemoveFromPacket}
            onExportJson={() => onExportPacket("json")}
            onExportCsv={() => onExportPacket("csv")}
            onCopyMd={() => onExportPacket("md")}
            onExportPdf={() => onExportPacket("pdf")}
            onBackupState={() => exportReviewStateBackup(reviewState, packetIds)}
            onImportState={onImportReviewState}
            {...packetPanelExtras}
          />
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPacketSummaryOpen(false)}>
            Back to case review
          </button>
        </section>
      ) : (
      <div className={`case-review-workspace-grid mobile-pane-${mobilePane}`}>
        <aside className="review-queue-panel">
          <Card title={`Review queue (${filteredIndex.length})`}>
            <input
              type="search"
              placeholder="Search cases…"
              value={filters.search}
              onChange={(e) => patchFilters({ search: e.target.value })}
              className="filter-search"
            />
            <CaseReviewFilterBar
              filters={filters}
              filterOptions={filterOptions}
              minimalSchema={minimalSchema}
              onChange={(patch) => patchFilters(patch)}
              activePresetId={activePresetId}
              onApplyPreset={onApplyFilterPreset}
            />
            <p className="muted keyboard-hint">Tip: use ↑/↓ or j/k to move between cases in the queue.</p>
            <VirtualReviewQueue
              entries={filteredIndex}
              recordsById={recordsById}
              selectedId={selectedEntry?.review_record_id ?? null}
              packetIds={packetIds}
              onSelect={handleSelectEntry}
              listRef={queueRef}
            />
          </Card>
        </aside>

        <div className="review-main-panel" ref={mainPanelRef} tabIndex={-1}>
          {selectedEntry && !selected ? (
            <div className="loading-screen loading-screen-inline" aria-live="polite">
              <p>{detailLoadingId === selectedEntry.review_record_id ? "Loading case comparison…" : "Preparing case comparison…"}</p>
            </div>
          ) : selected ? (
            <>
              <div className="sticky-comparison-header">
                <h2 dir={dirForText(selected.base_case_title || selected.base_case_id)}>{selected.base_case_title || selected.base_case_id}</h2>
                <p className="muted">
                  {selected.variant_case.variant_label || formatVariantLabel(selected.variant_type)} · {formatVariantLabel(selected.prompt_mode)}
                  {analysisBucketLabel(selected.analysis_bucket) ? ` · ${analysisBucketLabel(selected.analysis_bucket)}` : ""}
                </p>
                <div className="btn-row">
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => onTogglePacket(selected)}>
                    {packetIds.includes(caseReviewKey(selected)) ? "Remove from packet" : "Add to packet"}
                  </button>
                  <CopyButton text={displayWhyFlagged(selected)} label="Copy flag reason" />
                </div>
              </div>
              <DiffSummaryPanel record={selected} />
              <ValidityContextPanel record={selected} />
              <OutputComparisonPanel record={selected} />
              <ReasoningPanel record={selected} />
              <CrossPromptPanel record={selected} defaultExpanded />
              <CaseFactsPanel record={selected} />
            </>
          ) : (
            <EmptyState
              title={filteredIndex.length ? "Select a case" : "No cases match filters"}
              description={
                filteredIndex.length
                  ? "Choose a comparison from the review queue."
                  : "Try clearing filters or switching prompt mode to see more comparisons."
              }
            />
          )}
        </div>

        <aside className="review-right-panel">
          {selected ? (
            <ExpertChecklistPanel
              review={reviewState[caseReviewKey(selected)]}
              schemaVersion={selected.schema_version ?? schemaVersion}
              onUpdate={(p) => onUpdateReview(caseReviewKey(selected), p)}
            />
          ) : null}
          <PacketPanel
            count={packetIds.length}
            packetRecords={packetRecords}
            reviewState={reviewState}
            onSelectRecord={onSelectReviewId}
            onRemove={onRemoveFromPacket}
            onOpenSummary={() => setPacketSummaryOpen(true)}
            onExportJson={() => onExportPacket("json")}
            onExportCsv={() => onExportPacket("csv")}
            onCopyMd={() => onExportPacket("md")}
            onExportPdf={() => onExportPacket("pdf")}
            onBackupState={() => exportReviewStateBackup(reviewState, packetIds)}
            onImportState={onImportReviewState}
            {...packetPanelExtras}
          />
          <Callout title="Caution" variant="info">
            <p>{selected?.review_guidance.caution_note ?? "Audit signals only — not proof of unlawful discrimination."}</p>
          </Callout>
        </aside>
      </div>
      )}
    </div>
  );
}
