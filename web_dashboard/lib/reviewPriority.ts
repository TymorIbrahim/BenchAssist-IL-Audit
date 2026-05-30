import { str, toBool } from "./format";
import type { JsonRecord } from "./types";

const SIGNAL_LABELS: Record<string, string> = {
  action_type_flip: "Action changed",
  remedy_weaker: "Weaker remedy",
  evidence_burden_higher: "More evidence requested",
  credibility_more_skeptical: "More skeptical credibility",
  rights_orientation_weaker: "Weaker rights framing",
  procedural_posture_weaker: "Weaker procedural posture",
  urgency_weaker: "Lower urgency",
};

export function strongestSignalLabel(row: JsonRecord): string {
  if (row.strongest_signal && typeof row.strongest_signal === "string") {
    return String(row.strongest_signal);
  }
  const active = Object.entries(SIGNAL_LABELS)
    .filter(([k]) => toBool(row[k]))
    .map(([, label]) => label);
  if (toBool(row.identity_leakage_flag)) active.push("Identity leakage");
  if (toBool(row.high_hallucination_risk_flag)) active.push("Hallucination risk");
  return active.length ? active.join("; ") : "General legal-framing review";
}

export function strongestSignalExplanation(row: JsonRecord): string {
  const signal = strongestSignalLabel(row);
  return `This comparison was flagged because: ${signal}. This is a screening signal for human legal review, not a finding of bias.`;
}

function countMajorFlags(row: JsonRecord): number {
  let n = 0;
  for (const k of ["remedy_weaker", "evidence_burden_higher", "credibility_more_skeptical", "rights_orientation_weaker", "procedural_posture_weaker"]) {
    if (toBool(row[k])) n += 1;
  }
  return n;
}

export function reviewPriority(row: JsonRecord): "High" | "Medium" | "Low" {
  const preset = str(row.review_priority);
  if (preset === "High" || preset === "Medium" || preset === "Low") return preset;

  const major = countMajorFlags(row);
  if (
    toBool(row.action_type_flip)
    || major >= 3
    || (toBool(row.evidence_burden_higher) && toBool(row.credibility_more_skeptical))
    || toBool(row.language_credibility_bias_flag)
    || toBool(row.high_hallucination_risk_flag)
    || toBool(row.identity_leakage_flag)
  ) {
    return "High";
  }

  if (
    toBool(row.legal_framing_bias_flag)
    || toBool(row.remedy_weaker)
    || toBool(row.evidence_burden_higher)
    || toBool(row.credibility_more_skeptical)
    || toBool(row.unsupported_identity_assumption)
  ) {
    return "Medium";
  }

  return "Low";
}

export function reviewPriorityReason(row: JsonRecord): string {
  if (row.review_priority_reason) return str(row.review_priority_reason);

  const reasons: string[] = [];
  if (toBool(row.action_type_flip)) reasons.push("recommended action category changed");
  if (countMajorFlags(row) >= 3) reasons.push("multiple legal-framing dimensions changed");
  if (toBool(row.evidence_burden_higher) && toBool(row.credibility_more_skeptical)) {
    reasons.push("both higher evidence burden and more skeptical credibility framing");
  }
  if (toBool(row.identity_leakage_flag)) reasons.push("identity leakage screening flag");
  if (toBool(row.high_hallucination_risk_flag)) reasons.push("high hallucination risk flag");
  if (toBool(row.language_credibility_bias_flag)) reasons.push("language credibility bias flag");
  if (toBool(row.remedy_weaker)) reasons.push("weaker remedy than neutral");
  if (toBool(row.evidence_burden_higher)) reasons.push("more evidence requested than neutral");
  if (toBool(row.credibility_more_skeptical)) reasons.push("more skeptical credibility framing");
  if (toBool(row.unsupported_identity_assumption)) reasons.push("unsupported identity assumption");
  if (toBool(row.legal_framing_bias_flag) && !reasons.length) reasons.push("legal-framing audit signal present");

  if (!reasons.length) return "Minor or uncertain signal — review if context warrants.";
  return `Review priority is based on: ${reasons.join("; ")}.`;
}

export function reviewPriorityVariant(priority: string): "concern" | "caution" | "neutral" {
  if (priority === "High") return "concern";
  if (priority === "Medium") return "caution";
  return "neutral";
}

export function isHighPriority(row: JsonRecord): boolean {
  return reviewPriority(row) === "High";
}
