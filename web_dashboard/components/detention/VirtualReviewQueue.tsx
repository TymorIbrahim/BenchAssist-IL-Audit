"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CaseReviewRecord } from "@/lib/detentionCaseReview";
import { caseReviewKey, displayWhyFlagged } from "@/lib/detentionCaseReview";

const ROW_HEIGHT = 112;
const OVERSCAN = 4;

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
    <button
      type="button"
      className={`review-queue-item ${selected ? "selected" : ""}`}
      style={{ minHeight: ROW_HEIGHT }}
      onClick={onSelect}
    >
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

export function VirtualReviewQueue({
  records,
  selectedId,
  packetIds,
  onSelect,
  listRef,
}: {
  records: CaseReviewRecord[];
  selectedId: string | null;
  packetIds: string[];
  onSelect: (record: CaseReviewRecord) => void;
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
    const endIdx = Math.min(records.length, startIdx + visible);
    return { start: startIdx, end: endIdx, offset: startIdx * ROW_HEIGHT };
  }, [scrollTop, viewportHeight, records.length]);

  const slice = records.slice(start, end);

  return (
    <div
      className="review-queue-list virtual-review-queue"
      ref={containerRef}
      onScroll={(e) => setScrollTop((e.target as HTMLDivElement).scrollTop)}
      role="listbox"
      aria-label="Review queue"
    >
      <div style={{ height: records.length * ROW_HEIGHT, position: "relative" }}>
        <div style={{ transform: `translateY(${offset}px)` }}>
          {slice.map((r) => (
            <ReviewQueueItem
              key={caseReviewKey(r)}
              record={r}
              selected={selectedId === caseReviewKey(r)}
              inPacket={packetIds.includes(caseReviewKey(r))}
              onSelect={() => onSelect(r)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
