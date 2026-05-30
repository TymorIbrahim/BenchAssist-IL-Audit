"use client";

import { Card } from "@/components/Card";
import { StatusPill } from "@/components/StatusPill";
import { PageHeader } from "@/components/detention/PageHeader";
import { changedFieldsSummary, reviewKey, reviewerSummary, type ReviewRecord } from "@/lib/detentionReview";
import { str } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export function DetentionExpertWorkspace({
  flagged,
  reviewState,
  packetIds,
  onSelectCase,
  onToggleReviewed,
  onTogglePacket,
  onExportPacket,
  filterReviewed,
  onFilterReviewedChange,
}: {
  flagged: JsonRecord[];
  reviewState: Record<string, ReviewRecord>;
  packetIds: string[];
  onSelectCase: (row: JsonRecord) => void;
  onToggleReviewed: (row: JsonRecord, reviewed: boolean) => void;
  onTogglePacket: (row: JsonRecord) => void;
  onExportPacket: (format: "json" | "csv" | "md") => void;
  filterReviewed: "all" | "reviewed" | "unreviewed";
  onFilterReviewedChange: (v: "all" | "reviewed" | "unreviewed") => void;
}) {
  const queue = flagged.filter((r) => {
    const reviewed = reviewState[reviewKey(r)]?.reviewed;
    if (filterReviewed === "reviewed") return reviewed;
    if (filterReviewed === "unreviewed") return !reviewed;
    return true;
  });

  const packetRows = flagged.filter((r) => packetIds.includes(reviewKey(r)));

  return (
    <div className="tab-panel">
      <PageHeader
        title="Expert Workspace"
        subtitle="Review queue, local notes, and reviewer packet builder."
        note="Review notes are stored only in this browser unless exported."
      />

      <div className="expert-workspace-toolbar">
        <label>
          Show
          <select value={filterReviewed} onChange={(e) => onFilterReviewedChange(e.target.value as typeof filterReviewed)}>
            <option value="all">All flagged</option>
            <option value="unreviewed">Unreviewed only</option>
            <option value="reviewed">Reviewed locally</option>
          </select>
        </label>
        <span className="muted">{queue.length} in queue · {packetIds.length} in packet</span>
      </div>

      <div className="expert-workspace-grid">
        <section className="section-card">
          <h3>Review queue</h3>
          <ul className="review-queue-list">
            {queue.slice(0, 30).map((r) => {
              const key = reviewKey(r);
              const reviewed = reviewState[key]?.reviewed;
              return (
                <li key={key} className="review-queue-item">
                  <div className="review-queue-meta">
                    <StatusPill label={str(r.review_priority)} variant={str(r.review_priority) === "High" ? "concern" : "neutral"} />
                    {reviewed ? <StatusPill label="Reviewed" variant="success" /> : null}
                    {packetIds.includes(key) ? <StatusPill label="In packet" variant="info" /> : null}
                  </div>
                  <strong>{str(r.case_id)} · {str(r.display_variant)}</strong>
                  <p className="muted">{str(r.issue_type).slice(0, 100)}</p>
                  <p className="muted">Changed: {changedFieldsSummary(r).join(", ") || "—"}</p>
                  <div className="btn-row">
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => onSelectCase(r)}>Open comparison</button>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => onToggleReviewed(r, !reviewed)}>
                      {reviewed ? "Unmark" : "Mark reviewed"}
                    </button>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => onTogglePacket(r)}>
                      {packetIds.includes(key) ? "Remove" : "Add to packet"}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="section-card review-packet-panel">
          <h3>Reviewer packet ({packetRows.length})</h3>
          {packetRows.length ? (
            <ul className="packet-list">
              {packetRows.map((r) => (
                <li key={reviewKey(r)}>
                  <span>{str(r.case_id)} / {str(r.variant_id)}</span>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => onTogglePacket(r)}>Remove</button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Add cases from the queue or Case Review tab.</p>
          )}
          <div className="packet-bar">
            <button type="button" className="btn btn-primary btn-sm" onClick={() => onExportPacket("json")}>Export JSON</button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onExportPacket("csv")}>Export CSV</button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onExportPacket("md")}>Copy Markdown</button>
          </div>
          {packetRows.length ? (
            <Card title="Packet preview">
              <pre className="packet-preview">{reviewerSummary(packetRows[0]).slice(0, 400)}…</pre>
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
