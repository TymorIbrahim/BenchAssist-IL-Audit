import { issueGroupsForSchema, type CaseReviewIndexEntry } from "./detentionCaseReview";

export interface ExecutiveFinding {
  id: string;
  title: string;
  explanation: string;
  count: number;
  topVariants: string[];
  reviewPriority: string;
  analysisBucket?: "strict_demographic" | "address_proxy";
}

function bucketOf(entry: CaseReviewIndexEntry): "strict_demographic" | "address_proxy" {
  return entry.analysis_bucket === "address_proxy" ? "address_proxy" : "strict_demographic";
}

function variantRollups(flagged: CaseReviewIndexEntry[], bucket: "strict_demographic" | "address_proxy"): ExecutiveFinding[] {
  const scoped = flagged.filter((e) => bucketOf(e) === bucket);
  const findings: ExecutiveFinding[] = [];
  const byVariant = new Map<string, CaseReviewIndexEntry[]>();
  for (const e of scoped) {
    if (!byVariant.has(e.variant_type)) byVariant.set(e.variant_type, []);
    byVariant.get(e.variant_type)!.push(e);
  }
  for (const [variantType, group] of [...byVariant.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 3)) {
    if (group.length < 2) continue;
    const label = variantType.replace(/_/g, " ");
    findings.push({
      id: `${bucket}-variant-${variantType}`,
      title: `${label}: ${group.length} flagged (${bucket === "address_proxy" ? "address-proxy" : "strict"})`,
      explanation:
        bucket === "address_proxy"
          ? "Address-proxy bucket only — not comparable to strict demographic headline rates."
          : "Strict demographic counterfactual bucket — primary minimal-schema audit lane.",
      count: group.length,
      topVariants: [label],
      reviewPriority: group.some((r) => r.review_priority === "high") ? "high" : "medium",
      analysisBucket: bucket,
    });
  }
  return findings;
}

export function buildExecutiveFindingsFromIndex(
  index: CaseReviewIndexEntry[],
  schemaVersion?: string | null,
): ExecutiveFinding[] {
  const flagged = index.filter((e) => e.is_flagged);
  const minimal = issueGroupsForSchema(schemaVersion).length === 1;
  const findings: ExecutiveFinding[] = [];

  const strictFlagged = flagged.filter((e) => bucketOf(e) === "strict_demographic");
  const addressFlagged = flagged.filter((e) => bucketOf(e) === "address_proxy");

  if (strictFlagged.length) {
    findings.push({
      id: "strict-bucket-rollups",
      title: `Strict demographic: ${strictFlagged.length} flagged dangerousness shifts`,
      explanation:
        "Headline strict fairness audit (baseline prompt mode). Dangerousness_level change only — requires human legal review.",
      count: strictFlagged.length,
      topVariants: [],
      reviewPriority: strictFlagged.some((r) => r.review_priority === "high") ? "high" : "medium",
      analysisBucket: "strict_demographic",
    });
  }
  if (addressFlagged.length) {
    findings.push({
      id: "address-bucket-rollups",
      title: `Address-proxy: ${addressFlagged.length} flagged dangerousness shifts`,
      explanation:
        "Separate proxy-cautious lane — excluded from strict demographic headline rates. Not proof of individual identity.",
      count: addressFlagged.length,
      topVariants: [],
      reviewPriority: addressFlagged.some((r) => r.review_priority === "high") ? "high" : "medium",
      analysisBucket: "address_proxy",
    });
  }

  findings.push(...variantRollups(flagged, "strict_demographic"));
  findings.push(...variantRollups(flagged, "address_proxy"));

  if (!minimal) {
    const identity = flagged.filter((e) => e.issue_flags?.identity);
    if (identity.length) {
      findings.push({
        id: "identity-leakage",
        title: "Identity/proxy language may appear in model reasoning",
        explanation: `${identity.length} comparison(s) with informational identity/proxy wording in reasoning.`,
        count: identity.length,
        topVariants: [...new Set(identity.slice(0, 5).map((r) => r.variant_type.replace(/_/g, " ")))],
        reviewPriority: "low",
      });
    }
  }

  return findings.slice(0, 8);
}

export function groupIndexByIssue(
  index: CaseReviewIndexEntry[],
  schemaVersion?: string | null,
): {
  key: string;
  label: string;
  explanation: string;
  recordIds: string[];
  variantTypes: string[];
}[] {
  const flagged = index.filter((e) => e.is_flagged);
  const groups = issueGroupsForSchema(schemaVersion).map((g) => ({
    key: g.key,
    label: g.label,
    explanation: g.explanation,
    match: (e: CaseReviewIndexEntry) => Boolean(e.issue_flags?.[g.key as keyof typeof e.issue_flags]),
  }));

  return groups
    .map((g) => {
      const matched = flagged.filter((e) => g.match(e));
      return {
        key: g.key,
        label: g.label,
        explanation: g.explanation,
        recordIds: matched.map((e) => e.review_record_id),
        variantTypes: [...new Set(matched.map((e) => e.variant_type.replace(/_/g, " ")))],
      };
    })
    .filter((g) => g.recordIds.length > 0);
}
