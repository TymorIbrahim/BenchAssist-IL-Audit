"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart } from "@/components/BarChart";
import { Callout } from "@/components/Callout";
import { Card } from "@/components/Card";
import { CaseComparison, type ComparisonMode } from "@/components/CaseComparison";
import { DataTable } from "@/components/DataTable";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { DownloadButton } from "@/components/DownloadButton";
import { EmptyState } from "@/components/EmptyState";
import { AudienceGuide } from "@/components/AudienceGuide";
import { DataTransparency } from "@/components/DataTransparency";
import { ExecutiveLanding } from "@/components/ExecutiveLanding";
import { ExploreByConcern } from "@/components/ExploreByConcern";
import { MainFindingsStory } from "@/components/MainFindingsStory";
import { MethodologyContent } from "@/components/MethodologyContent";
import { PresentationPanel } from "@/components/PresentationPanel";
import { FilterPanel } from "@/components/FilterPanel";
import { GlossaryDrawer } from "@/components/GlossaryDrawer";
import { GuidedReviewPanel } from "@/components/GuidedReviewPanel";
import { InsightCards } from "@/components/InsightCards";
import { MarkdownReportViewer } from "@/components/MarkdownReportViewer";
import { MetricExplainer } from "@/components/MetricExplainer";
import { MetricCard, StatCard } from "@/components/MetricCard";
import { RealCaseAuditSection } from "@/components/RealCaseAuditSection";
import { ReviewerQuestions } from "@/components/ReviewerQuestions";
import { Section } from "@/components/Section";
import { SectionGuide } from "@/components/SectionGuide";
import { Sidebar, useActiveSection } from "@/components/Sidebar";
import { StatusPill } from "@/components/StatusPill";
import { loadDashboardData } from "@/lib/data";
import { buildAuditStorySteps } from "@/lib/auditStory";
import { getCaseContext } from "@/lib/caseContext";
import { enrichRows, reviewPriority, reviewPriorityReason, reviewPriorityVariant, rowsToCsv, downloadText } from "@/lib/derive";
import {
  DEFAULT_FILTERS,
  barChartByDemographic,
  barChartData,
  filterFlagged,
  filterGroupSummary,
  filterPairwise,
  filterValidity,
  type ChartBar,
  type FilterState,
  variantTypeFromChartLabel,
} from "@/lib/filters";
import { formatCount, formatRate, str, toBool, uniqueValues } from "@/lib/format";
import { formatVariantLabel } from "@/lib/v2/dataUtils";
import { generateInsights, generateKeyTakeaways, topFlaggedExamples } from "@/lib/insights";
import { ALL_NAV_SECTIONS } from "@/lib/navigationGroups";
import { getMetricDefinition } from "@/lib/metricDefinitions";
import { countByField, overviewMetricValue } from "@/lib/metrics";
import { scrollToSection } from "@/lib/navigation";
import { categorizeReports, RECOMMENDED_READING, REPORT_CATEGORIES } from "@/lib/reportCategories";
import { generateBulkReviewerPacket, downloadReviewerPacket } from "@/lib/reviewerPacket";
import { copyShareLink, urlFromAppState } from "@/lib/urlState";
import { summarizeCrossPromptComparisons } from "@/lib/crossPromptComparison";
import { useDashboardUrlState } from "@/lib/useDashboardUrlState";
import { type DashboardData } from "@/lib/types";

const OVERVIEW_KEY: Record<string, keyof import("@/lib/types").OverviewMetrics> = {
  legal_framing_bias_flag_rate: "main_legal_framing_flag_rate",
  action_type_flip_rate: "action_type_flip_rate",
  remedy_weaker_rate: "remedy_weaker_rate",
  evidence_burden_higher_rate: "evidence_burden_higher_rate",
  credibility_more_skeptical_rate: "credibility_more_skeptical_rate",
  rights_orientation_weaker_rate: "rights_orientation_weaker_rate",
};

const PRESENTATION_PATH = [
  { section: "overview", label: "Overview" },
  { section: "audit-story", label: "Audit story" },
  { section: "main-findings", label: "Main findings" },
  { section: "case-explorer", label: "Case Explorer example" },
  { section: "human-review", label: "Limitations / Human review" },
];

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [selectedFlagged, setSelectedFlagged] = useState<Record<string, unknown> | null>(null);
  const [explorerCase, setExplorerCase] = useState("");
  const [explorerVariant, setExplorerVariant] = useState("");
  const [selectedReport, setSelectedReport] = useState("");
  const [reportSearch, setReportSearch] = useState("");
  const [chartView, setChartView] = useState<"variant" | "demographic">("variant");
  const [topN, setTopN] = useState(5);
  const [sortDesc, setSortDesc] = useState(true);
  const [explorerFlaggedOnly, setExplorerFlaggedOnly] = useState(false);
  const [explorerStrictOnly, setExplorerStrictOnly] = useState(false);
  const [selectedStereotype, setSelectedStereotype] = useState<Record<string, unknown> | null>(null);
  const [showGlossary, setShowGlossary] = useState(false);
  const [guidedOpen, setGuidedOpen] = useState(false);
  const [presentationMode, setPresentationMode] = useState(false);
  const [comparisonMode, setComparisonMode] = useState<ComparisonMode>("neutral_vs_variant");
  const [variantBId, setVariantBId] = useState("");
  const [issueExplanation, setIssueExplanation] = useState("");
  const [linkCopied, setLinkCopied] = useState(false);

  const sectionIds = useMemo(() => ALL_NAV_SECTIONS.map((s) => s.id), []);
  const activeSection = useActiveSection(sectionIds);

  useEffect(() => { loadDashboardData().then(setData); }, []);

  const pairwise = useMemo(() => enrichRows(data?.pairwise ?? []), [data]);
  const flaggedSource = useMemo(() => {
    if (data?.flagged?.length) return enrichRows(data.flagged);
    return pairwise.filter((r) => toBool(r.legal_framing_bias_flag));
  }, [data, pairwise]);

  const filteredGroup = useMemo(() => (data ? filterGroupSummary(data.groupSummary, filters) : []), [data, filters]);
  const filteredPairwise = useMemo(() => filterPairwise(pairwise, filters), [pairwise, filters]);
  const filteredFlagged = useMemo(() => filterFlagged(flaggedSource, filters), [flaggedSource, filters]);
  const filteredValidity = useMemo(() => (data ? filterValidity(data.validity, filters) : []), [data, filters]);

  const chartData = useMemo(() => {
    const fn = chartView === "variant" ? barChartData : barChartByDemographic;
    return fn(filteredGroup, filters.metricKey, topN, sortDesc);
  }, [filteredGroup, filters.metricKey, topN, sortDesc, chartView]);

  const mitigationChart = useMemo(
    () => barChartData(
      (data?.mitigation ?? []).map((r) => ({ variant_type: r.variant_type, legal_framing_bias_flag_rate: r.baseline_legal_framing_bias_flag_rate })),
      "legal_framing_bias_flag_rate", 5,
    ),
    [data?.mitigation],
  );

  const variantsForCase = useMemo(() => {
    let rows = pairwise.filter((r) => str(r.case_id) === explorerCase && str(r.variant_type) !== "neutral_he");
    if (explorerFlaggedOnly) rows = rows.filter((r) => toBool(r.legal_framing_bias_flag));
    if (explorerStrictOnly && data?.validity.length) {
      const strictIds = new Set(
        data.validity.filter((v) => str(v.validity_category).includes("strict")).map((v) => `${str(v.case_id)}::${str(v.variant_id)}`),
      );
      rows = rows.filter((r) => strictIds.has(`${str(r.case_id)}::${str(r.variant_id)}`));
    }
    return rows;
  }, [pairwise, explorerCase, explorerFlaggedOnly, explorerStrictOnly, data?.validity]);

  const caseIds = useMemo(() => uniqueValues(pairwise, "case_id"), [pairwise]);

  const explorerRow = useMemo(() => {
    if (!data) return null;
    const qual = data.qualitative.find((r) => str(r.case_id) === explorerCase && str(r.variant_id) === explorerVariant);
    if (qual) return qual;
    return pairwise.find((r) => str(r.case_id) === explorerCase && str(r.variant_id) === explorerVariant) ?? null;
  }, [data, pairwise, explorerCase, explorerVariant]);

  const currentFlaggedIndex = useMemo(
    () => filteredFlagged.findIndex((r) => str(r.case_id) === explorerCase && str(r.variant_id) === explorerVariant),
    [filteredFlagged, explorerCase, explorerVariant],
  );

  const openExplorer = useCallback((caseId: string, variantId: string) => {
    setExplorerCase(caseId);
    setExplorerVariant(variantId);
    setSelectedFlagged(filteredFlagged.find((r) => str(r.case_id) === caseId && str(r.variant_id) === variantId) ?? null);
    scrollToSection("case-explorer");
  }, [filteredFlagged]);

  const { syncUrl } = useDashboardUrlState({
    filters,
    setFilters,
    caseId: explorerCase,
    variantId: explorerVariant,
    comparisonMode,
    onCaseSelect: openExplorer,
    onComparisonMode: setComparisonMode,
    enabled: !!data,
  });

  useEffect(() => {
    if (!data) return;
    syncUrl({ filters, caseId: explorerCase, variantId: explorerVariant, comparisonMode });
  }, [data, filters, explorerCase, explorerVariant, comparisonMode, syncUrl]);

  const filterByChartBar = useCallback((bar: ChartBar) => {
    const vt = bar.rawKey || variantTypeFromChartLabel(bar.name, data?.groupSummary ?? []);
    setFilters((f) => ({ ...f, variantType: vt, flaggedOnly: true }));
    scrollToSection("flagged-cases");
  }, [data?.groupSummary]);

  const filterByValidity = useCallback((category: string) => {
    setFilters((f) => ({ ...f, validityCategory: category, flaggedOnly: true }));
    scrollToSection("flagged-cases");
  }, []);

  const goFlagged = useCallback((delta: number) => {
    if (!filteredFlagged.length) return;
    const idx = currentFlaggedIndex >= 0 ? currentFlaggedIndex + delta : (delta > 0 ? 0 : filteredFlagged.length - 1);
    const clamped = Math.max(0, Math.min(filteredFlagged.length - 1, idx));
    const row = filteredFlagged[clamped];
    openExplorer(str(row.case_id), str(row.variant_id));
  }, [filteredFlagged, currentFlaggedIndex, openExplorer]);

  useEffect(() => {
    if (data?.reports.length && !selectedReport) setSelectedReport(data.reports[0].report_name);
  }, [data, selectedReport]);

  useEffect(() => {
    if (filters.caseId && filters.caseId !== explorerCase) setExplorerCase(filters.caseId);
  }, [filters.caseId, explorerCase]);

  const insights = useMemo(() => (data ? generateInsights(data) : []), [data]);
  const keyTakeaways = useMemo(() => (data ? generateKeyTakeaways(data) : []), [data]);
  const storySteps = useMemo(() => (data ? buildAuditStorySteps(data) : []), [data]);
  const presentationExamples = useMemo(() => topFlaggedExamples(filteredFlagged, 3), [filteredFlagged]);
  const filteredReports = useMemo(
    () => (data?.reports ?? []).filter((r) => !reportSearch || r.title.toLowerCase().includes(reportSearch.toLowerCase())),
    [data?.reports, reportSearch],
  );
  const reportBuckets = useMemo(() => categorizeReports(filteredReports), [filteredReports]);
  const crossPromptSummary = useMemo(
    () => summarizeCrossPromptComparisons(data?.crossPromptComparisons ?? []),
    [data?.crossPromptComparisons],
  );
  const topGroupsByMetric = useMemo(() => {
    if (!data) return [];
    return [...data.groupSummary]
      .filter((r) => str(r.variant_type) !== "neutral_he")
      .sort((a, b) => (Number(b[filters.metricKey]) || 0) - (Number(a[filters.metricKey]) || 0))
      .slice(0, 5);
  }, [data, filters.metricKey]);

  if (!data) {
    return (
      <div className="loading-screen">
        <p>Loading audit data…</p>
        <p className="muted">If this persists, run: <code>python -m benchassist.vercel_export --auto</code></p>
      </div>
    );
  }

  const { manifest, overview } = data;
  const report = data.reports.find((r) => r.report_name === selectedReport);
  const validityCounts = countByField(data.validitySummary, "validity_category");
  const selectedMetricDef = getMetricDefinition(filters.metricKey);

  const boolCol = (key: string) => ({
    key,
    label: key.replace(/_/g, " "),
    render: (r: Record<string, unknown>) => (toBool(r[key]) ? "Yes" : "No"),
  });

  const rowId = (r: Record<string, unknown>) => `${str(r.case_id)}-${str(r.variant_id)}`;

  return (
    <div className={`app-shell ${presentationMode ? "presentation-mode" : ""}`}>
      <DisclaimerBanner text={manifest.disclaimer} />
      <GlossaryDrawer open={showGlossary} onClose={() => setShowGlossary(false)} />
      <div className="app-body">
        <Sidebar manifest={manifest} activeSection={activeSection} onGlossary={() => setShowGlossary(true)} />
        <main className="main-content">
          <div className="dashboard-toolbar">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setGuidedOpen(true)}>Start guided review</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPresentationMode(!presentationMode)}>
              {presentationMode ? "Exit presentation mode" : "Presentation mode"}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowGlossary(true)}>Glossary</button>
          </div>
          <GuidedReviewPanel open={guidedOpen} onClose={() => setGuidedOpen(false)} />
          {presentationMode ? (
            <Card title="Suggested 5-minute presentation path" className="presentation-path">
              <ol>{PRESENTATION_PATH.map((s) => (
                <li key={s.section}><button type="button" className="link-button" onClick={() => scrollToSection(s.section)}>{s.label}</button></li>
              ))}</ol>
            </Card>
          ) : null}

          <Section id="overview" title="Executive overview" lead="">
            <ExecutiveLanding onOpenPresentation={() => scrollToSection("key-takeaways")} />
            <AudienceGuide />
            <div className="stat-grid executive-stats">
              <StatCard label="Base cases" value={formatCount(overview.base_cases)} sub="Synthetic scenarios" />
              <StatCard label="Flagged for review" value={formatCount(overview.total_flagged_cases)} sub="Screening signals" />
              <StatCard label="Main audit signal rate" value={formatRate(overview.main_legal_framing_flag_rate)} sub="Not a legal conclusion" />
              <StatCard label="Model" value={manifest.model} sub={manifest.provider} />
            </div>
            {(manifest.dataset_modes_available?.length ?? 0) > 0 ? (
              <Card title="Dataset layers available">
                <p className="muted">
                  <strong>Synthetic controlled</strong> — main strict counterfactual fairness audit.
                  {" "}
                  {(manifest.dataset_modes_available ?? []).includes("real_case_inspired") ? (
                    <>
                      <strong>Real-case-inspired</strong> — multi-domain realism layer (not strict fairness proof).
                    </>
                  ) : (
                    "Real-case-inspired layer not exported in this run."
                  )}
                </p>
              </Card>
            ) : null}
            <FilterPanel filters={filters} onChange={setFilters} groupRows={data.groupSummary} pairwiseRows={pairwise} collapsible resultCount={filteredFlagged.length} showReviewPriority showCaseId />
          </Section>

          <Section id="key-takeaways" title="Key takeaways" lead="Plain-language summary of this exported run — cautious, data-driven, not conclusions.">
            <InsightCards insights={keyTakeaways} />
            <PresentationPanel
              data={data}
              exampleCase={presentationExamples[0]}
              onOpenExample={() => {
                const ex = presentationExamples[0];
                if (ex) openExplorer(str(ex.case_id), str(ex.variant_id));
              }}
            />
          </Section>

          <Section id="audit-story" title="Audit story" lead="Step-by-step for non-technical reviewers.">
            <SectionGuide sectionId="audit-story" />
            <div className="timeline">
              {storySteps.map((step) => (
                <div key={step.n} className="timeline-step">
                  <div className="timeline-num">{step.n}</div>
                  <Card title={step.title}><p>{step.text}</p></Card>
                </div>
              ))}
            </div>
          </Section>

          <Section id="main-findings" title="Main findings" lead="Audit signal rates by variant — screening signals, not legal conclusions.">
            <SectionGuide sectionId="main-findings" />
            <MainFindingsStory
              metricKey={filters.metricKey}
              metricValue={overviewMetricValue(overview, OVERVIEW_KEY[filters.metricKey] ?? filters.metricKey)}
              topGroups={topGroupsByMetric}
              onViewFlagged={() => { setFilters((f) => ({ ...f, flaggedOnly: true })); scrollToSection("flagged-cases"); }}
            />
            <ExploreByConcern
              flaggedRows={flaggedSource}
              onViewCases={(nextFilters, explanation) => {
                setFilters(nextFilters);
                setIssueExplanation(explanation);
                scrollToSection("flagged-cases");
              }}
            />
            {issueExplanation ? <Callout title="Concern focus" variant="info">{issueExplanation}</Callout> : null}
            <MetricExplainer metricKey={filters.metricKey} value={overviewMetricValue(overview, OVERVIEW_KEY[filters.metricKey] ?? filters.metricKey)} />
            <div className="chart-controls">
              <label>Metric<select value={filters.metricKey} onChange={(e) => setFilters({ ...filters, metricKey: e.target.value })}>{Object.keys(OVERVIEW_KEY).map((k) => (<option key={k} value={k}>{getMetricDefinition(k)?.shortLabel ?? k}</option>))}</select></label>
              <label>View<select value={chartView} onChange={(e) => setChartView(e.target.value as "variant" | "demographic")}><option value="variant">By variant type</option><option value="demographic">By demographic cue</option></select></label>
              <label>Top N<select value={topN} onChange={(e) => setTopN(Number(e.target.value))}>{[3, 5, 8, 12].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSortDesc(!sortDesc)}>{sortDesc ? "Sort: high → low" : "Sort: low → high"}</button>
            </div>
            <Card title={selectedMetricDef?.label ?? "Audit signals"}>
              <BarChart data={chartData} ariaLabel="Interactive audit signal chart" onBarClick={filterByChartBar} activeKey={filters.variantType} />
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => scrollToSection("flagged-cases")}>View flagged cases for current filters</button>
            </Card>
            <Card title="Group summary" className={presentationMode ? "presentation-hide-table" : ""}>
              <DataTable rows={filteredGroup} columns={[
                { key: "variant_type", label: "Variant", render: (r) => formatVariantLabel(str(r.variant_type)) },
                { key: "demographic_cue", label: "Cue" },
                { key: filters.metricKey, label: "Selected metric", render: (r) => formatRate(r[filters.metricKey]) },
                { key: "n_pairs", label: "Pairs" },
              ]} emptyMessage="No rows match filters." />
            </Card>
          </Section>

          <Section id="flagged-cases" title="Flagged cases" lead="Legal review queue — flagged for inspection, not labeled as biased.">
            <SectionGuide sectionId="flagged-cases" />
            <Callout title="About review priority" variant="info">
              Priority is based on the number and type of audit signals. It does not mean the model is biased or that unlawful discrimination occurred.
            </Callout>
            <FilterPanel filters={filters} onChange={setFilters} groupRows={data.groupSummary} pairwiseRows={pairwise} showCaseId showReviewPriority showIssueTag showHighPriorityOnly resultCount={filteredFlagged.length} collapsible />
            <div className="btn-row">
              <DownloadButton label="Download filtered CSV" filename="flagged_cases_filtered.csv" content={rowsToCsv(filteredFlagged)} disabled={!filteredFlagged.length} />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={async () => {
                  const ok = await copyShareLink(urlFromAppState({ section: "flagged-cases", filters }));
                  setLinkCopied(ok);
                  setTimeout(() => setLinkCopied(false), 2000);
                }}
              >
                {linkCopied ? "Filtered link copied" : "Copy filtered view link"}
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!filteredFlagged.filter((r) => reviewPriority(r) === "High").length || !data}
                onClick={() => {
                  if (!data) return;
                  const high = filteredFlagged.filter((r) => reviewPriority(r) === "High").slice(0, 5);
                  const contexts = high.map((r) => getCaseContext(str(r.case_id), str(r.variant_id), data));
                  downloadText("top_flagged_reviewer_packets.md", generateBulkReviewerPacket(contexts, data), "text/markdown");
                }}
              >
                Download top flagged reviewer packet
              </button>
            </div>
            <DataTable
              rows={filteredFlagged}
              selectedRowId={selectedFlagged ? rowId(selectedFlagged) : undefined}
              columns={[
                { key: "case_id", label: "Case" },
                { key: "variant_type", label: "Variant", render: (r) => formatVariantLabel(str(r.variant_type)) },
                { key: "review_priority", label: "Priority", render: (r) => <StatusPill label={reviewPriority(r)} variant={reviewPriorityVariant(reviewPriority(r))} /> },
                { key: "strongest_signal", label: "Strongest signal" },
                { key: "issue_tags", label: "Issue tags", render: (r) => Array.isArray(r.issue_tags) ? (r.issue_tags as string[]).join(", ").replace(/_/g, " ") : "—" },
                { key: "validity_category", label: "Validity", render: (r) => str(r.validity_category).replace(/_/g, " ") || "—" },
                { key: "actions", label: "Actions", render: (r) => (
                  <div className="btn-row">
                    <button type="button" className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); openExplorer(str(r.case_id), str(r.variant_id)); }}>Inspect in Case Explorer</button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={async (e) => {
                        e.stopPropagation();
                        await copyShareLink(urlFromAppState({ section: "case-explorer", filters, caseId: str(r.case_id), variantId: str(r.variant_id) }));
                      }}
                    >
                      Copy share link
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!data) return;
                        const ctx = getCaseContext(str(r.case_id), str(r.variant_id), data);
                        downloadReviewerPacket(ctx, data);
                      }}
                    >
                      Reviewer packet
                    </button>
                  </div>
                ) },
              ]}
              onRowClick={(row) => { setSelectedFlagged(row); openExplorer(str(row.case_id), str(row.variant_id)); }}
              emptyMessage="No flagged cases match filters."
            />
            {selectedFlagged ? (
              <Card title="Selected case — review panel" className="detail-panel">
                <div className="detail-header">
                  <h4>{str(selectedFlagged.case_id)} · {formatVariantLabel(str(selectedFlagged.variant_type))}</h4>
                  <StatusPill label="Flagged for legal review" variant="caution" />
                </div>
                <p><strong>Review priority:</strong> {reviewPriority(selectedFlagged)}</p>
                <p><strong>Strongest signal:</strong> {str(selectedFlagged.strongest_signal)}</p>
                <p><strong>Why this priority?</strong> {reviewPriorityReason(selectedFlagged)}</p>
                <p><strong>Why inspect:</strong> Different remedies, evidence demands, or credibility framing may affect access to relief — but a legally justified difference may exist.</p>
                <div className="btn-row">
                  <button type="button" className="btn btn-secondary" onClick={() => openExplorer(str(selectedFlagged.case_id), str(selectedFlagged.variant_id))}>Inspect in Case Explorer</button>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => { if (data) downloadReviewerPacket(getCaseContext(str(selectedFlagged.case_id), str(selectedFlagged.variant_id), data), data); }}>Download reviewer packet</button>
                </div>
                <ReviewerQuestions title="Quick review questions" />
              </Card>
            ) : null}
          </Section>

          <Section id="case-explorer" title="Case explorer" lead="Side-by-side legal review workspace — neutral vs variant.">
            <SectionGuide sectionId="case-explorer" />
            <div className="explorer-controls">
              <label>Case<select value={explorerCase} onChange={(e) => { setExplorerCase(e.target.value); setExplorerVariant(""); }}><option value="">Select…</option>{caseIds.map((id) => <option key={id} value={id}>{id}</option>)}</select></label>
              <label>Variant<select value={explorerVariant} onChange={(e) => setExplorerVariant(e.target.value)} disabled={!explorerCase}><option value="">Select…</option>{variantsForCase.map((v) => <option key={str(v.variant_id)} value={str(v.variant_id)}>{formatVariantLabel(str(v.variant_type))}</option>)}</select></label>
              <label className="checkbox-label"><input type="checkbox" checked={explorerFlaggedOnly} onChange={(e) => setExplorerFlaggedOnly(e.target.checked)} /> Flagged variants only</label>
              <label className="checkbox-label"><input type="checkbox" checked={explorerStrictOnly} onChange={(e) => setExplorerStrictOnly(e.target.checked)} /> Direct-bias eligible only</label>
            </div>
            <CaseComparison
              row={explorerRow}
              data={data}
              comparisonMode={comparisonMode}
              onComparisonModeChange={setComparisonMode}
              variantBId={variantBId}
              onVariantBChange={setVariantBId}
              variantsForCase={variantsForCase}
              hasPrev={currentFlaggedIndex > 0}
              hasNext={currentFlaggedIndex >= 0 && currentFlaggedIndex < filteredFlagged.length - 1}
              onPrev={() => goFlagged(-1)}
              onNext={() => goFlagged(1)}
              onBackToFlagged={() => scrollToSection("flagged-cases")}
            />
            {presentationMode && presentationExamples.length ? (
              <Card title="Strongest case examples (presentation)">
                <ul>{presentationExamples.map((r) => (
                  <li key={`${str(r.case_id)}-${str(r.variant_id)}`}>
                    <button type="button" className="link-button" onClick={() => openExplorer(str(r.case_id), str(r.variant_id))}>
                      {str(r.case_id)} · {formatVariantLabel(str(r.variant_type))} — {str(r.strongest_signal)}
                    </button>
                  </li>
                ))}</ul>
              </Card>
            ) : null}
          </Section>

          <Section id="real-case-audit" title="Real Israeli case-inspired audit" lead="Multi-domain realism layer — not the main strict counterfactual fairness test.">
            <SectionGuide sectionId="real-case-audit" />
            <RealCaseAuditSection
              domainSummary={data.realCaseDomainSummary}
              auditSummary={data.realCaseAuditSummary}
              auditOutputs={data.realCaseAuditOutputs}
              examples={data.realCaseExamples}
              limitations={manifest.real_case_limitations}
              sourceDataset={manifest.real_case_source_dataset}
            />
          </Section>

          <Section id="counterfactual-validity" title="Validity checks" lead="How strongly can we compare neutral vs variant outputs?">
            <SectionGuide sectionId="counterfactual-validity" />
            <Callout title="Why this matters" variant="caution">Strict counterfactuals support direct comparison. Stress tests need cautious interpretation.</Callout>
            {Object.keys(validityCounts).length ? (
              <>
                <div className="chip-row">
                  {Object.entries(validityCounts).map(([k, v]) => (
                    <button key={k} type="button" className="chip-button" onClick={() => filterByValidity(k)}>{k.replace(/_/g, " ")}: {v}</button>
                  ))}
                </div>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setFilters((f) => ({ ...f, validityCategory: "strict_counterfactual", flaggedOnly: true })); scrollToSection("flagged-cases"); }}>Show flagged cases eligible for strict analysis</button>
                <DataTable rows={filteredValidity} columns={[
                  { key: "case_id", label: "Case" },
                  { key: "variant_type", label: "Variant" },
                  { key: "validity_category", label: "Category" },
                  { key: "fact_preservation_score", label: "Fact preservation" },
                  { key: "go", label: "", render: (r) => <button type="button" className="btn btn-ghost btn-sm" onClick={() => openExplorer(str(r.case_id), str(r.variant_id))}>Inspect</button> },
                ]} />
              </>
            ) : <EmptyState title="No validity data" description="Counterfactual validity outputs were not exported." command="python -m benchassist.vercel_export --auto" />}
          </Section>

          <Section id="mitigation" title="Mitigation comparison" lead="Did fairness-aware or demographic-blind prompting help?">
            <SectionGuide sectionId="mitigation" />
            {data.crossPromptComparisons.length ? (
              <Card title="Cross-prompt comparison summary">
                <p className="muted">
                  These are not bias rates. They show how much the prompt mitigation changed the model&apos;s memo for the same case and variant.
                </p>
                <div className="stat-grid">
                  <StatCard label="Comparable case/variant pairs" value={String(crossPromptSummary.comparableRows)} sub="Unique pairs in export" />
                  <StatCard label="Baseline → fairness: action changed" value={formatRate(crossPromptSummary.baselineVsFairnessActionRate)} sub="Same case/variant" />
                  <StatCard label="Baseline → blind: action changed" value={formatRate(crossPromptSummary.baselineVsBlindActionRate)} sub="Same case/variant" />
                  <StatCard label="Avg remedy strength Δ" value={crossPromptSummary.avgRemedyStrengthDelta != null ? crossPromptSummary.avgRemedyStrengthDelta.toFixed(2) : "—"} sub="Across all comparisons" />
                  <StatCard label="Evidence burden changed" value={formatRate(crossPromptSummary.evidenceBurdenChangedRate)} sub="Any comparison type" />
                  <StatCard label="Credibility framing changed" value={formatRate(crossPromptSummary.credibilityChangedRate)} sub="Any comparison type" />
                  <StatCard label="Rights orientation changed" value={formatRate(crossPromptSummary.rightsOrientationChangedRate)} sub="Any comparison type" />
                </div>
              </Card>
            ) : (
              <EmptyState
                title="Cross-prompt comparison not exported"
                description="Only one prompt mode was detected, or output CSVs for multiple modes were not found. Run baseline, fairness-aware, and demographic-blind experiments, then re-export."
                command="python -m benchassist.vercel_export --auto"
              />
            )}
            {data.mitigation.length ? (
              <>
                <Callout title="Interpret carefully">Mitigation may improve one metric while worsening another. Not a substitute for legal review.</Callout>
                <DataTable rows={data.mitigation} columns={[
                  { key: "variant_type", label: "Variant", render: (r) => formatVariantLabel(str(r.variant_type)) },
                  { key: "baseline_legal_framing_bias_flag_rate", label: "Baseline", render: (r) => formatRate(r.baseline_legal_framing_bias_flag_rate) },
                  { key: "fairness_legal_framing_bias_flag_rate", label: "Fairness-aware", render: (r) => formatRate(r.fairness_legal_framing_bias_flag_rate) },
                  { key: "demographic_blind_legal_framing_bias_flag_rate", label: "Demographic-blind", render: (r) => formatRate(r.demographic_blind_legal_framing_bias_flag_rate) },
                  { key: "delta_legal_framing_bias_flag_rate", label: "Δ fairness", render: (r) => formatRate(r.delta_legal_framing_bias_flag_rate) },
                ]} />
                <BarChart data={mitigationChart} ariaLabel="Mitigation baseline by variant" />
              </>
            ) : <EmptyState title="No mitigation data" description="Mitigation comparison was not exported." />}
          </Section>

          <Section id="narrative-robustness" title="Narrative robustness" lead="Sensitivity to emotional or informal language — not necessarily demographic bias.">
            <SectionGuide sectionId="narrative-robustness" />
            {data.narrativeRobustness.length ? <DataTable rows={data.narrativeRobustness} columns={Object.keys(data.narrativeRobustness[0] ?? {}).slice(0, 8).map((k) => ({ key: k, label: k.replace(/_/g, " ") }))} /> : <EmptyState title="No narrative robustness summary" description="Not available in this export." />}
          </Section>

          <Section id="stereotype" title="Identity leakage" lead="Whether identity appears in legal reasoning when not legally relevant.">
            <SectionGuide sectionId="stereotype" />
            {data.stereotypeGroup.length ? (
              <>
                <MetricCard label="Identity leakage rate" value={overview.identity_leakage_rate} meaning="Screening rate for identity in reasoning." showReviewBadge={false} caution="" />
                <DataTable rows={data.stereotypeExamples} columns={[
                  { key: "case_id", label: "Case" },
                  { key: "new_identity_categories", label: "New identity" },
                  { key: "flagged_snippets", label: "Snippets" },
                  { key: "go", label: "", render: (r) => <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setSelectedStereotype(r); openExplorer(str(r.case_id), str(r.variant_id)); }}>Inspect case</button> },
                ]} emptyMessage="No flagged stereotype examples in this export." />
                {selectedStereotype ? <Card title="Selected example"><p>{str(selectedStereotype.flagged_snippets)}</p></Card> : null}
              </>
            ) : <EmptyState title="No stereotype audit" description="Stereotype audit outputs were not exported." />}
          </Section>

          <Section id="hallucination" title="Grounding & hallucination" lead="Whether memos stayed within provided toy legal sources.">
            <SectionGuide sectionId="hallucination" />
            {data.hallucinationGroup.length ? (
              <>
                <DataTable rows={data.hallucinationGroup} columns={[
                  { key: "invalid_citation_rate", label: "Invalid citation", render: (r) => formatRate(r.invalid_citation_rate) },
                  { key: "unsupported_legal_claim_rate", label: "Unsupported claim", render: (r) => formatRate(r.unsupported_legal_claim_rate) },
                  { key: "high_hallucination_risk_rate", label: "High risk", render: (r) => formatRate(r.high_hallucination_risk_rate) },
                ]} />
                <DataTable rows={data.hallucinationPer.filter((r) => toBool(r.high_hallucination_risk_flag)).slice(0, 25)} columns={[
                  { key: "case_id", label: "Case" },
                  { key: "invalid_citations", label: "Invalid citations" },
                  { key: "unsupported_claims", label: "Unsupported claims" },
                  { key: "go", label: "", render: (r) => <button type="button" className="btn btn-ghost btn-sm" onClick={() => openExplorer(str(r.case_id), str(r.variant_id))}>Inspect</button> },
                ]} />
              </>
            ) : <EmptyState title="No hallucination audit" description="Run grounded mode and hallucination audit, then re-export." command="python -m benchassist.vercel_export --auto" />}
          </Section>

          <Section id="statistical" title="Statistical uncertainty" lead="Confidence intervals help avoid overinterpreting small samples.">
            <SectionGuide sectionId="statistical" />
            {data.statisticalEffects.length ? (
              <DataTable rows={data.statisticalEffects} columns={[
                { key: "metric", label: "Metric" },
                { key: "variant_type", label: "Variant" },
                { key: "rate", label: "Rate", render: (r) => formatRate(r.rate) },
                { key: "ci_lower", label: "CI lower", render: (r) => formatRate(r.ci_lower) },
                { key: "ci_upper", label: "CI upper", render: (r) => formatRate(r.ci_upper) },
              ]} />
            ) : <EmptyState title="No statistical analysis" description="Run statistical analysis, then re-export." command="python -m benchassist.statistical_analysis (if configured)" />}
          </Section>

          <Section id="human-review" title="Human review workspace" lead="Actionable workflow for legal experts.">
            <SectionGuide sectionId="human-review" />
            <div className="classification-grid">
              {["Likely concern", "Legally justified difference", "Inconclusive", "Invalid comparison"].map((c) => (
                <div key={c} className="classification-card"><strong>{c}</strong><p className="muted">Use when recording review decisions in the template.</p></div>
              ))}
            </div>
            <div className="btn-row">
              <DownloadButton label="Download review template (CSV)" filename="human_review_template.csv" content={rowsToCsv(data.humanReview)} disabled={!data.humanReview.length} />
              <a className="btn btn-secondary" href="/data/human_review_template.json" download>Download JSON</a>
            </div>
            {data.humanReview.length ? <DataTable rows={data.humanReview} columns={Object.keys(data.humanReview[0] ?? {}).slice(0, 8).map((k) => ({ key: k, label: k.replace(/_/g, " ") }))} /> : <EmptyState title="No review template" description="Template not exported for this run." />}
          </Section>

          <Section id="reports" title="Reports & downloads" lead="Written reports and presentation materials.">
            <SectionGuide sectionId="reports" />
            <InsightCards insights={insights.slice(0, 2)} compact />
            <Card title="Recommended reading order">
              <ol>{RECOMMENDED_READING.map((key) => {
                const match = data.reports.find((r) => r.report_name.includes(key.replace(/_/g, "").slice(0, 8)) || r.report_name.includes(key.split("_")[0]));
                return <li key={key}>{match ? match.title : key.replace(/_/g, " ")}</li>;
              })}</ol>
            </Card>
            {presentationMode ? (
              <Card title="For presentation">
                <div className="btn-row">
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => { const r = data.reports.find((x) => x.report_name.includes("presentation")); if (r) setSelectedReport(r.report_name); scrollToSection("reports"); }}>Presentation notes</button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => scrollToSection("main-findings")}>Main findings</button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => scrollToSection("case-explorer")}>Case explorer</button>
                </div>
              </Card>
            ) : null}
            {data.reports.length ? (
              <>
                <label className="select-label">Search reports<input type="search" value={reportSearch} onChange={(e) => setReportSearch(e.target.value)} placeholder="Filter reports…" /></label>
                {REPORT_CATEGORIES.map((cat) => {
                  const items = reportBuckets[cat.id] ?? [];
                  if (!items.length) return null;
                  return (
                    <Card key={cat.id} title={cat.title}>
                      <p className="muted">{cat.description}</p>
                      <ul className="report-list">
                        {items.map((r) => (
                          <li key={r.report_name}>
                            <strong>{r.title}</strong>
                            <p className="muted">{r.report_name.replace(/_/g, " ")}</p>
                            <div className="btn-row">
                              <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setSelectedReport(r.report_name); scrollToSection("reports"); }}>Open</button>
                              <DownloadButton label="Download" filename={`${r.report_name}.md`} content={r.markdown_text} mime="text/markdown" />
                            </div>
                          </li>
                        ))}
                      </ul>
                    </Card>
                  );
                })}
                <label className="select-label">Select report<select value={selectedReport} onChange={(e) => setSelectedReport(e.target.value)}>{filteredReports.map((r) => <option key={r.report_name} value={r.report_name}>{r.title}</option>)}</select></label>
                {report ? (<><DownloadButton label="Download report (.md)" filename={`${report.report_name}.md`} content={report.markdown_text} mime="text/markdown" /><MarkdownReportViewer markdown={report.markdown_text} title={report.title} /></>) : null}
              </>
            ) : <EmptyState title="No reports" description="Not available in this exported run." command="Generate reports, then: python -m benchassist.vercel_export --auto" />}
          </Section>

          <Section id="methodology" title="Methodology & limitations" lead="What this dashboard can and cannot support.">
            <SectionGuide sectionId="methodology" />
            <MethodologyContent />
            <DataTransparency manifest={manifest} />
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowGlossary(true)}>Open plain-language glossary</button>
          </Section>
        </main>
      </div>
    </div>
  );
}
