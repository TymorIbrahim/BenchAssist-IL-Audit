import { reviewPriority, reviewPriorityReason, strongestSignalLabel } from "./reviewPriority";
import { str, toBool } from "./format";
import type { DashboardData, JsonRecord } from "./types";

export interface CaseContext {
  caseId: string;
  variantId: string;
  pairwise: JsonRecord | null;
  flagged: JsonRecord | null;
  validity: JsonRecord | null;
  stereotype: JsonRecord | null;
  hallucination: JsonRecord | null;
  qualitative: JsonRecord | null;
  humanReview: JsonRecord | null;
  reviewPriority: "High" | "Medium" | "Low";
  reviewPriorityReason: string;
  strongestSignal: string;
  linkedCaseKey: string;
}

export interface CaseBadge {
  label: string;
  variant: "info" | "caution" | "concern" | "success" | "neutral";
}

function matchCaseVariant(row: JsonRecord, caseId: string, variantId: string): boolean {
  return str(row.case_id) === caseId && (str(row.variant_id) === variantId || str(row.variant_type) === variantId);
}

export function getCaseContext(caseId: string, variantId: string, data: DashboardData): CaseContext {
  const pairwise = data.pairwise.find((r) => matchCaseVariant(r, caseId, variantId)) ?? null;
  const flagged = data.flagged.find((r) => matchCaseVariant(r, caseId, variantId))
    ?? (pairwise && toBool(pairwise.legal_framing_bias_flag) ? pairwise : null);
  const validity = data.validity.find((r) => matchCaseVariant(r, caseId, variantId)) ?? null;
  const stereotype = data.stereotypeExamples.find((r) => str(r.case_id) === caseId) ?? null;
  const hallucination = data.hallucinationPer.find((r) => str(r.case_id) === caseId && str(r.variant_id) === variantId)
    ?? data.hallucinationPer.find((r) => str(r.case_id) === caseId) ?? null;
  const qualitative = data.qualitative.find((r) => matchCaseVariant(r, caseId, variantId)) ?? null;
  const humanReview = data.humanReview.find((r) => str(r.case_id) === caseId) ?? null;

  const base = flagged ?? pairwise ?? {};
  const priority = reviewPriority(base);
  return {
    caseId,
    variantId,
    pairwise,
    flagged,
    validity,
    stereotype,
    hallucination,
    qualitative,
    humanReview,
    reviewPriority: priority,
    reviewPriorityReason: reviewPriorityReason(base),
    strongestSignal: strongestSignalLabel(base),
    linkedCaseKey: `${caseId}::${variantId}`,
  };
}

export function getRelatedRows(caseId: string, variantId: string, data: DashboardData): JsonRecord[] {
  const ctx = getCaseContext(caseId, variantId, data);
  return [ctx.pairwise, ctx.flagged, ctx.validity, ctx.stereotype, ctx.hallucination, ctx.qualitative, ctx.humanReview].filter(Boolean) as JsonRecord[];
}

export function getCaseBadges(context: CaseContext): CaseBadge[] {
  const badges: CaseBadge[] = [];
  if (toBool(context.flagged?.legal_framing_bias_flag) || toBool(context.pairwise?.legal_framing_bias_flag)) {
    badges.push({ label: "Legal-framing signal", variant: "caution" });
  }
  const vc = str(context.validity?.validity_category);
  if (vc) badges.push({ label: vc.replace(/_/g, " "), variant: "info" });
  if (vc.includes("strict")) badges.push({ label: "Direct-bias eligible", variant: "success" });
  if (vc.includes("cautious") || vc.includes("needs_human")) badges.push({ label: "Cautious interpretation", variant: "caution" });
  if (context.stereotype) badges.push({ label: "Identity leakage flag", variant: "caution" });
  if (context.hallucination && toBool(context.hallucination.high_hallucination_risk_flag)) {
    badges.push({ label: "Hallucination risk", variant: "concern" });
  }
  if (context.qualitative) badges.push({ label: "Qualitative review available", variant: "info" });
  if (context.humanReview) badges.push({ label: "Human-review row available", variant: "info" });
  badges.push({ label: `${context.reviewPriority} review priority`, variant: context.reviewPriority === "High" ? "concern" : context.reviewPriority === "Medium" ? "caution" : "neutral" });
  return badges;
}

export function issueTagsFromRow(row: JsonRecord): string[] {
  const tags: string[] = [];
  if (toBool(row.remedy_weaker)) tags.push("weaker_remedy");
  if (toBool(row.evidence_burden_higher)) tags.push("higher_evidence_burden");
  if (toBool(row.credibility_more_skeptical)) tags.push("skeptical_credibility");
  if (toBool(row.rights_orientation_weaker)) tags.push("weaker_rights_framing");
  if (toBool(row.action_type_flip)) tags.push("action_changed");
  return tags;
}
