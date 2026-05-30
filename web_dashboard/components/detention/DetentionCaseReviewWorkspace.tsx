"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/Card";
import { Callout } from "@/components/Callout";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/detention/PageHeader";
import { CaseTextDiff } from "@/components/detention/CaseTextDiff";
import { CrossPromptPanel } from "@/components/detention/CrossPromptPanel";
import { VirtualReviewQueue } from "@/components/detention/VirtualReviewQueue";
import { computeReviewProgress, ReviewProgressPanel } from "@/components/detention/ReviewProgressPanel";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import {
  caseReviewKey,
  DEFAULT_CASE_REVIEW_FILTERS,
  dirForText,
  displayWhyFlagged,
  filterCaseReviewRecords,
  formatOutputValue,
  OUTPUT_COMPARISON_ROWS,
  outputDiffIndicator,
  type CaseReviewFilters,
  type CaseReviewRecord,
} from "@/lib/detentionCaseReview";
import {
  CHECKLIST_ITEMS,
  EMPTY_CHECKLIST,
  exportReviewStateBackup,
  importReviewStateBackup,
  REVIEW_DECISION_OPTIONS,
  type ReviewRecord,
} from "@/lib/detentionReview";
import { str, toBool } from "@/lib/format";

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
          <dt>{k.replace(/_/g, " ")}</dt>
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
      <summary>{title}{status ? ` · ${status.replace(/_/g, " ")}` : ""}</summary>
      <div className="prompt-block">
        <CopyButton text={prompt} />
        <pre dir={dirForText(prompt)}>{prompt}</pre>
      </div>
    </details>
  );
}

function ReviewQueueItem({
  record,
  selected,
  inPacket,
  onSelect,
}: {
  record: CaseReviewRecord;
  selected: boolean;
  inPacket: boolean;
  onSelect: () => void;
}) {
  return (
    <button type="button" className={`review-queue-item ${selected ? "selected" : ""}`} onClick={onSelect}>
      <div className="review-queue-item-top">
        <strong>{record.base_case_title || record.base_case_id}</strong>
        {inPacket ? <span className="packet-badge">In packet</span> : null}
      </div>
      <p className="muted">{record.variant_case.variant_label || record.variant_type} · {record.prompt_mode}</p>
      <div className="issue-tags compact">
        <span className={`priority-tag priority-${record.review_priority}`}>{record.review_priority}</span>
        {record.is_flagged ? null : <span className="issue-tag">Not flagged</span>}
        {record.issue_types.slice(0, 2).map((t) => (
          <span key={t} className="issue-tag">{t.slice(0, 48)}</span>
        ))}
      </div>
      <p className="muted queue-reason">{displayWhyFlagged(record).slice(0, 100)}</p>
    </button>
  );
}

function CaseFactsPanel({ record }: { record: CaseReviewRecord }) {
  const preserved = record.variant_case.legally_relevant_facts_preserved;
  const preservedLabel = preserved === true ? "Yes" : preserved === false ? "No" : "Needs review";

  return (
    <section className="review-section">
      <h3>1. What was given to the model?</h3>
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
          <p className="muted panel-sub">{record.variant_id} · {record.protected_attribute_tested.replace(/_/g, " ")}</p>
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
    </section>
  );
}

function OutputComparisonPanel({ record }: { record: CaseReviewRecord }) {
  return (
    <section className="review-section">
      <h3>2. What did the model output?</h3>
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
            {OUTPUT_COMPARISON_ROWS.map(({ key, label, list }) => {
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
  const lines = [
    d.dangerousness_shift ? `Dangerousness shift: ${d.dangerousness_shift}` : null,
    d.obstruction_risk_shift ? `Obstruction risk shift: ${d.obstruction_risk_shift}` : null,
    d.recommended_action_shift ? `Recommended action shift: ${d.recommended_action_shift}` : null,
    d.duration_shift ? `Duration shift: ${d.duration_shift}` : null,
    d.alternatives_omitted ? "Alternatives considered: present → omitted" : null,
    d.procedural_safeguards_omitted ? "Procedural safeguards: present → omitted" : null,
    d.credibility_framing_shift ? `Credibility framing shift: ${d.credibility_framing_shift}` : null,
    `Identity leakage: ${toBool(d.identity_leakage_flag) ? "yes" : "no"}`,
    `Unsupported risk inference: ${toBool(d.unsupported_risk_inference_flag) ? "yes" : "no"}`,
  ].filter(Boolean);

  return (
    <section className="review-section">
      <h3>3. What changed?</h3>
      {!record.is_flagged ? (
        <p className="muted">No primary audit flag on this comparison — review for completeness or subtle shifts.</p>
      ) : null}
      <p className="muted">{record.diff.diff_summary}</p>
      <ul className="diff-summary-list">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <Callout title="Why this was flagged" variant="caution">
        <p>{displayWhyFlagged(record)}</p>
        <p className="muted">{record.review_guidance.plain_language_summary}</p>
      </Callout>
    </section>
  );
}

function ExpertChecklistPanel({
  review,
  onUpdate,
}: {
  review: ReviewRecord | undefined;
  onUpdate: (patch: Partial<ReviewRecord>) => void;
}) {
  const checklist = { ...EMPTY_CHECKLIST, ...(review?.checklist ?? {}) };

  const updateChecklist = (key: keyof typeof checklist, value: boolean | null) => {
    onUpdate({ checklist: { ...checklist, [key]: value } });
  };

  return (
    <section className="review-section">
      <h3>4. Legal expert review</h3>
      <p className="muted local-storage-note">Notes and checklist are stored only in this browser unless exported.</p>
      <ul className="checklist-list">
        {CHECKLIST_ITEMS.map((item) => (
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

function FullMemoPanel({ record }: { record: CaseReviewRecord }) {
  const neutral = record.neutral_output.full_memo_text || record.neutral_output.reasoning_text || "";
  const variant = record.variant_output.full_memo_text || record.variant_output.reasoning_text || "";
  if (!neutral && !variant) return null;
  return (
    <section className="review-section">
      <h3>Full memo text</h3>
      <div className="side-by-side-panels">
        <Card title="Neutral memo">
          <pre dir={dirForText(neutral)} className="legal-text-block">{neutral || "—"}</pre>
        </Card>
        <Card title="Variant memo">
          <pre dir={dirForText(variant)} className="legal-text-block">{variant || "—"}</pre>
        </Card>
      </div>
    </section>
  );
}

function ReasoningPanel({ record }: { record: CaseReviewRecord }) {
  const n = str(record.neutral_output.reasoning_text);
  const v = str(record.variant_output.reasoning_text);
  if (!n && !v) return null;
  return (
    <section className="review-section">
      <h3>Model reasoning (excerpt)</h3>
      <div className="side-by-side-panels">
        <Card title="Neutral reasoning">
          <pre dir={dirForText(n)} className="reasoning-excerpt">{n.slice(0, 1200) || "—"}{n.length > 1200 ? "…" : ""}</pre>
        </Card>
        <Card title="Variant reasoning">
          <pre dir={dirForText(v)} className="reasoning-excerpt">{v.slice(0, 1200) || "—"}{v.length > 1200 ? "…" : ""}</pre>
        </Card>
      </div>
    </section>
  );
}

function PacketPanel({
  count,
  packetRecords,
  onRemove,
  onExportJson,
  onExportCsv,
  onCopyMd,
  onExportPdf,
  onBackupState,
  onImportState,
}: {
  count: number;
  packetRecords: CaseReviewRecord[];
  onRemove: (id: string) => void;
  onExportJson: () => void;
  onExportCsv: () => void;
  onCopyMd: () => void;
  onExportPdf: () => void;
  onBackupState: () => void;
  onImportState: (file: File) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <Card title="Review packet">
      <p className="muted">{count} case{count === 1 ? "" : "s"} in packet</p>
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
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onExportJson}>Export JSON</button>
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onExportCsv}>Export CSV</button>
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onCopyMd}>Copy Markdown</button>
        <button type="button" className="btn btn-secondary btn-sm" disabled={!count} onClick={onExportPdf}>Export PDF</button>
      </div>
      <div className="btn-row">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onBackupState}>Backup review state</button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => fileRef.current?.click()}>Import review state</button>
        <input ref={fileRef} type="file" accept="application/json" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) onImportState(f); e.target.value = ""; }} />
      </div>
    </Card>
  );
}

export function DetentionCaseReviewWorkspace({
  bundle,
  reviewState,
  packetIds,
  selectedId,
  onSelectRecord,
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
}: {
  bundle: DetentionDashboardBundle;
  reviewState: Record<string, ReviewRecord>;
  packetIds: string[];
  selectedId: string | null;
  onSelectRecord: (record: CaseReviewRecord) => void;
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
}) {
  const [filters, setFilters] = useState<CaseReviewFilters>({ ...DEFAULT_CASE_REVIEW_FILTERS, ...initialFilters, focusMode });
  const [mobilePane, setMobilePane] = useState<"queue" | "detail" | "checklist">("queue");
  const queueRef = useRef<HTMLDivElement>(null);

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
  const effectiveFilters = useMemo(() => ({ ...filters, focusMode }), [filters, focusMode]);

  const filtered = useMemo(
    () => filterCaseReviewRecords(records, effectiveFilters, reviewState),
    [records, effectiveFilters, reviewState],
  );

  const selected = useMemo(
    () => filtered.find((r) => caseReviewKey(r) === selectedId) ?? filtered[0] ?? null,
    [filtered, selectedId],
  );

  const progress = useMemo(
    () =>
      computeReviewProgress(
        records,
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
    if (selectedId && selected) setMobilePane("detail");
  }, [selectedId, selected]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!filtered.length || e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      const idx = selected ? filtered.findIndex((r) => caseReviewKey(r) === caseReviewKey(selected)) : -1;
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        const next = filtered[Math.min(idx + 1, filtered.length - 1)];
        if (next) onSelectRecord(next);
      }
      if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        const prev = filtered[Math.max(idx - 1, 0)];
        if (prev) onSelectRecord(prev);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [filtered, selected, onSelectRecord]);

  const filterOptions = useMemo(() => ({
    variants: [...new Set(records.map((r) => r.variant_type))].sort(),
    bases: [...new Set(records.map((r) => r.base_case_id))].sort(),
    protected: [...new Set(records.map((r) => r.protected_attribute_tested).filter(Boolean))].sort(),
    issues: [...new Set(records.flatMap((r) => r.issue_types))].sort(),
  }), [records]);

  if (loading) {
    return (
      <div className="loading-screen" aria-live="polite" aria-busy="true">
        <p>{loadStatus || "Loading case review records…"}</p>
      </div>
    );
  }

  if (!records.length && !bundle.caseReviewIndexCount) {
    return (
      <EmptyState
        title="Case review records not available"
        description="This file is required for the full side-by-side expert review workspace."
        command="python -m benchassist.detention_case_review_export --run-dir results/gemini/detention_full --synthetic-input data/synthetic/detention_core_cases.csv --output web_dashboard/public/data/detention_case_review_records.json"
      />
    );
  }

  if (!records.length && bundle.caseReviewIndexCount > 0) {
    const pendingProgress = computeReviewProgress(
      [],
      reviewState,
      packetIds,
      bundle.caseReviewIndex.filter((e) => e.is_flagged).length,
    );
    return (
      <div className="loading-screen">
        <p>Loading {bundle.caseReviewIndexCount} review records…</p>
        <ReviewProgressPanel progress={pendingProgress} pendingLoad />
      </div>
    );
  }

  const handleSelectRecord = (record: CaseReviewRecord) => {
    onSelectRecord(record);
    setMobilePane("detail");
  };

  return (
    <div className="case-review-workspace">
      <PageHeader
        title="Case Review Workspace"
        subtitle="Review neutral-vs-variant model outputs side by side."
        note={bundle.caseReviewMeta?.prompt_reconstruction_note}
      />

      <div className="review-status-chips">
        <StatusChip>{bundle.dataStatus.replace(/_/g, " ")}</StatusChip>
        <StatusChip>Synthetic comparison</StatusChip>
        <StatusChip tone="ok">Real cases excluded from strict rates</StatusChip>
        {selected ? <StatusChip tone={selected.review_priority === "high" ? "warn" : "default"}>Priority: {selected.review_priority}</StatusChip> : null}
        <label className="focus-mode-toggle">
          <input type="checkbox" checked={focusMode} onChange={(e) => onFocusModeChange(e.target.checked)} />
          Focus review mode
        </label>
        <label className="focus-mode-toggle">
          <input type="checkbox" checked={filters.flaggedOnly} onChange={(e) => patchFilters({ flaggedOnly: e.target.checked })} />
          Flagged only
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
            onClick={() => setMobilePane(pane)}
          >
            {pane === "queue" ? "Queue" : pane === "detail" ? "Comparison" : "Checklist"}
          </button>
        ))}
      </div>

      <div className={`case-review-workspace-grid mobile-pane-${mobilePane}`}>
        <aside className="review-queue-panel">
          <Card title={`Review queue (${filtered.length})`}>
            <input
              type="search"
              placeholder="Search cases…"
              value={filters.search}
              onChange={(e) => patchFilters({ search: e.target.value })}
              className="filter-search"
            />
            <div className="review-filter-grid">
              <select value={filters.reviewPriority} onChange={(e) => patchFilters({ reviewPriority: e.target.value })}>
                <option value="">All priorities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <select value={filters.variantType} onChange={(e) => patchFilters({ variantType: e.target.value })}>
                <option value="">All variants</option>
                {filterOptions.variants.map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
              </select>
              <select value={filters.baseCaseId} onChange={(e) => patchFilters({ baseCaseId: e.target.value })}>
                <option value="">All base scenarios</option>
                {filterOptions.bases.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
              <select value={filters.localReview} onChange={(e) => patchFilters({ localReview: e.target.value as CaseReviewFilters["localReview"] })}>
                <option value="all">All review states</option>
                <option value="unreviewed">Unreviewed locally</option>
                <option value="reviewed">Reviewed locally</option>
              </select>
              <select value={filters.identityLeakage} onChange={(e) => patchFilters({ identityLeakage: e.target.value })}>
                <option value="">Identity leakage: any</option>
                <option value="yes">Identity leakage: yes</option>
                <option value="no">Identity leakage: no</option>
              </select>
              <select value={filters.issueType} onChange={(e) => patchFilters({ issueType: e.target.value })}>
                <option value="">All issue types</option>
                {filterOptions.issues.map((issue) => (
                  <option key={issue} value={issue}>{issue.slice(0, 40)}</option>
                ))}
              </select>
            </div>
            <p className="muted keyboard-hint">Tip: use ↑/↓ or j/k to move between cases in the queue.</p>
            <VirtualReviewQueue
              records={filtered}
              selectedId={selected ? caseReviewKey(selected) : null}
              packetIds={packetIds}
              onSelect={handleSelectRecord}
              listRef={queueRef}
            />
          </Card>
        </aside>

        <div className="review-main-panel">
          {selected ? (
            <>
              <div className="sticky-comparison-header">
                <h2>{selected.base_case_title} · {selected.variant_case.variant_label}</h2>
                <p className="muted">{selected.review_guidance.plain_language_summary}</p>
                <div className="btn-row">
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => onTogglePacket(selected)}>
                    {packetIds.includes(caseReviewKey(selected)) ? "Remove from packet" : "Add to packet"}
                  </button>
                  <CopyButton text={selected.review_guidance.plain_language_summary} label="Copy summary" />
                </div>
              </div>
              <CaseFactsPanel record={selected} />
              <OutputComparisonPanel record={selected} />
              <FullMemoPanel record={selected} />
              <ReasoningPanel record={selected} />
              <CrossPromptPanel record={selected} />
              <DiffSummaryPanel record={selected} />
            </>
          ) : (
            <EmptyState title="Select a case" description="Choose a comparison from the review queue." />
          )}
        </div>

        <aside className="review-right-panel">
          {selected ? (
            <ExpertChecklistPanel
              review={reviewState[caseReviewKey(selected)]}
              onUpdate={(p) => onUpdateReview(caseReviewKey(selected), p)}
            />
          ) : null}
          <PacketPanel
            count={packetIds.length}
            packetRecords={packetRecords}
            onRemove={onRemoveFromPacket}
            onExportJson={() => onExportPacket("json")}
            onExportCsv={() => onExportPacket("csv")}
            onCopyMd={() => onExportPacket("md")}
            onExportPdf={() => onExportPacket("pdf")}
            onBackupState={() => exportReviewStateBackup(reviewState, packetIds)}
            onImportState={onImportReviewState}
          />
          <Callout title="Caution" variant="info">
            <p>{selected?.review_guidance.caution_note ?? "Audit signals only — not proof of unlawful discrimination."}</p>
          </Callout>
        </aside>
      </div>
    </div>
  );
}
