import { ISSUE_EXPLANATIONS, type CaseReviewIndexEntry } from "./detentionCaseReview";

export interface ExecutiveFinding {
  id: string;
  title: string;
  explanation: string;
  count: number;
  topVariants: string[];
  reviewPriority: string;
}

export function buildExecutiveFindingsFromIndex(index: CaseReviewIndexEntry[]): ExecutiveFinding[] {
  const flagged = index.filter((e) => e.is_flagged);
  const findings: ExecutiveFinding[] = [];

  const byVariant = new Map<string, CaseReviewIndexEntry[]>();
  for (const e of flagged) {
    if (!byVariant.has(e.variant_type)) byVariant.set(e.variant_type, []);
    byVariant.get(e.variant_type)!.push(e);
  }

  for (const [variantType, group] of [...byVariant.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 4)) {
    if (group.length < 3) continue;
    const label = variantType.replace(/_/g, " ");
    findings.push({
      id: `variant-${variantType}`,
      title: `${label} variants appear in ${group.length} flagged comparisons`,
      explanation: `May indicate possible concern in controlled comparisons involving ${label}. Requires human legal review — not proof of unlawful discrimination.`,
      count: group.length,
      topVariants: [label],
      reviewPriority: group.some((r) => r.review_priority === "high") ? "high" : "medium",
    });
  }

  const identity = flagged.filter((e) => e.issue_flags?.identity);
  if (identity.length) {
    findings.push({
      id: "identity-leakage",
      title: "Identity/proxy language may appear in model reasoning",
      explanation: `${identity.length} comparison(s) flagged where identity, language, or proxy cues may have entered reasoning text.`,
      count: identity.length,
      topVariants: [...new Set(identity.slice(0, 5).map((r) => r.variant_type.replace(/_/g, " ")))],
      reviewPriority: "high",
    });
  }

  const unsupported = flagged.filter((e) => e.issue_flags?.unsupported);
  if (unsupported.length) {
    findings.push({
      id: "unsupported-inference",
      title: "Possible unsupported risk inferences detected",
      explanation: `${unsupported.length} comparison(s) flagged where risk assessments may not be fully supported by stated legal facts.`,
      count: unsupported.length,
      topVariants: [...new Set(unsupported.slice(0, 5).map((r) => r.variant_type.replace(/_/g, " ")))],
      reviewPriority: "high",
    });
  }

  return findings.slice(0, 6);
}

export function groupIndexByIssue(index: CaseReviewIndexEntry[]): {
  key: string;
  label: string;
  explanation: string;
  recordIds: string[];
  variantTypes: string[];
}[] {
  const flagged = index.filter((e) => e.is_flagged);
  const groups: { key: string; label: string; explanation: string; match: (e: CaseReviewIndexEntry) => boolean }[] = [
    { key: "dangerousness", label: "Dangerousness shifts", explanation: ISSUE_EXPLANATIONS.dangerousness, match: (e) => Boolean(e.issue_flags?.dangerousness) },
    { key: "obstruction", label: "Obstruction-risk shifts", explanation: ISSUE_EXPLANATIONS.obstruction, match: (e) => Boolean(e.issue_flags?.obstruction) },
    { key: "recommended_action", label: "Recommended-action shifts", explanation: ISSUE_EXPLANATIONS.recommended_action, match: (e) => Boolean(e.issue_flags?.recommended_action) },
    { key: "duration", label: "Detention-duration shifts", explanation: ISSUE_EXPLANATIONS.duration, match: (e) => Boolean(e.issue_flags?.duration) },
    { key: "alternatives", label: "Omitted alternatives", explanation: ISSUE_EXPLANATIONS.alternatives, match: (e) => Boolean(e.issue_flags?.alternatives) },
    { key: "safeguards", label: "Omitted safeguards", explanation: ISSUE_EXPLANATIONS.safeguards, match: (e) => Boolean(e.issue_flags?.safeguards) },
    { key: "identity", label: "Identity/proxy leakage", explanation: ISSUE_EXPLANATIONS.identity, match: (e) => Boolean(e.issue_flags?.identity) },
    { key: "unsupported", label: "Unsupported risk inference", explanation: ISSUE_EXPLANATIONS.unsupported, match: (e) => Boolean(e.issue_flags?.unsupported) },
  ];

  return groups
    .map((g) => {
      const matched = flagged.filter(g.match);
      return {
        key: g.key,
        label: g.label,
        explanation: g.explanation,
        recordIds: matched.map((e) => e.review_record_id),
        variantTypes: [...new Set(matched.slice(0, 5).map((e) => e.variant_type.replace(/_/g, " ")))],
      };
    })
    .filter((g) => g.recordIds.length > 0);
}
