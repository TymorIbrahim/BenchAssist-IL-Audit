"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/Card";
import { DataTable } from "@/components/DataTable";
import { StatusPill } from "@/components/StatusPill";
import {
  changedFieldsSummary,
  reviewKey,
  reviewerSummary,
  type ReviewRecord,
} from "@/lib/detentionReview";
import { str, toBool } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

type ViewMode = "table" | "cards";
type GroupBy = "none" | "issue_type" | "case_id" | "variant_type" | "prompt_mode";

function formatDelta(v: unknown): string {
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  if (n === 0) return "0";
  return n > 0 ? `+${n}` : String(n);
}

function groupRows(rows: JsonRecord[], groupBy: GroupBy): [string, JsonRecord[]][] {
  if (groupBy === "none") return [["All flagged cases", rows]];
  const map = new Map<string, JsonRecord[]>();
  for (const row of rows) {
    const key = str(row[groupBy === "issue_type" ? "issue_type" : groupBy]) || "Unknown";
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(row);
  }
  return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
}

export function DetentionFlaggedTriage({
  rows,
  reviewState,
  packetIds,
  onSelectCase,
  onToggleReviewed,
  onTogglePacket,
  onCopySummary,
}: {
  rows: JsonRecord[];
  reviewState: Record<string, ReviewRecord>;
  packetIds: string[];
  onSelectCase: (row: JsonRecord) => void;
  onToggleReviewed: (row: JsonRecord, reviewed: boolean) => void;
  onTogglePacket: (row: JsonRecord) => void;
  onCopySummary: (row: JsonRecord) => void;
}) {
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [groupBy, setGroupBy] = useState<GroupBy>("none");

  const groups = useMemo(() => groupRows(rows, groupBy), [rows, groupBy]);

  const actionCell = (r: JsonRecord) => {
    const key = reviewKey(r);
    const inPacket = packetIds.includes(key);
    return (
      <div className="btn-row triage-actions">
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => onSelectCase(r)}>View comparison</button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onToggleReviewed(r, !(reviewState[key]?.reviewed))}>
          {reviewState[key]?.reviewed ? "Unmark reviewed" : "Mark reviewed"}
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onCopySummary(r)}>Copy summary</button>
        <button type="button" className={`btn btn-sm ${inPacket ? "btn-primary" : "btn-secondary"}`} onClick={() => onTogglePacket(r)}>
          {inPacket ? "Remove from packet" : "Add to packet"}
        </button>
      </div>
    );
  };

  return (
    <div className="triage-board">
      <div className="triage-toolbar">
        <div className="btn-row">
          <button type="button" className={`btn btn-sm ${viewMode === "table" ? "btn-primary" : "btn-secondary"}`} onClick={() => setViewMode("table")}>Table view</button>
          <button type="button" className={`btn btn-sm ${viewMode === "cards" ? "btn-primary" : "btn-secondary"}`} onClick={() => setViewMode("cards")}>Card view</button>
        </div>
        <label className="select-label-inline">
          Group by
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value as GroupBy)}>
            <option value="none">None</option>
            <option value="issue_type">Issue type</option>
            <option value="case_id">Base scenario</option>
            <option value="variant_type">Variant</option>
            <option value="prompt_mode">Prompt mode</option>
          </select>
        </label>
        <span className="muted">{rows.length} flagged · {packetIds.length} in packet</span>
      </div>

      {groups.map(([groupLabel, groupRows]) => (
        <div key={groupLabel} className="triage-group">
          {groupBy !== "none" ? <h4 className="triage-group-title">{groupLabel.replace(/_/g, " ")} ({groupRows.length})</h4> : null}

          {viewMode === "table" ? (
            <DataTable
              rows={groupRows}
              searchable
              downloadable
              showCopyJsonAction={false}
              columns={[
                { key: "review_priority", label: "Review priority", render: (r) => <StatusPill label={str(r.review_priority)} variant={str(r.review_priority) === "High" ? "concern" : "neutral"} /> },
                { key: "issue_type", label: "Issue type", render: (r) => str(r.issue_type).slice(0, 60) },
                { key: "case_id", label: "Base scenario" },
                { key: "display_variant", label: "Variant" },
                { key: "prompt_mode", label: "Prompt mode", render: (r) => str(r.prompt_mode) || "baseline" },
                { key: "case_id", label: "Changed fields", render: (r) => changedFieldsSummary(r).join(", ") || "—" },
                { key: "dangerousness_level_delta", label: "Dangerousness", render: (r) => formatDelta(r.dangerousness_level_delta) },
                { key: "obstruction_risk_level_delta", label: "Obstruction", render: (r) => formatDelta(r.obstruction_risk_level_delta) },
                { key: "recommended_action_type_delta", label: "Action", render: (r) => formatDelta(r.recommended_action_type_delta) },
                { key: "identity_leakage_flag", label: "Identity", render: (r) => (toBool(r.identity_leakage_flag) ? "Yes" : "—") },
                { key: "unsupported_risk_inference_flag", label: "Unsupported", render: (r) => (toBool(r.unsupported_risk_inference_flag) ? "Yes" : "—") },
                { key: "_actions", label: "Actions", render: actionCell },
              ]}
            />
          ) : (
            <div className="triage-cards">
              {groupRows.map((r) => {
                const key = reviewKey(r);
                return (
                  <Card key={key} title={`${str(r.case_id)} · ${str(r.display_variant)}`}>
                    <div className="triage-card-meta">
                      <StatusPill label={str(r.review_priority)} variant={str(r.review_priority) === "High" ? "concern" : "neutral"} />
                      {reviewState[key]?.reviewed ? <StatusPill label="Reviewed locally" variant="success" /> : null}
                      {packetIds.includes(key) ? <StatusPill label="In packet" variant="info" /> : null}
                    </div>
                    <p className="muted">{str(r.issue_type).slice(0, 120)}</p>
                    <p><strong>Shifts:</strong> dangerousness {formatDelta(r.dangerousness_level_delta)}, obstruction {formatDelta(r.obstruction_risk_level_delta)}, action {formatDelta(r.recommended_action_type_delta)}</p>
                    <p className="muted">{reviewerSummary(r).split("\n").slice(0, 3).join(" · ")}</p>
                    {actionCell(r)}
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
