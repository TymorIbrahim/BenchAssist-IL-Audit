"use client";

import { useMemo, useState } from "react";
import { StatusPill } from "@/components/StatusPill";
import { str, toBool } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export function DetentionLegalTextViewer({
  row,
  notes,
  onNotesChange,
}: {
  row: JsonRecord;
  notes: string;
  onNotesChange: (notes: string) => void;
}) {
  const fullText = str(row.full_text || row.text);
  const keywords = useMemo(() => {
    const mk = str(row.matched_keywords);
    if (mk) return mk.split(/[;,]/).map((k) => k.trim()).filter(Boolean);
    if (Array.isArray(row.ingest_matched_keywords)) return row.ingest_matched_keywords.map(String);
    return [];
  }, [row]);

  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState(false);

  const displayText = useMemo(() => {
    if (!search.trim()) return fullText;
    const q = search.toLowerCase();
    const idx = fullText.toLowerCase().indexOf(q);
    if (idx < 0) return fullText;
    const start = Math.max(0, idx - 200);
    const end = Math.min(fullText.length, idx + search.length + 400);
    return `${start > 0 ? "…" : ""}${fullText.slice(start, end)}${end < fullText.length ? "…" : ""}`;
  }, [fullText, search]);

  const jumpToKeyword = (kw: string) => {
    setSearch(kw);
    setExpanded(true);
  };

  const citation = [
    str(row.source_dataset),
    str(row.source_id),
    str(row.likely_case_stage).replace(/_/g, " "),
  ].filter(Boolean).join(" · ");

  return (
    <div className="legal-text-viewer">
      <div className="legal-text-toolbar">
        <StatusPill label="Not used in strict fairness rates" variant="caution" />
        {toBool(row.sensitive_content_flag) ? <StatusPill label="Sensitive content flagged" variant="concern" /> : null}
        <StatusPill label={`Stage: ${str(row.likely_case_stage).replace(/_/g, " ")}`} variant="neutral" />
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigator.clipboard.writeText(citation)}>Copy citation</button>
      </div>

      {keywords.length ? (
        <div className="keyword-panel">
          <strong>Matched keywords</strong>
          <div className="keyword-chips">
            {keywords.map((kw) => (
              <button key={kw} type="button" className="keyword-chip" onClick={() => jumpToKeyword(kw)}>{kw}</button>
            ))}
          </div>
        </div>
      ) : null}

      <label className="search-in-text">
        Search within text
        <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search Hebrew/English text…" />
      </label>

      <div
        className={`legal-text-body ${expanded ? "legal-text-expanded" : "legal-text-collapsed"}`}
        dir="rtl"
        lang="he"
      >
        {displayText || "No full text available."}
      </div>
      {fullText.length > 800 ? (
        <button type="button" className="link-button" onClick={() => setExpanded(!expanded)}>
          {expanded ? "Collapse text" : "Expand full legal text"}
        </button>
      ) : null}

      <label className="legal-reliability-notes">
        Legal reliability notes (local only)
        <textarea rows={3} value={notes} onChange={(e) => onNotesChange(e.target.value)} placeholder="Expert notes on grounding, hallucination risk, citation quality…" />
      </label>
    </div>
  );
}
