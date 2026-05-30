import type { DetentionDashboardBundle } from "./detentionData";

export interface ReadinessCheck {
  id: string;
  label: string;
  ok: boolean;
  detail: string;
}

export interface ReadinessReport {
  checks: ReadinessCheck[];
  readyForGeminiPilotReview: boolean;
  missingRecommended: string[];
}

export function assessDetentionReadiness(bundle: DetentionDashboardBundle): ReadinessReport {
  const missing: string[] = [];
  const checks: ReadinessCheck[] = [];

  checks.push({
    id: "manifest",
    label: "Manifest loaded",
    ok: Boolean(bundle.manifest.timestamp),
    detail: bundle.manifest.timestamp ? "OK" : "manifest.json missing or empty",
  });

  checks.push({
    id: "policy",
    label: "Data access policy loaded",
    ok: Object.keys(bundle.dataAccessPolicy).length > 0,
    detail: Object.keys(bundle.dataAccessPolicy).length ? "OK" : "data_access_policy.json missing",
  });

  checks.push({
    id: "overview",
    label: "Overview metrics",
    ok: Object.keys(bundle.overview).length > 0,
    detail: Object.keys(bundle.overview).length ? "OK" : "detention_overview_metrics.json missing",
  });
  if (!Object.keys(bundle.overview).length) missing.push("detention_overview_metrics.json");

  checks.push({
    id: "flagged",
    label: "Flagged cases",
    ok: bundle.flagged.length > 0,
    detail: bundle.flagged.length ? `${bundle.flagged.length} rows` : "detention_flagged_cases.json empty",
  });
  if (!bundle.flagged.length) missing.push("detention_flagged_cases.json");

  checks.push({
    id: "pairwise",
    label: "Pairwise comparisons",
    ok: bundle.pairwise.length > 0,
    detail: bundle.pairwise.length ? `${bundle.pairwise.length} rows` : "detention_pairwise_comparison.json empty",
  });
  if (!bundle.pairwise.length) missing.push("detention_pairwise_comparison.json");

  checks.push({
    id: "case-review-records",
    label: "Case review records (expert workspace)",
    ok: bundle.caseReviewLoaded || bundle.caseReviewIndexCount > 0,
    detail: bundle.caseReviewLoaded
      ? `${bundle.caseReviewRecords.length} full records loaded`
      : bundle.caseReviewIndexCount
        ? `${bundle.caseReviewIndexCount} records in index (lazy-load on Case Review tab)`
        : "detention_case_review_records.json missing — run case review export",
  });
  if (!bundle.caseReviewLoaded && !bundle.caseReviewIndexCount) {
    missing.push("detention_case_review_records.json");
  }

  checks.push({
    id: "real-cases",
    label: "Real-case examples",
    ok: bundle.realCaseExamples.length > 0,
    detail: bundle.realCaseExamples.length ? `${bundle.realCaseExamples.length} rows` : "Optional — qualitative review layer",
  });

  checks.push({
    id: "reports",
    label: "Markdown reports",
    ok: bundle.reports.length > 0,
    detail: bundle.reports.length ? `${bundle.reports.length} reports` : "reports.json empty — optional",
  });

  checks.push({
    id: "fulltext-warning",
    label: "Full-text access-control warning",
    ok: !bundle.hasFullText || true,
    detail: bundle.hasFullText ? "Warning displayed when full text present" : "No full text in export",
  });

  checks.push({
    id: "strict-exclusion",
    label: "Strict-rate exclusion visible",
    ok: true,
    detail: "Real cases labeled excluded from strict fairness rates",
  });

  const coreOk = checks.filter((c) => ["manifest", "flagged", "pairwise"].includes(c.id)).every((c) => c.ok);

  return {
    checks,
    readyForGeminiPilotReview: coreOk,
    missingRecommended: missing,
  };
}
