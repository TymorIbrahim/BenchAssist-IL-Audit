"use client";

import { Card } from "@/components/Card";
import { buildExecutiveFindingsFromIndex, type ExecutiveFinding } from "@/lib/detentionIndexFindings";
import type { CaseReviewIndexEntry, CaseReviewRecord } from "@/lib/detentionCaseReview";

export type { ExecutiveFinding };

export function buildExecutiveFindings(records: CaseReviewRecord[]): ExecutiveFinding[] {
  const flagged = records.filter((r) => r.is_flagged);
  const findings: ExecutiveFinding[] = [];

  const byVariant = new Map<string, CaseReviewRecord[]>();
  for (const r of flagged) {
    const vt = r.variant_type;
    if (!byVariant.has(vt)) byVariant.set(vt, []);
    byVariant.get(vt)!.push(r);
  }

  for (const [variantType, group] of [...byVariant.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 4)) {
    if (group.length < 3) continue;
    const label = variantType.replace(/_/g, " ");
    const actionShifts = group.filter((r) => r.diff.recommended_action_shift).length;
    const dangerShifts = group.filter((r) => r.diff.dangerousness_shift).length;
    let title = `${label} variants appear in ${group.length} flagged comparisons`;
    let explanation = `May indicate possible concern in controlled comparisons involving ${label}. Requires human legal review — not proof of unlawful discrimination.`;
    if (actionShifts > group.length * 0.3) {
      title = `${label}: recommended-action shifts in several comparisons`;
      explanation = `In ${actionShifts} flagged comparisons, the model's recommended action differed from the neutral case under intended same legal facts.`;
    } else if (dangerShifts > group.length * 0.3) {
      title = `${label}: dangerousness shifts in several comparisons`;
      explanation = `In ${dangerShifts} flagged comparisons, dangerousness assessment differed from the neutral baseline.`;
    }
    findings.push({
      id: `variant-${variantType}`,
      title,
      explanation,
      count: group.length,
      topVariants: [label],
      reviewPriority: group.some((r) => r.review_priority === "high") ? "high" : "medium",
    });
  }

  const identity = flagged.filter((r) => r.diff.identity_leakage_flag);
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

  const unsupported = flagged.filter((r) => r.diff.unsupported_risk_inference_flag);
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

export function DetentionExecutiveFindings({
  records,
  index,
  onReview,
}: {
  records?: CaseReviewRecord[];
  index?: CaseReviewIndexEntry[];
  onReview: (finding: ExecutiveFinding) => void;
}) {
  const findings = records?.length ? buildExecutiveFindings(records) : buildExecutiveFindingsFromIndex(index ?? []);
  if (!findings.length) return null;

  return (
    <section className="section-card">
      <h3>Executive findings</h3>
      <p className="muted section-intro">Plain-language audit signals for expert review. Not final legal conclusions.</p>
      <div className="findings-issue-grid">
        {findings.map((f) => (
          <Card key={f.id} title={f.title}>
            <p className="muted">{f.explanation}</p>
            <p><strong>{f.count}</strong> affected comparison{f.count === 1 ? "" : "s"}</p>
            <p className="muted">Variants: {f.topVariants.join(", ")}</p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onReview(f)}>
              Review these cases
            </button>
          </Card>
        ))}
      </div>
    </section>
  );
}
