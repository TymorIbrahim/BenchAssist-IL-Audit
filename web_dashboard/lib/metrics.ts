import { toNumber } from "./format";
import type { JsonRecord, OverviewMetrics } from "./types";

export const MAIN_METRICS = [
  {
    key: "main_legal_framing_flag_rate",
    label: "Legal framing signal rate",
    source: "overview",
    caution: "Screening signal — not proof of discrimination.",
  },
  {
    key: "action_type_flip_rate",
    label: "Action type flip rate",
    source: "overview",
    caution: "Category change may or may not be legally justified.",
  },
  {
    key: "remedy_weaker_rate",
    label: "Remedy weaker rate",
    source: "overview",
    caution: "Compare with counterfactual validity before concluding concern.",
  },
  {
    key: "evidence_burden_higher_rate",
    label: "Evidence burden higher rate",
    source: "overview",
    caution: "Higher proof requests require human legal review.",
  },
  {
    key: "credibility_more_skeptical_rate",
    label: "Credibility more skeptical rate",
    source: "overview",
    caution: "Tone shifts are audit signals, not findings of bias.",
  },
  {
    key: "rights_orientation_weaker_rate",
    label: "Rights orientation weaker rate",
    source: "overview",
    caution: "Protective emphasis may vary for non-demographic reasons.",
  },
] as const;

export function overviewMetricValue(
  overview: OverviewMetrics,
  key: string,
): number | null {
  const v = overview[key as keyof OverviewMetrics];
  return typeof v === "number" ? v : toNumber(v);
}

export function avgFromGroup(rows: JsonRecord[], key: string): number | null {
  const vals = rows.map((r) => toNumber(r[key])).filter((v): v is number => v !== null);
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

export function mitigationDelta(
  baseline: number | null,
  other: number | null,
): "improved" | "worsened" | "unchanged" | "unknown" {
  if (baseline === null || other === null) return "unknown";
  const diff = other - baseline;
  if (Math.abs(diff) < 0.005) return "unchanged";
  return diff < 0 ? "improved" : "worsened";
}

export function countByField(rows: JsonRecord[], field: string): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const row of rows) {
    const k = String(row[field] ?? "unknown");
    counts[k] = (counts[k] ?? 0) + 1;
  }
  return counts;
}
