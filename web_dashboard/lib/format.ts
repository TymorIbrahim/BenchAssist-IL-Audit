import type { JsonRecord } from "./types";

export const LEGACY_METRICS_NOT_APPLICABLE = "not_applicable_under_minimal_dangerousness_schema";

export function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "string" && value.trim() === LEGACY_METRICS_NOT_APPLICABLE) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "boolean") return value ? 1 : 0;
  const n = Number(String(value).replace(/%/g, ""));
  return Number.isFinite(n) ? n : null;
}

/** True when a pairwise delta is a numeric shift (excludes minimal-schema N/A placeholders). */
export function hasMetricDeltaShift(value: unknown): boolean {
  const n = toNumber(value);
  return n !== null && n !== 0;
}

export function toBool(value: unknown): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  const s = String(value).toLowerCase().trim();
  return s === "true" || s === "1" || s === "yes";
}

export function formatRate(value: unknown, digits = 1): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(digits)}%`;
}

export function formatCount(value: unknown): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return Math.round(n).toLocaleString();
}

export function formatDate(iso: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export function truncate(text: unknown, max = 200): string {
  const s = String(text ?? "");
  if (s.length <= max) return s;
  return `${s.slice(0, max)}…`;
}

export function str(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

export type ReviewPriorityLevel = "high" | "medium" | "low";

export function normalizeReviewPriority(value: unknown): ReviewPriorityLevel | "" {
  const s = str(value).trim().toLowerCase();
  if (s === "high" || s === "medium" || s === "low") return s;
  return "";
}

export function reviewPriorityLabel(value: unknown): string {
  const level = normalizeReviewPriority(value);
  if (!level) return str(value) || "—";
  return level.charAt(0).toUpperCase() + level.slice(1);
}

export function matchesReviewPriority(rowValue: unknown, filter: string): boolean {
  if (!filter.trim()) return true;
  return normalizeReviewPriority(rowValue) === normalizeReviewPriority(filter);
}

export function isHighReviewPriority(value: unknown): boolean {
  return normalizeReviewPriority(value) === "high";
}

export function uniqueValues(rows: JsonRecord[], key: string): string[] {
  const set = new Set<string>();
  for (const row of rows) {
    const v = row[key];
    if (v !== null && v !== undefined && String(v).trim()) {
      set.add(String(v));
    }
  }
  return Array.from(set).sort();
}

export function isRtlText(text: string): boolean {
  return /[\u0590-\u05FF\u0600-\u06FF]/.test(text);
}

export function textDir(text: string): "rtl" | "ltr" {
  return isRtlText(text) ? "rtl" : "ltr";
}

/** Parse CSV/JSON list cells that may arrive as arrays or Python-style strings. */
export function coerceStringList(value: unknown): string[] {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) {
    return value.flatMap((v) => coerceStringList(v)).filter((s) => s && s.toLowerCase() !== "nan");
  }
  const text = String(value).trim();
  if (!text || text === "[]" || text.toLowerCase() === "nan") return [];
  if (text.startsWith("[")) {
    try {
      const parsed = JSON.parse(text.replace(/'/g, '"')) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map((v) => String(v)).filter((s) => s && s.toLowerCase() !== "nan");
      }
    } catch {
      // fall through
    }
  }
  return [text];
}

export function joinStringList(value: unknown, sep = ", "): string {
  const items = coerceStringList(value);
  return items.length ? items.join(sep) : "";
}
