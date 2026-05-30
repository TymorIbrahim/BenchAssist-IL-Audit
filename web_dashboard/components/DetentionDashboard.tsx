"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { GlossaryDrawer, GLOSSARY_ENTRIES } from "@/components/GlossaryDrawer";
import { DetentionCaseReviewWorkspace } from "@/components/detention/DetentionCaseReviewWorkspace";
import { DetentionAuditResultsPage } from "@/components/detention/DetentionAuditResultsPage";
import { DetentionFilterBar } from "@/components/detention/DetentionFilterBar";
import { DetentionGuidedTour, useGuidedTour } from "@/components/detention/DetentionGuidedTour";
import { DetentionHomePage } from "@/components/detention/DetentionHomePage";
import { DetentionLegalReliabilityPage } from "@/components/detention/DetentionLegalReliabilityPage";
import { DetentionMethodologyPage } from "@/components/detention/DetentionMethodologyPage";
import { DetentionMitigationPage } from "@/components/detention/DetentionMitigationPage";
import { DetentionPresentationMode } from "@/components/detention/DetentionPresentationMode";
import { DetentionRealCasePage } from "@/components/detention/DetentionRealCasePage";
import { DetentionReportsPage } from "@/components/detention/DetentionReportsPage";
import { SafetyContextBar } from "@/components/detention/SafetyContextBar";
import { DetentionStatusStrip } from "@/components/detention/DetentionStatusStrip";
import { DetentionTabNav } from "@/components/detention/DetentionTabNav";
import { loadDashboardData } from "@/lib/data";
import { loadDetentionDashboardData, fetchCaseReviewRecord, fetchFullCaseReviewRecords, type DetentionDashboardBundle } from "@/lib/detentionData";
import { DEFAULT_CASE_REVIEW_FILTERS, dedupeCaseReviewRecords, type CaseReviewFilters } from "@/lib/detentionCaseReview";
import { caseReviewFiltersFromUrl, caseReviewFiltersToUrl } from "@/lib/caseReviewUrl";
import {
  DEFAULT_DETENTION_FILTERS,
  detentionFiltersFromUrl,
  detentionFiltersToUrl,
  filterDetentionRealCases,
  filterDetentionRows,
  type DetentionFilterState,
} from "@/lib/detentionFilters";
import { DETENTION_GLOSSARY_ENTRIES } from "@/lib/detentionGlossary";
import { parseDetentionTab, type DetentionTab } from "@/lib/detentionNavigation";
import { caseReviewKey, type CaseReviewRecord } from "@/lib/detentionCaseReview";
import {
  buildCaseReviewPacketMarkdown,
  buildPacketMarkdown,
  EMPTY_CHECKLIST,
  exportCaseReviewPacketCsv,
  exportCaseReviewPacketJson,
  exportCaseReviewPacketPdf,
  exportPacketCsv,
  exportPacketJson,
  importReviewStateBackup,
  REAL_CASE_NOTES_KEY,
  reviewKey,
  savePacketIds,
  saveRealCasePacketIds,
  saveReviewState,
  reviewerSummary,
  type ReviewRecord,
} from "@/lib/detentionReview";
import { buildDetentionTakeaways } from "@/lib/detentionTakeaways";
import { loadReviewStorageWithFallback, scheduleReviewStorageBackup } from "@/lib/detentionReviewStorage";
import { str } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

export default function DetentionDashboard() {
  const [bundle, setBundle] = useState<DetentionDashboardBundle | null>(null);
  const [activeTab, setActiveTab] = useState<DetentionTab>("home");
  const [filters, setFilters] = useState<DetentionFilterState>(DEFAULT_DETENTION_FILTERS);
  const [selectedCase, setSelectedCase] = useState<JsonRecord | null>(null);
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [focusReviewMode, setFocusReviewMode] = useState(false);
  const [reviewFilterPatch, setReviewFilterPatch] = useState<Partial<CaseReviewFilters>>({});
  const [caseReviewLoading, setCaseReviewLoading] = useState(false);
  const [caseReviewLoadStatus, setCaseReviewLoadStatus] = useState("");
  const [selectedRealCase, setSelectedRealCase] = useState<JsonRecord | null>(null);
  const [reviewState, setReviewState] = useState<Record<string, ReviewRecord>>({});
  const [packetIds, setPacketIds] = useState<string[]>([]);
  const [realCasePacketIds, setRealCasePacketIds] = useState<string[]>([]);
  const [realCaseNotes, setRealCaseNotes] = useState<Record<string, string>>({});
  const [showGlossary, setShowGlossary] = useState(false);
  const [selectedReport, setSelectedReport] = useState("");
  const [presentationMode, setPresentationMode] = useState(false);
  const hydrated = useRef(false);
  const tour = useGuidedTour();

  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    loadDashboardData().then((base) => loadDetentionDashboardData(base).then(setBundle));
  }, []);

  useEffect(() => {
    void loadReviewStorageWithFallback().then((snap) => {
      setReviewState(snap.reviewState);
      setPacketIds(snap.packetIds);
      setRealCasePacketIds(snap.realCasePacketIds);
    });
    try {
      setRealCaseNotes(JSON.parse(localStorage.getItem(REAL_CASE_NOTES_KEY) ?? "{}"));
    } catch { /* empty */ }
  }, []);

  useEffect(() => {
    scheduleReviewStorageBackup(reviewState, packetIds, realCasePacketIds);
  }, [reviewState, packetIds, realCasePacketIds]);

  useEffect(() => {
    if (hydrated.current || !bundle) return;
    const fromUrl = detentionFiltersFromUrl(searchParams);
    if (fromUrl.tab) setActiveTab(parseDetentionTab(fromUrl.tab));
    const { tab: _t, ...filterPatch } = fromUrl;
    if (Object.keys(filterPatch).length) setFilters((prev) => ({ ...prev, ...filterPatch }));
    const crFromUrl = caseReviewFiltersFromUrl(searchParams);
    if (Object.keys(crFromUrl).length) setReviewFilterPatch(crFromUrl);
    const caseId = searchParams.get("case_id");
    const variantId = searchParams.get("variant_id");
    const reviewId = searchParams.get("review_id");
    if (reviewId) {
      setSelectedReviewId(reviewId);
      setActiveTab("case-review");
    } else if (caseId) {
      const matchReview = bundle.caseReviewRecords.find(
        (r) => r.base_case_id === caseId && (!variantId || r.variant_id === variantId),
      );
      if (matchReview) {
        setSelectedReviewId(caseReviewKey(matchReview));
        setActiveTab("case-review");
      } else {
        const match = bundle.flagged.find((r) => str(r.case_id) === caseId && (!variantId || str(r.variant_id) === variantId));
        if (match) {
          setSelectedCase(match);
          setActiveTab("case-review");
        }
      }
    }
    if (bundle.reports.length && !selectedReport) setSelectedReport(bundle.reports[0].report_name);
    hydrated.current = true;
  }, [searchParams, bundle, selectedReport]);

  useEffect(() => {
    if (!bundle || bundle.caseReviewLoaded) return;
    if (!bundle.caseReviewIndexCount && !bundle.caseReviewRecords.length) return;
    let cancelled = false;
    setCaseReviewLoading(true);
    setCaseReviewLoadStatus(bundle.caseReviewSplit ? "Loading review records (split export)…" : "Loading case review records…");
    fetchFullCaseReviewRecords()
      .then(({ records, meta }) => {
        if (cancelled) return;
        setBundle((prev) =>
          prev
            ? {
                ...prev,
                caseReviewRecords: records,
                caseReviewMeta: meta ?? prev.caseReviewMeta,
                caseReviewLoaded: true,
              }
            : prev,
        );
        setCaseReviewLoading(false);
        setCaseReviewLoadStatus("");
      })
      .catch(() => {
        if (cancelled) return;
        setCaseReviewLoading(false);
        setCaseReviewLoadStatus("Failed to load review records.");
      });
    return () => {
      cancelled = true;
    };
    // Intentionally omit full `bundle` — prefetch updates must not cancel the in-flight full load.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stable keys only; see review_id prefetch effect
  }, [bundle?.caseReviewLoaded, bundle?.caseReviewIndexCount, bundle?.caseReviewSplit]);

  useEffect(() => {
    if (!bundle?.caseReviewLoaded) return;
    const reviewId = searchParams.get("review_id");
    if (!reviewId || bundle.caseReviewRecords.some((r) => caseReviewKey(r) === reviewId)) return;
    const indexEntry = bundle.caseReviewIndex.find((r) => r.review_record_id === reviewId);
    if (!indexEntry?.record_path) return;
    let cancelled = false;
    fetchCaseReviewRecord(indexEntry.record_path).then((rec) => {
      if (cancelled || !rec) return;
      setBundle((prev) =>
        prev
          ? {
              ...prev,
              caseReviewRecords: dedupeCaseReviewRecords([...prev.caseReviewRecords, rec]),
            }
          : prev,
      );
    });
    return () => {
      cancelled = true;
    };
  }, [bundle, searchParams]);

  useEffect(() => {
    if (!hydrated.current || !bundle) return;
    const tabParam = searchParams.get("tab");
    if (tabParam) {
      const parsed = parseDetentionTab(tabParam);
      if (parsed !== activeTab) setActiveTab(parsed);
    }
  }, [searchParams, bundle, activeTab]);

  useEffect(() => {
    if (!bundle?.caseReviewLoaded || selectedReviewId) return;
    if (!focusReviewMode) return;
    const first =
      bundle.caseReviewRecords.find((r) => r.is_flagged && (r.review_priority === "high" || r.review_priority === "medium"))
      ?? bundle.caseReviewRecords.find((r) => r.is_flagged);
    if (first) setSelectedReviewId(caseReviewKey(first));
  }, [bundle?.caseReviewLoaded, bundle?.caseReviewRecords, focusReviewMode, selectedReviewId]);

  const syncCaseReviewUrl = useCallback(
    (crFilters: CaseReviewFilters, reviewId?: string | null) => {
      const qs = caseReviewFiltersToUrl(crFilters, {
        tab: "case-review",
        reviewId: reviewId ?? selectedReviewId ?? undefined,
      });
      router.replace(qs ? `?${qs}` : "/", { scroll: false });
    },
    [router, selectedReviewId],
  );

  const syncUrl = useCallback(
    (patch: {
      tab?: DetentionTab;
      filters?: DetentionFilterState;
      caseId?: string | null;
      variantId?: string | null;
      reviewId?: string | null;
    }) => {
      const tab = patch.tab ?? activeTab;
      const onCaseReview = tab === "case-review";
      const qs = detentionFiltersToUrl(patch.filters ?? filters, {
        tab,
        caseId:
          patch.caseId !== undefined
            ? patch.caseId ?? undefined
            : onCaseReview && selectedCase
              ? str(selectedCase.case_id)
              : undefined,
        variantId:
          patch.variantId !== undefined
            ? patch.variantId ?? undefined
            : onCaseReview && selectedCase
              ? str(selectedCase.variant_id)
              : undefined,
        reviewId:
          patch.reviewId !== undefined
            ? patch.reviewId ?? undefined
            : onCaseReview && selectedReviewId
              ? selectedReviewId
              : undefined,
      });
      router.replace(qs ? `?${qs}` : "/", { scroll: false });
    },
    [filters, router, selectedCase, selectedReviewId, activeTab],
  );

  const setTab = (tab: DetentionTab) => {
    const resolved = tab === "expert-workspace" ? "case-review" : tab;
    setActiveTab(resolved);
    if (resolved !== "case-review") {
      syncUrl({ tab: resolved, caseId: null, variantId: null, reviewId: null });
    } else {
      syncUrl({ tab: resolved });
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const startExpertReview = () => {
    setFocusReviewMode(true);
    setReviewFilterPatch({ ...DEFAULT_CASE_REVIEW_FILTERS, focusMode: true, flaggedOnly: true });
    setTab("case-review");
    const flagged = bundle?.caseReviewRecords.filter((r) => r.is_flagged && (r.review_priority === "high" || r.review_priority === "medium"))
      ?? [];
    const first = flagged[0] ?? bundle?.caseReviewRecords.find((r) => r.is_flagged);
    if (first) setSelectedReviewId(caseReviewKey(first));
  };

  const setFiltersAndSync = (f: DetentionFilterState) => {
    setFilters(f);
    syncUrl({ filters: f });
  };

  const filteredFlagged = useMemo(() => (bundle ? filterDetentionRows(bundle.flagged, filters) : []), [bundle, filters]);
  const filteredPairwise = useMemo(() => (bundle ? filterDetentionRows(bundle.pairwise, filters) : []), [bundle, filters]);
  const filteredRealCases = useMemo(() => (bundle ? filterDetentionRealCases(bundle.realCaseExamples, filters) : []), [bundle, filters]);

  const takeaways = useMemo(
    () => (bundle ? buildDetentionTakeaways({ groupSummary: bundle.groupSummary, flagged: bundle.flagged, isMock: bundle.isMock, dataStatus: bundle.dataStatus }) : []),
    [bundle],
  );

  const packetReviewRecords = useMemo(
    () => (bundle ? bundle.caseReviewRecords.filter((r) => packetIds.includes(caseReviewKey(r))) : []),
    [bundle, packetIds],
  );

  const packetRows = useMemo(
    () => (bundle ? bundle.flagged.filter((r) => packetIds.includes(reviewKey(r))) : []),
    [bundle, packetIds],
  );

  const updateReview = (key: string, patch: Partial<ReviewRecord>) => {
    setReviewState((prev) => {
      const next = {
        ...prev,
        [key]: {
          reviewed: patch.reviewed ?? prev[key]?.reviewed ?? false,
          notes: patch.notes ?? prev[key]?.notes ?? "",
          reviewedAt: patch.reviewedAt ?? (patch.reviewed !== undefined || patch.decision ? new Date().toISOString() : prev[key]?.reviewedAt ?? ""),
          decision: patch.decision ?? prev[key]?.decision ?? "not_reviewed",
          checklist: { ...EMPTY_CHECKLIST, ...(patch.checklist ?? prev[key]?.checklist ?? {}) },
        },
      };
      saveReviewState(next);
      return next;
    });
  };

  const togglePacketRecord = (record: CaseReviewRecord) => {
    const key = caseReviewKey(record);
    setPacketIds((prev) => {
      const next = prev.includes(key) ? prev.filter((id) => id !== key) : [...prev, key];
      savePacketIds(next);
      return next;
    });
  };

  const removeFromPacket = (id: string) => {
    setPacketIds((prev) => {
      const next = prev.filter((x) => x !== id);
      savePacketIds(next);
      return next;
    });
  };

  const handleImportReviewState = (file: File) => {
    importReviewStateBackup(file).then(({ reviewState: imported, packetIds: pids, realCasePacketIds: rcIds }) => {
      setReviewState(imported);
      saveReviewState(imported);
      setPacketIds(pids);
      savePacketIds(pids);
      setRealCasePacketIds(rcIds);
      saveRealCasePacketIds(rcIds);
    });
  };

  const toggleRealCasePacket = (sourceId: string) => {
    setRealCasePacketIds((prev) => {
      const next = prev.includes(sourceId) ? prev.filter((id) => id !== sourceId) : [...prev, sourceId];
      saveRealCasePacketIds(next);
      return next;
    });
  };

  const togglePacket = (row: JsonRecord) => {
    const key = reviewKey(row);
    setPacketIds((prev) => {
      const next = prev.includes(key) ? prev.filter((id) => id !== key) : [...prev, key];
      savePacketIds(next);
      return next;
    });
  };

  const exportPacket = (format: "json" | "csv" | "md" | "pdf") => {
    const reviewRows = packetReviewRecords.length
      ? packetReviewRecords
      : bundle?.caseReviewRecords.filter((r) => r.is_flagged).slice(0, 10) ?? [];
    if (reviewRows.length) {
      if (format === "json") exportCaseReviewPacketJson(reviewRows, reviewState);
      else if (format === "csv") exportCaseReviewPacketCsv(reviewRows, reviewState);
      else if (format === "pdf") {
        exportCaseReviewPacketPdf(reviewRows, reviewState, {
          dataMode: bundle?.isMock ? "Mock" : String(bundle?.dataStatus),
        });
      } else {
        void navigator.clipboard.writeText(
          buildCaseReviewPacketMarkdown(reviewRows, reviewState, {
            dataMode: bundle?.isMock ? "Mock" : String(bundle?.dataStatus),
            exportedAt: new Date().toISOString(),
          }),
        );
      }
      return;
    }
    const rows = packetRows.length ? packetRows : filteredFlagged.slice(0, 10);
    if (format === "json") exportPacketJson(rows, reviewState);
    else if (format === "csv") exportPacketCsv(rows, reviewState);
    else {
      void navigator.clipboard.writeText(
        buildPacketMarkdown(rows, reviewState, {
          dataMode: bundle?.isMock ? "Mock" : String(bundle?.dataStatus),
          exportedAt: new Date().toISOString(),
        }),
      );
    }
  };

  const selectCase = (row: JsonRecord) => {
    setSelectedCase(row);
    syncUrl({ tab: "case-review", caseId: str(row.case_id), variantId: str(row.variant_id), reviewId: null });
  };

  const selectReviewRecord = (record: CaseReviewRecord) => {
    const reviewId = caseReviewKey(record);
    setSelectedReviewId(reviewId);
    syncCaseReviewUrl({ ...DEFAULT_CASE_REVIEW_FILTERS, ...reviewFilterPatch, focusMode: focusReviewMode }, reviewId);
  };

  if (!bundle) {
    return <div className="loading-screen"><p>Loading detention audit dashboard…</p></div>;
  }

  const { isMock } = bundle;
  const glossaryEntries = [...GLOSSARY_ENTRIES, ...DETENTION_GLOSSARY_ENTRIES];
  const showFilters = ["audit-results"].includes(activeTab);

  return (
    <div className={`dashboard-shell detention-dashboard ${presentationMode ? "presentation-mode-active" : ""}`}>
      <DetentionStatusStrip bundle={bundle} />
      <SafetyContextBar bundle={bundle} />

      <div className="detention-top-bar">
        <DetentionTabNav activeTab={activeTab} onTabChange={setTab} />
        <div className="detention-top-actions">
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowGlossary(true)}>Glossary</button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={tour.start}>Start here</button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPresentationMode(true)}>Presentation</button>
        </div>
      </div>

      {selectedCase && activeTab === "case-review" ? (
        <nav className="case-breadcrumb" aria-label="Case breadcrumb">
          <button type="button" className="link-button" onClick={() => setSelectedCase(null)}>Case Review</button>
          <span aria-hidden> / </span>
          <span>{str(selectedCase.case_id)} · {str(selectedCase.variant_id)}</span>
        </nav>
      ) : null}

      {showFilters ? (
        <DetentionFilterBar
          flagged={bundle.flagged}
          filters={filters}
          onChange={setFiltersAndSync}
          onReset={() => setFiltersAndSync(DEFAULT_DETENTION_FILTERS)}
          sticky
        />
      ) : null}

      <main className="detention-main">
        {activeTab === "home" && (
          <DetentionHomePage
            bundle={bundle}
            onNavigate={(tab) => setTab(tab)}
            onStartTour={tour.start}
            onPresentationMode={() => setPresentationMode(true)}
            onStartExpertReview={startExpertReview}
          />
        )}

        {activeTab === "audit-results" && (
          <DetentionAuditResultsPage
            bundle={bundle}
            filteredFlagged={filteredFlagged}
            filteredPairwise={filteredPairwise}
            takeaways={takeaways}
            isMock={isMock}
            onViewCases={(t) => {
              if (t.filterVariant) setFiltersAndSync({ ...filters, variantType: t.filterVariant });
              if (t.filterIssue) setFiltersAndSync({ ...filters, issueType: t.filterIssue });
              if (t.filterReviewPatch) setReviewFilterPatch(t.filterReviewPatch);
              setTab("case-review");
            }}
            onReviewIssueGroup={({ recordIds }) => {
              const patch = { ...DEFAULT_CASE_REVIEW_FILTERS, flaggedOnly: true };
              setReviewFilterPatch(patch);
              if (recordIds[0]) setSelectedReviewId(recordIds[0]);
              setActiveTab("case-review");
              syncCaseReviewUrl(patch, recordIds[0] ?? null);
            }}
            onReviewExecutiveFinding={(variantType) => {
              const patch = { ...DEFAULT_CASE_REVIEW_FILTERS, variantType, flaggedOnly: true };
              setReviewFilterPatch(patch);
              setTab("case-review");
              syncCaseReviewUrl(patch);
            }}
            onOpenVariant={(caseId, variantId) => {
              const rec = bundle.caseReviewRecords.find((r) => r.base_case_id === caseId && r.variant_id === variantId);
              const indexEntry = bundle.caseReviewIndex.find(
                (e) => e.base_case_id === caseId && e.variant_id === variantId,
              );
              const patch = {
                ...DEFAULT_CASE_REVIEW_FILTERS,
                baseCaseId: caseId,
                variantType: rec?.variant_type ?? indexEntry?.variant_type ?? "",
              };
              setReviewFilterPatch(patch);
              setActiveTab("case-review");
              if (rec) {
                setSelectedReviewId(caseReviewKey(rec));
                syncCaseReviewUrl(patch, caseReviewKey(rec));
              } else if (indexEntry) {
                setSelectedReviewId(indexEntry.review_record_id);
                syncCaseReviewUrl(patch, indexEntry.review_record_id);
              } else {
                syncCaseReviewUrl(patch);
              }
            }}
            onReviewIdentityCases={() => {
              const patch = { ...DEFAULT_CASE_REVIEW_FILTERS, identityLeakage: "yes", flaggedOnly: true };
              setReviewFilterPatch(patch);
              setTab("case-review");
              syncCaseReviewUrl(patch);
            }}
          />
        )}

        {activeTab === "case-review" && (
          <DetentionCaseReviewWorkspace
            bundle={bundle}
            reviewState={reviewState}
            packetIds={packetIds}
            selectedId={selectedReviewId}
            onSelectRecord={selectReviewRecord}
            onUpdateReview={updateReview}
            onTogglePacket={togglePacketRecord}
            onRemoveFromPacket={removeFromPacket}
            onExportPacket={exportPacket}
            onImportReviewState={handleImportReviewState}
            focusMode={focusReviewMode}
            onFocusModeChange={setFocusReviewMode}
            initialFilters={reviewFilterPatch}
            onFiltersChange={(crFilters) => syncCaseReviewUrl(crFilters, selectedReviewId)}
            loading={caseReviewLoading}
            loadStatus={caseReviewLoadStatus}
          />
        )}

        {activeTab === "mitigation" && <DetentionMitigationPage bundle={bundle} />}

        {activeTab === "real-cases" && (
          <DetentionRealCasePage
            filteredRealCases={filteredRealCases}
            selectedRealCase={selectedRealCase}
            onSelectRealCase={setSelectedRealCase}
            realCaseNotes={realCaseNotes}
            onNotesChange={(id, n) => {
              const next = { ...realCaseNotes, [id]: n };
              setRealCaseNotes(next);
              localStorage.setItem(REAL_CASE_NOTES_KEY, JSON.stringify(next));
            }}
            realCasePacketIds={realCasePacketIds}
            onToggleRealCasePacket={toggleRealCasePacket}
            filters={filters}
            onFilterChange={setFiltersAndSync}
          />
        )}

        {activeTab === "legal-reliability" && <DetentionLegalReliabilityPage bundle={bundle} isMock={isMock} />}

        {activeTab === "reports" && (
          <DetentionReportsPage
            reports={bundle.reports}
            isMock={isMock}
            selectedReport={selectedReport}
            onSelectReport={setSelectedReport}
          />
        )}

        {activeTab === "methodology" && (
          <DetentionMethodologyPage
            onOpenGlossary={() => setShowGlossary(true)}
            exampleRecord={bundle.caseReviewRecords.find((r) => r.is_flagged) ?? bundle.caseReviewRecords[0] ?? null}
          />
        )}
      </main>

      <DetentionGuidedTour
        open={tour.open}
        step={tour.step}
        onStepChange={tour.setStep}
        onClose={tour.close}
        onGoToTab={(tab) => { setTab(tab); tour.close(); }}
      />

      {presentationMode ? (
        <DetentionPresentationMode
          bundle={bundle}
          takeaways={takeaways}
          onClose={() => setPresentationMode(false)}
          onOpenCase={() => {
            setPresentationMode(false);
            const rec = bundle.caseReviewRecords.find((r) => r.is_flagged) ?? bundle.caseReviewRecords[0];
            if (rec) selectReviewRecord(rec);
            else if (bundle.flagged[0]) selectCase(bundle.flagged[0]);
            setTab("case-review");
          }}
        />
      ) : null}

      <GlossaryDrawer open={showGlossary} onClose={() => setShowGlossary(false)} entries={glossaryEntries} />
    </div>
  );
}
