"use client";

import { useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { DownloadButton } from "@/components/DownloadButton";
import { MarkdownReportViewer } from "@/components/MarkdownReportViewer";
import { StatusPill } from "@/components/StatusPill";
import { PageHeader } from "@/components/detention/PageHeader";
import type { ReportEntry } from "@/lib/types";

const REPORT_TYPES = [
  { match: /qa/i, label: "QA" },
  { match: /analysis/i, label: "Analysis" },
  { match: /flagged|review/i, label: "Review packet" },
  { match: /method/i, label: "Methodology" },
  { match: /presentation/i, label: "Presentation" },
  { match: /limit/i, label: "Limitations" },
];

function reportType(name: string): string {
  for (const t of REPORT_TYPES) {
    if (t.match.test(name)) return t.label;
  }
  return "Other";
}

export function DetentionReportsPage({
  reports,
  isMock,
  selectedReport,
  onSelectReport,
}: {
  reports: ReportEntry[];
  isMock: boolean;
  selectedReport: string;
  onSelectReport: (name: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return reports.filter((r) => {
      if (typeFilter && reportType(r.report_name) !== typeFilter) return false;
      if (!q) return true;
      return r.title.toLowerCase().includes(q) || r.report_name.toLowerCase().includes(q);
    });
  }, [reports, search, typeFilter]);

  const active = filtered.find((r) => r.report_name === selectedReport) ?? filtered[0];

  return (
    <div className="tab-panel">
      <PageHeader title="Reports" subtitle="QA reports, analysis, review packets, and methodology documents." />

      <div className="report-downloads">
        {["data_access_policy.json", "detention_overview_metrics.json"].map((f) => (
          <a key={f} className="btn btn-secondary btn-sm" href={`/data/${f}`} download={f}>
            {f.replace(".json", "").replace(/_/g, " ")}
          </a>
        ))}
      </div>

      <div className="reports-toolbar">
        <input type="search" className="table-search" placeholder="Search reports…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">All types</option>
          {REPORT_TYPES.map((t) => (
            <option key={t.label} value={t.label}>{t.label}</option>
          ))}
        </select>
      </div>

      {filtered.length ? (
        <div className="reports-layout">
          <div className="report-cards">
            {filtered.map((r) => (
              <button
                key={r.report_name}
                type="button"
                className={`report-card ${active?.report_name === r.report_name ? "report-card-active" : ""}`}
                onClick={() => onSelectReport(r.report_name)}
              >
                <StatusPill label={reportType(r.report_name)} variant="info" />
                <strong>{r.title}</strong>
                <span className="muted">{r.report_name}</span>
              </button>
            ))}
          </div>
          {active ? (
            <div className="report-viewer-panel">
              <StatusPill label={isMock ? "Mock QA" : "Export"} variant="info" />
              <DownloadButton label="Download .md" filename={`${active.report_name}.md`} content={active.markdown_text} mime="text/markdown" />
              <MarkdownReportViewer markdown={active.markdown_text} title={active.title} />
            </div>
          ) : null}
        </div>
      ) : (
        <EmptyState title="No reports" description="reports.json not exported for this run." command="python -m benchassist.vercel_export --auto --use-case detention" />
      )}
    </div>
  );
}
