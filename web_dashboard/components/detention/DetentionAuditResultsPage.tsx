"use client";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatCard } from "@/components/MetricCard";
import { BarChart } from "@/components/BarChart";
import { DetentionFindingsByIssue } from "@/components/detention/DetentionFindingsByIssue";
import { DetentionFindingsByIssueIndex } from "@/components/detention/DetentionFindingsByIssueIndex";
import { DetentionIdentityAuditSection } from "@/components/detention/DetentionIdentityAuditSection";
import { DetentionVariantMatrix } from "@/components/detention/DetentionVariantMatrix";
import { DetentionExecutiveFindings, type ExecutiveFinding } from "@/components/detention/DetentionExecutiveFindings";
import { DetentionKeyTakeaways } from "@/components/detention/DetentionKeyTakeaways";
import { PageHeader } from "@/components/detention/PageHeader";
import { MetricTipLabel } from "@/components/detention/DetentionMetricTip";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import type { DetentionTakeaway } from "@/lib/detentionTakeaways";
import type { DetentionFilterState } from "@/lib/detentionFilters";
import { formatCount, formatRate, str, toBool } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export function DetentionAuditResultsPage({
  bundle,
  filteredFlagged,
  filteredPairwise,
  takeaways,
  isMock,
  onViewCases,
  onReviewIssueGroup,
  onReviewExecutiveFinding,
  onOpenVariant,
  onReviewIdentityCases,
}: {
  bundle: DetentionDashboardBundle;
  filteredFlagged: JsonRecord[];
  filteredPairwise: JsonRecord[];
  takeaways: DetentionTakeaway[];
  isMock: boolean;
  onViewCases: (t: DetentionTakeaway) => void;
  onReviewIssueGroup?: (filter: { issueKey: string; recordIds: string[] }) => void;
  onReviewExecutiveFinding?: (variantType: string) => void;
  onOpenVariant?: (caseId: string, variantId: string) => void;
  onReviewIdentityCases?: () => void;
}) {
  const identityCount = bundle.flagged.filter((r) => toBool(r.identity_leakage_flag)).length;
  const unsupportedCount = bundle.flagged.filter((r) => toBool(r.unsupported_risk_inference_flag)).length;
  const actionShifts = bundle.flagged.filter((r) => Number(r.recommended_action_type_delta) !== 0).length;
  const durationShifts = bundle.flagged.filter((r) => Number(r.recommended_duration_days_delta) !== 0).length;
  const highPriority = bundle.flagged.filter((r) => str(r.review_priority) === "High").length;

  const chartData = bundle.groupSummary.slice(0, 8).map((g) => ({
    name: str(g.variant_type).replace(/_/g, " ").slice(0, 18),
    value: Number(g.mean_dangerousness_delta) || 0,
    rawKey: str(g.variant_type),
  }));

  return (
    <div className="tab-panel">
      <PageHeader
        title="Audit Results"
        subtitle="Layered view of audit signals from the synthetic strict-fairness audit."
        note={isMock ? "Mock data — pipeline QA only, not a research finding." : undefined}
      />

      <div className="metric-grid">
        <StatCard label="Total comparisons" value={formatCount(filteredPairwise.length || bundle.pairwise.length)} sub={<MetricTipLabel tipKey="strict_fairness">Synthetic strict audit</MetricTipLabel>} />
        <StatCard label="Audit signals" value={formatCount(filteredFlagged.length)} sub="Flagged for legal review" />
        <StatCard label="High-priority items" value={formatCount(highPriority)} sub="Review priority: High" />
        <StatCard label="Identity leakage flags" value={formatCount(identityCount)} sub={<MetricTipLabel tipKey="identity_leakage">Possible proxy language</MetricTipLabel>} />
        <StatCard label="Unsupported inferences" value={formatCount(unsupportedCount)} sub={<MetricTipLabel tipKey="unsupported_inference">May need fact check</MetricTipLabel>} />
        <StatCard label="Action shifts" value={formatCount(actionShifts)} sub="Recommended action changed" />
        <StatCard label="Duration shifts" value={formatCount(durationShifts)} sub="Recommended duration changed" />
        <StatCard label="Real-case model outputs" value={formatCount(bundle.overview.n_real_case_review_outputs ?? bundle.realCaseExamples.length)} sub={`${formatCount(bundle.realCaseExamples.length)} fulltext examples for qualitative review`} />
      </div>

      <section className="section-card">
        <h3>Key takeaways</h3>
        <p className="muted section-intro">Human-readable interpretation cards — audit signals only, requires human review.</p>
        <DetentionKeyTakeaways takeaways={takeaways} onViewCases={onViewCases} />
      </section>

      <DetentionIdentityAuditSection bundle={bundle} onReviewCases={onReviewIdentityCases} />

      {(bundle.caseReviewIndex.length || bundle.caseReviewRecords.length) && onReviewExecutiveFinding ? (
        <DetentionExecutiveFindings
          records={bundle.caseReviewRecords.length ? bundle.caseReviewRecords : undefined}
          index={bundle.caseReviewIndex.length ? bundle.caseReviewIndex : undefined}
          onReview={(f: ExecutiveFinding) => {
            const variant = f.topVariants[0]?.replace(/ /g, "_") ?? "";
            onReviewExecutiveFinding(f.id.startsWith("variant-") ? f.id.replace("variant-", "") : variant);
          }}
        />
      ) : null}

      {(bundle.caseReviewIndex.length || bundle.caseReviewRecords.length) && onReviewIssueGroup ? (
        bundle.caseReviewRecords.length ? (
        <DetentionFindingsByIssue
          records={bundle.caseReviewRecords}
          onReviewCases={onReviewIssueGroup}
        />
        ) : (
        <DetentionFindingsByIssueIndex
          index={bundle.caseReviewIndex}
          onReviewCases={onReviewIssueGroup}
        />
        )
      ) : null}

      {chartData.length ? (
        <section className="section-card">
          <h3>
            <MetricTipLabel tipKey="dangerousness_shift">Mean dangerousness shift by variant</MetricTipLabel>
          </h3>
          <BarChart
            data={chartData}
            ariaLabel="Mean dangerousness shift by variant type"
            valueFormat="delta"
            valueLabel="Mean shift"
          />
          <p className="muted chart-caption">Exploratory screening — may indicate possible concern. Not proof of unlawful discrimination.</p>
        </section>
      ) : null}

      {bundle.pairwise.length ? (
        <DetentionVariantMatrix bundle={bundle} onSelectVariant={onOpenVariant} />
      ) : null}

      {bundle.groupSummary.length ? (
        <section className="section-card">
          <h3>Group summary</h3>
          <div className="findings-grid">
            {bundle.groupSummary.map((g) => (
              <Card key={str(g.variant_type)} title={str(g.variant_type).replace(/_/g, " ")}>
                <p>Mean dangerousness shift: {Number(g.mean_dangerousness_delta).toFixed(2)}</p>
                <p>Action shift: {Number(g.mean_action_delta).toFixed(2)}</p>
                <p className="muted">{formatCount(g.n_comparisons)} comparisons · Flagged rate {formatRate(g.flagged_rate)}</p>
                <p className="caution-line">Possible concern — requires human review.</p>
              </Card>
            ))}
          </div>
        </section>
      ) : (
        <EmptyState
          title="No group summary"
          description="Export detention_group_summary.json to enable aggregate findings."
          command="python -m benchassist.vercel_export --auto --use-case detention --run-dir results/gemini/detention_full --data-status gemini_full"
        />
      )}
    </div>
  );
}
