"use client";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatCard } from "@/components/MetricCard";
import { LazyBarChart } from "@/components/LazyBarChart";
import { DetentionFindingsByIssueIndex } from "@/components/detention/DetentionFindingsByIssueIndex";
import { DetentionVariantMatrix } from "@/components/detention/DetentionVariantMatrix";
import { DetentionExecutiveFindings, type ExecutiveFinding } from "@/components/detention/DetentionExecutiveFindings";
import { DetentionKeyTakeaways } from "@/components/detention/DetentionKeyTakeaways";
import { DetentionExpertProgressPanel } from "@/components/detention/DetentionExpertProgressPanel";
import { PageHeader } from "@/components/detention/PageHeader";
import { MetricTipLabel } from "@/components/detention/DetentionMetricTip";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import type { DetentionTakeaway } from "@/lib/detentionTakeaways";
import type { ReviewProgressSummary } from "@/lib/detentionReview";
import { detentionHeadlineMetrics, filterRowsByPromptMode } from "@/lib/detentionMetrics";
import { isMinimalDetentionSchema } from "@/lib/detentionCaseReview";
import { formatCount, formatRate, str, toBool, isHighReviewPriority, hasMetricDeltaShift } from "@/lib/format";
import { formatVariantLabel } from "@/lib/v2/dataUtils";
import type { JsonRecord } from "@/lib/types";

export function DetentionAuditResultsPage({
  bundle,
  filteredFlagged,
  filteredPairwise,
  filteredAddressProxy,
  filteredAddressProxyFlagged,
  filters,
  takeaways,
  isMock,
  onViewCases,
  onReviewIssueGroup,
  onReviewExecutiveFinding,
  onOpenVariant,
  reviewProgress,
}: {
  bundle: DetentionDashboardBundle;
  filteredFlagged: JsonRecord[];
  filteredPairwise: JsonRecord[];
  filteredAddressProxy: JsonRecord[];
  filteredAddressProxyFlagged: JsonRecord[];
  filters: { promptMode: string };
  takeaways: DetentionTakeaway[];
  isMock: boolean;
  onViewCases: (t: DetentionTakeaway) => void;
  onReviewIssueGroup?: (filter: { issueKey: string; recordIds: string[] }) => void;
  onReviewExecutiveFinding?: (finding: ExecutiveFinding) => void;
  onOpenVariant?: (caseId: string, variantId: string) => void;
  reviewProgress?: ReviewProgressSummary | null;
}) {
  const schemaVersion =
    str(bundle.manifest.schema_version) ||
    str(bundle.fullMetricSummary[0]?.schema_version) ||
    str(bundle.overview.schema_version);
  const isMinimalSchema = isMinimalDetentionSchema(schemaVersion);
  const dangerousnessShifts = filteredFlagged.filter((r) => hasMetricDeltaShift(r.dangerousness_level_delta)).length;
  const highPriority = filteredFlagged.filter((r) => isHighReviewPriority(r.review_priority)).length;
  const headline = detentionHeadlineMetrics(bundle);
  const groupSummaryRows = filters.promptMode
    ? filterRowsByPromptMode(bundle.groupSummary, filters.promptMode)
    : bundle.groupSummary;
  const statisticalSource = bundle.statisticalTestsAll.length ? bundle.statisticalTestsAll : bundle.statisticalTests;
  const statisticalRows = filters.promptMode
    ? filterRowsByPromptMode(statisticalSource, filters.promptMode)
    : statisticalSource;

  const chartData = groupSummaryRows.slice(0, 8).map((g) => ({
    name: formatVariantLabel(str(g.variant_type)).slice(0, 18),
    value: Number(g.mean_dangerousness_delta) || 0,
    rawKey: str(g.variant_type),
  }));

  return (
    <div className="tab-panel">
      <PageHeader
        title="Audit Results"
        subtitle="Layered view of audit signals from the synthetic strict-fairness audit."
        note={
          isMock
            ? "Mock data — pipeline QA only, not a research finding."
            : filters.promptMode
              ? `Showing ${formatVariantLabel(filters.promptMode)} prompt mode. Change mode in the filter bar above.`
              : headline.usesBaselineHeadline
                ? "Baseline prompt mode shown by default. Select “All” in the filter bar to include mitigation prompts."
                : undefined
        }
      />

      {headline.usesBaselineHeadline && !isMock ? (
        <p className="muted section-intro headline-metrics-note">
          Headline flagged count uses baseline prompt mode only (dangerousness level change). Case review index may
          include all prompt modes. Address-proxy variants are excluded from strict demographic rates.
        </p>
      ) : null}

      <div className="metric-grid">
        <StatCard
          label="Total comparisons"
          value={formatCount(filteredPairwise.length || bundle.pairwise.length)}
          sub={
            <>
              <MetricTipLabel tipKey="strict_fairness">Synthetic strict audit</MetricTipLabel>
              {filters.promptMode ? ` · ${formatVariantLabel(filters.promptMode)}` : headline.usesBaselineHeadline ? " · baseline default" : ""}
            </>
          }
        />
        <StatCard label="Audit signals" value={formatCount(filteredFlagged.length)} sub="Dangerousness-level changes only" />
        <StatCard label="High-priority items" value={formatCount(highPriority)} sub="Review priority: High" />
        <StatCard label="Dangerousness shifts" value={formatCount(dangerousnessShifts)} sub="Primary audit signal" />
        <StatCard label="Strict-excluded layer" value={formatCount(bundle.overview.n_strict_excluded_review_outputs ?? 0)} sub={`${formatCount(bundle.overview.n_address_proxy_review_outputs ?? bundle.overview.n_strict_excluded_review_outputs ?? 0)} address-proxy outputs · excluded from strict rates`} />
      </div>

      {(filteredAddressProxy.length > 0 || bundle.addressProxyPairwise.length > 0) ? (
        <section className="section-card">
          <h3>Address-proxy audit bucket</h3>
          <p className="muted section-intro">
            Separate from strict demographic fairness rates. Address strings are proxy-cautious stress tests — not proof of individual identity.
          </p>
          <div className="metric-grid metric-grid-compact">
            <StatCard
              label="Address-proxy comparisons"
              value={formatCount(filteredAddressProxy.length || bundle.addressProxyPairwise.length)}
              sub={filters.promptMode ? formatVariantLabel(filters.promptMode) : "All prompt modes"}
            />
            <StatCard
              label="Address-proxy audit signals"
              value={formatCount(filteredAddressProxyFlagged.length)}
              sub="Flagged for separate expert review"
            />
          </div>
          {filteredAddressProxyFlagged.length ? (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Variant</th>
                    <th>Prompt</th>
                    <th>Flagged</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAddressProxyFlagged.slice(0, 12).map((row) => (
                    <tr key={`${str(row.case_id)}::${str(row.variant_id)}::${str(row.prompt_mode)}`}>
                      <td>{str(row.case_id)}</td>
                      <td>{formatVariantLabel(str(row.variant_type))}</td>
                      <td>{formatVariantLabel(str(row.prompt_mode || "baseline"))}</td>
                      <td>{toBool(row.detention_framing_bias_flag) ? "yes" : "no"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      {reviewProgress ? <DetentionExpertProgressPanel progress={reviewProgress} /> : null}

      {statisticalRows.length ? (
        <section className="section-card">
          <h3>Statistical uncertainty (exploratory)</h3>
          <p className="muted section-intro">Wilson 95% CIs and Benjamini–Hochberg FDR on variant-group flagged rates. Not proof of discrimination.</p>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Variant</th>
                  <th>n</th>
                  <th>Flagged rate</th>
                  <th>95% CI</th>
                  <th>FDR sig.</th>
                </tr>
              </thead>
              <tbody>
                {statisticalRows.slice(0, 12).map((row) => (
                  <tr key={`${str(row.variant_type)}::${str(row.prompt_mode || "baseline")}`}>
                    <td>{formatVariantLabel(str(row.variant_type))}</td>
                    <td>{formatCount(Number(row.n_comparisons))}</td>
                    <td>{formatRate(Number(row.flagged_rate))}</td>
                    <td>
                      {row.flagged_rate_ci_low != null
                        ? `${formatRate(Number(row.flagged_rate_ci_low))}–${formatRate(Number(row.flagged_rate_ci_high))}`
                        : "—"}
                    </td>
                    <td>{row.fdr_significant_at_0_10 ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="section-card">
        <h3>Key takeaways</h3>
        <p className="muted section-intro">Human-readable interpretation cards — audit signals only, requires human review.</p>
        <DetentionKeyTakeaways takeaways={takeaways} onViewCases={onViewCases} />
      </section>

      {(bundle.caseReviewIndex.length || bundle.caseReviewRecords.length) && onReviewExecutiveFinding ? (
        <DetentionExecutiveFindings
          records={bundle.caseReviewRecords.length ? bundle.caseReviewRecords : undefined}
          index={bundle.caseReviewIndex.length ? bundle.caseReviewIndex : undefined}
          schemaVersion={schemaVersion}
          onReview={(f: ExecutiveFinding) => onReviewExecutiveFinding(f)}
        />
      ) : null}

      {(bundle.caseReviewIndex.length || bundle.caseReviewRecords.length) && onReviewIssueGroup ? (
        <DetentionFindingsByIssueIndex
          index={bundle.caseReviewIndex}
          schemaVersion={schemaVersion}
          onReviewCases={onReviewIssueGroup}
        />
      ) : null}

      {chartData.length ? (
        <section className="section-card">
          <h3>
            <MetricTipLabel tipKey="dangerousness_shift">Mean dangerousness shift by variant</MetricTipLabel>
          </h3>
          <LazyBarChart
            data={chartData}
            ariaLabel="Mean dangerousness shift by variant type"
            valueFormat="delta"
            valueLabel="Mean shift"
          />
          <p className="muted chart-caption">Exploratory screening — may indicate possible concern. Not proof of unlawful discrimination.</p>
        </section>
      ) : null}

      {bundle.pairwise.length ? (
        <DetentionVariantMatrix bundle={bundle} promptMode={filters.promptMode} onSelectVariant={onOpenVariant} />
      ) : null}

      {groupSummaryRows.length ? (
        <section className="section-card">
          <h3>Group summary</h3>
          <div className="findings-grid">
            {groupSummaryRows.map((g) => (
              <Card key={`${str(g.variant_type)}::${str(g.prompt_mode || "baseline")}`} title={formatVariantLabel(str(g.variant_type))}>
                <p>Mean dangerousness shift: {Number(g.mean_dangerousness_delta).toFixed(2)}</p>
                {!isMinimalSchema ? <p>Action shift: {Number(g.mean_action_delta).toFixed(2)}</p> : null}
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
