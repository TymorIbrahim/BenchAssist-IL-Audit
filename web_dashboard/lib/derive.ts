export {
  strongestSignalLabel,
  strongestSignalExplanation,
  reviewPriority,
  reviewPriorityReason,
  reviewPriorityVariant,
  isHighPriority,
} from "./reviewPriority";
import { str, toBool } from "./format";
import type { JsonRecord } from "./types";
import { reviewPriority, strongestSignalLabel } from "./reviewPriority";

export function detectRunType(runLabel: string): string {
  const lower = runLabel.toLowerCase();
  if (lower === "empty") return "none";
  if (lower.startsWith("qa_") || lower.includes("mock")) return "mock";
  if (lower.includes("core_full")) return "core_full";
  if (lower.includes("core_pilot")) return "core_pilot";
  if (lower.includes("main_audit")) return "full";
  if (lower.includes("pilot")) return "pilot";
  return "audit";
}

export function runTypeLabel(runType: string): string {
  const labels: Record<string, string> = {
    core_full: "Core full audit",
    core_pilot: "Core pilot",
    full: "Full audit",
    pilot: "Pilot run",
    mock: "Mock / demo",
    none: "No run loaded",
    audit: "Audit run",
  };
  return labels[runType] ?? runType;
}

export function metricNeedsReview(value: unknown, threshold = 0.15): boolean {
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return false;
  const rate = n <= 1 ? n : n / 100;
  return rate >= threshold;
}

export function enrichRowForDisplay(row: JsonRecord): JsonRecord {
  return {
    ...row,
    strongest_signal: strongestSignalLabel(row),
    review_priority: reviewPriority(row),
    is_flagged: toBool(row.legal_framing_bias_flag) || toBool(row.is_flagged),
    display_case_label: str(row.display_case_label || row.case_id),
    display_variant_label: str(row.display_variant_label || row.variant_type),
  };
}

export function enrichRows(rows: JsonRecord[]): JsonRecord[] {
  return rows.map(enrichRowForDisplay);
}

export function rowsToCsv(rows: JsonRecord[], columns?: string[]): string {
  if (!rows.length) return "";
  const cols = columns ?? Object.keys(rows[0]);
  const escape = (v: unknown) => {
    const s = str(v);
    if (s.includes(",") || s.includes('"') || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };
  const lines = [cols.join(",")];
  for (const row of rows) {
    lines.push(cols.map((c) => escape(row[c])).join(","));
  }
  return lines.join("\n");
}

export function downloadText(filename: string, content: string, mime = "text/plain") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
