"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CaseReviewIndexEntry, CaseReviewRecord } from "@/lib/detentionCaseReview";
import {
  analysisBucketLabel,
  dangerousnessPairLabel,
  shortQueueIssueLabel,
} from "@/lib/detentionCaseReview";
import { formatVariantLabel } from "@/lib/v2/dataUtils";

const ROW_HEIGHT = 118;
const OVERSCAN = 4;

function ReviewQueueItem({
  entry,
  record,
  selected,
  inPacket,
  onSelect,
}: {
  entry: CaseReviewIndexEntry;
  record?: CaseReviewRecord;
  selected: boolean;
  inPacket: boolean;
  onSelect: () => void;
}) {
  const bucket = analysisBucketLabel(record?.analysis_bucket ?? entry.analysis_bucket);
  const dangerPair = record ? dangerousnessPairLabel(record) : null;

  return (
    <button
      type="button"
      className={`review-queue-item ${selected ? "selected" : ""} ${entry.is_flagged ? "flagged" : ""}`}
      style={{ minHeight: ROW_HEIGHT }}
      onClick={onSelect}
    >
      <div className="review-queue-item-top">
        <strong>{entry.base_case_id}</strong>
        {inPacket ? <span className="packet-badge">In packet</span> : null}
      </div>
      <p className="muted queue-item-sub">
        {entry.variant_label || formatVariantLabel(entry.variant_type)} · {formatVariantLabel(entry.prompt_mode)}
      </p>
      {dangerPair ? (
        <p className="queue-danger-pair">{dangerPair}</p>
      ) : entry.is_flagged ? (
        <p className="muted queue-reason">{entry.why_flagged_short?.slice(0, 72) ?? "Flagged comparison"}</p>
      ) : null}
      <div className="issue-tags compact">
        <span className={`priority-tag priority-${entry.review_priority}`}>{entry.review_priority}</span>
        {bucket ? <span className="issue-tag bucket-tag">{bucket}</span> : null}
        {entry.is_flagged ? (
          entry.issue_types.slice(0, 1).map((t) => (
            <span key={t} className="issue-tag">{shortQueueIssueLabel(t)}</span>
          ))
        ) : (
          <span className="issue-tag">Not flagged</span>
        )}
      </div>
    </button>
  );
}

export function VirtualReviewQueue({
  entries,
  recordsById,
  selectedId,
  packetIds,
  onSelect,
  listRef,
}: {
  entries: CaseReviewIndexEntry[];
  recordsById: Record<string, CaseReviewRecord>;
  selectedId: string | null;
  packetIds: string[];
  onSelect: (entry: CaseReviewIndexEntry) => void;
  listRef?: React.RefObject<HTMLDivElement>;
}) {
  const internalRef = useRef<HTMLDivElement>(null);
  const containerRef = listRef ?? internalRef;
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(480);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setViewportHeight(el.clientHeight || 480));
    ro.observe(el);
    return () => ro.disconnect();
  }, [containerRef]);

  const { start, end, offset } = useMemo(() => {
    const startIdx = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const visible = Math.ceil(viewportHeight / ROW_HEIGHT) + OVERSCAN * 2;
    const endIdx = Math.min(entries.length, startIdx + visible);
    return { start: startIdx, end: endIdx, offset: startIdx * ROW_HEIGHT };
  }, [scrollTop, viewportHeight, entries.length]);

  const slice = entries.slice(start, end);

  return (
    <div
      className="review-queue-list virtual-review-queue"
      ref={containerRef}
      onScroll={(e) => setScrollTop((e.target as HTMLDivElement).scrollTop)}
      role="listbox"
      aria-label="Review queue"
    >
      <div style={{ height: entries.length * ROW_HEIGHT, position: "relative" }}>
        <div style={{ transform: `translateY(${offset}px)` }}>
          {slice.map((entry) => (
            <ReviewQueueItem
              key={entry.review_record_id}
              entry={entry}
              record={recordsById[entry.review_record_id]}
              selected={selectedId === entry.review_record_id}
              inPacket={packetIds.includes(entry.review_record_id)}
              onSelect={() => onSelect(entry)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
