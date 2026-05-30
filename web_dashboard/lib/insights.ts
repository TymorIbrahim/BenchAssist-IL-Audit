import { reviewPriority, reviewPriorityReason } from "./reviewPriority";
import { str, toBool, toNumber } from "./format";
import type { DashboardData, JsonRecord } from "./types";

export interface InsightCard {
  id: string;
  text: string;
  caution?: string;
  requiresReview?: boolean;
}

function topVariantByMetric(groupSummary: JsonRecord[], metricKey: string): JsonRecord | null {
  const rows = groupSummary.filter((r) => str(r.variant_type) !== "neutral_he");
  if (!rows.length) return null;
  return rows.reduce((best, row) => {
    const v = toNumber(row[metricKey]) ?? 0;
    const b = toNumber(best[metricKey]) ?? 0;
    return v > b ? row : best;
  }, rows[0]);
}

export function generateKeyTakeaways(data: DashboardData): InsightCard[] {
  const takeaways: InsightCard[] = [];
  const { overview, manifest, groupSummary, validitySummary, hallucinationGroup, flagged } = data;

  const flaggedCount = overview.total_flagged_cases ?? flagged.length;
  if (flaggedCount > 0) {
    takeaways.push({
      id: "tk-flagged",
      text: `The audit flagged ${flaggedCount} comparison${flaggedCount === 1 ? "" : "s"} for human legal review in this export.`,
      requiresReview: true,
      caution: "Flagged means worth inspecting — not proof of bias or unlawful discrimination.",
    });
  } else {
    takeaways.push({
      id: "tk-flagged-none",
      text: "No flagged comparisons were exported in this run, or the count is not available.",
    });
  }

  const topFraming = topVariantByMetric(groupSummary, "legal_framing_bias_flag_rate");
  if (topFraming) {
    const vt = str(topFraming.variant_type).replace(/_/g, " ");
    const rate = toNumber(topFraming.legal_framing_bias_flag_rate);
    if (rate !== null && rate > 0) {
      takeaways.push({
        id: "tk-top-variant",
        text: `The strongest aggregate legal-framing audit signal in this run appears in “${vt}” variants (${(rate <= 1 ? rate * 100 : rate).toFixed(1)}% screening rate). Manual review is recommended.`,
        requiresReview: true,
      });
    }
  }

  const cautious = validitySummary.filter((r) => {
    const c = str(r.validity_category).toLowerCase();
    return c.includes("cautious") || c.includes("stress") || c.includes("needs_human");
  }).length;
  if (cautious > 0) {
    takeaways.push({
      id: "tk-validity",
      text: "Some variants require cautious interpretation because facts or vulnerability cues may be legally relevant, or the variant is not a strict counterfactual.",
      requiresReview: true,
    });
  }

  if (hallucinationGroup.length) {
    const rates = hallucinationGroup.map((r) => toNumber(r.high_hallucination_risk_rate)).filter((v): v is number => v !== null);
    if (rates.length) {
      const max = Math.max(...rates);
      const level = max < 0.05 ? "relatively low" : max < 0.15 ? "moderate" : "elevated";
      takeaways.push({
        id: "tk-hallucination",
        text: `Grounded-mode outputs in this export show ${level} high-hallucination-risk rates in aggregate.`,
        caution: "Grounding checks are separate from fairness audit signals.",
      });
    }
  } else {
    takeaways.push({
      id: "tk-hallucination-na",
      text: "Hallucination / grounding summary: not available in this exported run.",
    });
  }

  takeaways.push({
    id: "tk-uncertainty",
    text: "Statistical uncertainty and small sample size matter. These results are screening signals for human review — not proof of unlawful discrimination.",
    caution: "Treat aggregate rates as exploratory unless validated with legal expertise.",
  });

  if (manifest.cross_prompt_comparisons_available) {
    takeaways.push({
      id: "tk-mitigation",
      text: `Cross-prompt comparison data is available (${manifest.cross_prompt_comparison_row_count ?? 0} rows). You can compare baseline, fairness-aware, and demographic-blind memos for the same case.`,
    });
  }

  return takeaways.slice(0, 6);
}

export function generateInsights(data: DashboardData): InsightCard[] {
  const insights: InsightCard[] = [];
  const { overview, manifest, groupSummary, mitigation, validitySummary, hallucinationGroup } = data;

  if (overview.base_cases != null) {
    insights.push({
      id: "base-cases",
      text: `This exported run includes ${overview.base_cases} synthetic base housing scenarios.`,
    });
  }

  const topEvidence = topVariantByMetric(groupSummary, "evidence_burden_higher_rate");
  if (topEvidence) {
    const vt = str(topEvidence.variant_type).replace(/_/g, " ");
    const rate = toNumber(topEvidence.evidence_burden_higher_rate);
    if (rate !== null && rate > 0) {
      insights.push({
        id: "top-evidence",
        text: `The “${vt}” variant type shows the highest “more evidence requested” signal rate in this run (${(rate <= 1 ? rate * 100 : rate).toFixed(1)}%).`,
        caution: "Screening signal only — requires human legal review.",
        requiresReview: true,
      });
    }
  }

  const topFraming = topVariantByMetric(groupSummary, "legal_framing_bias_flag_rate");
  if (topFraming) {
    const vt = str(topFraming.variant_type).replace(/_/g, " ");
    const rate = toNumber(topFraming.legal_framing_bias_flag_rate);
    if (rate !== null && rate > 0) {
      insights.push({
        id: "top-framing",
        text: `“${vt}” variants produced the most legal-framing audit signals in aggregate (${(rate <= 1 ? rate * 100 : rate).toFixed(1)}%).`,
        requiresReview: true,
      });
    }
  }

  if (overview.total_flagged_cases != null && overview.total_flagged_cases > 0) {
    insights.push({
      id: "flagged-count",
      text: `${overview.total_flagged_cases} case comparisons were flagged for human legal review in this export.`,
      requiresReview: true,
    });
  }

  if (mitigation.length) {
    const improved = mitigation.filter((r) => {
      const d = toNumber(r.delta_legal_framing_bias_flag_rate);
      return d !== null && d < 0;
    }).length;
    if (improved > 0) {
      insights.push({
        id: "mitigation-improved",
        text: `Fairness-aware prompting reduced legal-framing signal rates for ${improved} variant type(s) compared with baseline in the mitigation table.`,
        caution: "Mitigation may help one metric while affecting others.",
      });
    }
  }

  const cautious = validitySummary.filter((r) => {
    const c = str(r.validity_category).toLowerCase();
    return c.includes("cautious") || c.includes("stress") || c.includes("needs_human");
  });
  if (cautious.length) {
    insights.push({
      id: "validity-cautious",
      text: "Several flagged comparisons may require cautious interpretation because not all variants are strict counterfactuals.",
      requiresReview: true,
    });
  }

  if (hallucinationGroup.length) {
    const high = hallucinationGroup.map((r) => toNumber(r.high_hallucination_risk_rate)).filter((v): v is number => v !== null);
    if (high.length && Math.max(...high) < 0.05) {
      insights.push({
        id: "hallucination-low",
        text: "Grounded-mode outputs in this export show relatively low high-hallucination-risk rates in aggregate.",
        caution: "Does not certify legal correctness under Israeli law.",
      });
    }
  }

  const runType = str(manifest.run_type);
  if (runType.includes("pilot") || (overview.base_cases != null && overview.base_cases <= 20)) {
    insights.push({
      id: "small-sample",
      text: "Sample size may be limited in this run; interpret statistical and aggregate signals cautiously.",
      caution: "Multiple comparisons can produce exploratory false positives.",
    });
  }

  if (!insights.length) {
    insights.push({
      id: "none",
      text: "Insight cards are not available for this exported run. Review Main Findings and Flagged Cases directly.",
    });
  }

  return insights;
}

export function priorityInsightsForRow(row: JsonRecord): string {
  return reviewPriorityReason(row);
}

export function topFlaggedExamples(flagged: JsonRecord[], n = 3): JsonRecord[] {
  const sorted = [...flagged].sort((a, b) => {
    const order = { High: 0, Medium: 1, Low: 2 };
    return (order[reviewPriority(a)] ?? 3) - (order[reviewPriority(b)] ?? 3);
  });
  return sorted.slice(0, n);
}
