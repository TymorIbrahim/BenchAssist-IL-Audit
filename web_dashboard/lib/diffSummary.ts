import { str, toBool } from "./format";
import type { JsonRecord } from "./types";

export interface DiffRow {
  field: string;
  neutral: string;
  variant: string;
  changed: boolean;
  summary: string;
}

const KEYWORDS = ["evidence", "proof", "credibility", "identity", "urgent", "urgency", "Arab", "Hebrew", "immigrant", "skeptic"];

export function buildDiffSummary(row: JsonRecord): DiffRow[] {
  const specs: [string, string, string][] = [
    ["Recommended action", "neutral_recommended_action_type", "variant_recommended_action_type"],
    ["Urgency", "neutral_urgency_score", "variant_urgency_score"],
    ["Remedy strength", "neutral_remedy_strength_score", "variant_remedy_strength_score"],
    ["Evidence burden", "neutral_evidence_burden_score", "variant_evidence_burden_score"],
    ["Credibility", "neutral_credibility_skepticism_score", "variant_credibility_skepticism_score"],
    ["Rights orientation", "neutral_rights_orientation_score", "variant_rights_orientation_score"],
    ["Procedural posture", "neutral_procedural_posture_score", "variant_procedural_posture_score"],
  ];

  return specs.map(([label, nk, vk]) => {
    const neutral = str(row[nk]);
    const variant = str(row[vk]);
    const changed = neutral !== variant && Boolean(neutral || variant);
    let summary = "unchanged";
    if (changed) summary = `${neutral || "—"} → ${variant || "—"}`;
    if (label === "Recommended action" && toBool(row.action_type_flip)) summary = "changed";
    return { field: label, neutral: neutral || "—", variant: variant || "—", changed, summary };
  });
}

export function highlightKeywords(text: string): string[] {
  const lower = text.toLowerCase();
  return KEYWORDS.filter((k) => lower.includes(k.toLowerCase()));
}

export function reasoningDiffNotes(row: JsonRecord): { neutralHits: string[]; variantHits: string[] } {
  return {
    neutralHits: highlightKeywords(str(row.neutral_reasoning_text)),
    variantHits: highlightKeywords(str(row.reasoning_text ?? row.variant_reasoning_text)),
  };
}
