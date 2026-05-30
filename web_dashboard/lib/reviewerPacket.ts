import { getCaseContext, type CaseContext } from "./caseContext";
import { strongestSignalExplanation } from "./reviewPriority";
import { str } from "./format";
import type { DashboardData } from "./types";

const DISCLAIMER = `> Research audit packet. Not legal advice. Not an AI judge. Synthetic toy audit setting. Human legal review required. Metrics are screening signals, not proof of unlawful discrimination.

`;

export function generateReviewerPacket(context: CaseContext, data: DashboardData): string {
  const row = context.pairwise ?? context.flagged ?? {};
  const timestamp = data.manifest.timestamp || "Not available in exported data";
  const neutralInput = str(row.neutral_input_text || row.input_text) || "Not available in exported data.";
  const variantInput = str(row.variant_input_text || row.input_text) || "Not available in exported data.";

  const lines: string[] = [
    DISCLAIMER,
    `# Review packet: ${context.caseId} / ${context.variantId}`,
    "",
    `- **Export timestamp:** ${timestamp}`,
    "",
    "## Case metadata",
    `- **Case ID:** ${context.caseId}`,
    `- **Variant ID:** ${context.variantId}`,
    `- **Variant type:** ${str(row.variant_type) || "Not available"}`,
    `- **Demographic cue:** ${str(row.demographic_cue) || "Not available"}`,
    `- **Review priority:** ${context.reviewPriority}`,
    `- **Strongest signal:** ${context.strongestSignal}`,
    "",
    "## Why this priority?",
    context.reviewPriorityReason,
    "",
    "## Strongest signal explanation",
    strongestSignalExplanation(row),
    "",
    "## Input texts",
    "### Neutral input",
    neutralInput.slice(0, 2000),
    "",
    "### Variant input",
    variantInput.slice(0, 2000),
    "",
    "## Neutral memo (structured fields)",
    `- Action: ${str(row.neutral_recommended_action_type) || "—"}`,
    `- Urgency: ${str(row.neutral_urgency_score ?? row.neutral_urgency) || "—"}`,
    `- Remedy strength: ${str(row.neutral_remedy_strength_score) || "—"}`,
    `- Evidence burden: ${str(row.neutral_evidence_burden_score) || "—"}`,
    `- Credibility: ${str(row.neutral_credibility_skepticism_score) || "—"}`,
    `- Reasoning: ${str(row.neutral_reasoning_text).slice(0, 1500) || "Not available"}`,
    "",
    "## Variant memo (structured fields)",
    `- Action: ${str(row.variant_recommended_action_type) || "—"}`,
    `- Urgency: ${str(row.variant_urgency_score ?? row.variant_urgency) || "—"}`,
    `- Remedy strength: ${str(row.variant_remedy_strength_score) || "—"}`,
    `- Evidence burden: ${str(row.variant_evidence_burden_score) || "—"}`,
    `- Credibility: ${str(row.variant_credibility_skepticism_score) || "—"}`,
    `- Reasoning: ${str(row.reasoning_text ?? row.variant_reasoning_text).slice(0, 1500) || "Not available"}`,
    "",
    "## Structured field differences",
    `- Action changed: ${str(row.action_type_flip)}`,
    `- Urgency change: ${str(row.urgency_delta) || "—"}`,
    `- Remedy change: ${str(row.remedy_strength_delta) || "—"}`,
    `- Evidence burden change: ${str(row.evidence_burden_delta) || "—"}`,
    `- Credibility change: ${str(row.credibility_skepticism_delta) || "—"}`,
    "",
  ];

  if (context.validity) {
    lines.push("## Validity metadata", `- Category: ${str(context.validity.validity_category)}`, `- Fact preservation: ${str(context.validity.fact_preservation_score)}`, "");
  } else {
    lines.push("## Validity metadata", "Not available in exported data.", "");
  }
  if (context.stereotype) {
    lines.push("## Stereotype / identity leakage", `- Snippets: ${str(context.stereotype.flagged_snippets)}`, "");
  } else {
    lines.push("## Stereotype / identity leakage", "Not available in exported data.", "");
  }
  if (context.hallucination) {
    lines.push("## Hallucination / grounding", `- Invalid citations: ${str(context.hallucination.invalid_citations)}`, `- Unsupported claims: ${str(context.hallucination.unsupported_claims)}`, "");
  } else {
    lines.push("## Hallucination / grounding", "Not available in exported data.", "");
  }

  lines.push(
    "## Human-review questions",
    "1. Are the legal facts equivalent?",
    "2. Is the output difference legally justified?",
    "3. Did identity or language affect credibility?",
    "4. Did the model demand more evidence?",
    "5. Would this matter in a judicial workflow?",
    "",
    "## Disclaimer",
    "This packet supports human legal review only. It does not prove discrimination or legal wrongdoing.",
  );

  return lines.join("\n");
}

export function downloadReviewerPacket(context: CaseContext, data: DashboardData) {
  const md = generateReviewerPacket(context, data);
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `review_packet_${context.caseId}_${context.variantId}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export function generateBulkReviewerPacket(contexts: CaseContext[], data: DashboardData): string {
  return contexts.map((c) => generateReviewerPacket(c, data)).join("\n\n---\n\n");
}
