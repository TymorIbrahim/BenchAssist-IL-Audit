"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { GlossaryDrawer, GLOSSARY_ENTRIES } from "@/components/GlossaryDrawer";
import { DetentionFilterBar } from "@/components/detention/DetentionFilterBar";
import { DetentionGuidedTour, useGuidedTour } from "@/components/detention/DetentionGuidedTour";
import { SafetyContextBar } from "@/components/detention/SafetyContextBar";
import { DetentionStatusStrip } from "@/components/detention/DetentionStatusStrip";
import { DetentionTabNav } from "@/components/detention/DetentionTabNav";
import { loadDashboardData } from "@/lib/data";
import { loadDetentionDashboardData, fetchCaseReviewRecord, fetchFullCaseReviewRecords, type DetentionDashboardBundle } from "@/lib/detentionData";
import { DEFAULT_CASE_REVIEW_FILTERS, dedupeCaseReviewRecords, pickReviewRecordId, type CaseReviewFilters, type CaseReviewRecord } from "@/lib/detentionCaseReview";
import { caseReviewFiltersFromUrl, caseReviewFiltersToUrl, caseReviewFiltersToUrlWithPreset } from "@/lib/caseReviewUrl";
import { presetPatchById } from "@/lib/caseReviewPresets";
import {
  DEFAULT_DETENTION_FILTERS,
  detentionFiltersFromUrl,
  detentionFiltersToUrl,
  filterDetentionRows,
  type DetentionFilterState,
} from "@/lib/detentionFilters";
import { defaultAuditPromptMode, findCaseReviewTarget, filterRowsByPromptMode } from "@/lib/detentionMetrics";
import { DETENTION_GLOSSARY_ENTRIES } from "@/lib/detentionGlossary";
import { parseDetentionTab, type DetentionTab } from "@/lib/detentionNavigation";
import { caseReviewKey } from "@/lib/detentionCaseReview";
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
  reviewKey,
  savePacketIds,
  saveReviewState,
  reviewerSummary,
  summarizeExpertReviewProgress,
  type ReviewRecord,
} from "@/lib/detentionReview";
import type { ExecutiveFinding } from "@/lib/detentionIndexFindings";
import { buildDetentionTakeaways } from "@/lib/detentionTakeaways";
import { loadReviewStorageWithFallback, scheduleReviewStorageBackup } from "@/lib/detentionReviewStorage";
import { useDetentionStickyOffsets } from "@/lib/useDetentionStickyOffsets";
import { str } from "@/lib/format";
import type { JsonRecord, Manifest } from "@/lib/types";

const DetentionCaseReviewWorkspace = dynamic(
  () => import("@/components/detention/DetentionCaseReviewWorkspace").then((m) => m.DetentionCaseReviewWorkspace),
  { loading: () => <div className="loading-screen"><p>Loading case review workspace…</p></div> },
);
const DetentionHomePage = dynamic(
  () => import("@/components/detention/DetentionHomePage").then((m) => m.DetentionHomePage),
);
const DetentionAuditResultsPage = dynamic(
  () => import("@/components/detention/DetentionAuditResultsPage").then((m) => m.DetentionAuditResultsPage),
);
const DetentionMitigationPage = dynamic(
  () => import("@/components/detention/DetentionMitigationPage").then((m) => m.DetentionMitigationPage),
);
const DetentionValidityPage = dynamic(
  () => import("@/components/detention/DetentionValidityPage").then((m) => m.DetentionValidityPage),
);
const DetentionReportsPage = dynamic(
  () => import("@/components/detention/DetentionReportsPage").then((m) => m.DetentionReportsPage),
);
const DetentionMethodologyPage = dynamic(
  () => import("@/components/detention/DetentionMethodologyPage").then((m) => m.DetentionMethodologyPage),
);
const DetentionPresentationMode = dynamic(
  () => import("@/components/detention/DetentionPresentationMode").then((m) => m.DetentionPresentationMode),
);

export default function DetentionDashboard({ initialManifest }: { initialManifest: Manifest }) {
  const [bundle, setBundle] = useState<DetentionDashboardBundle | null>(null);
  const [activeTab, setActiveTab] = useState<DetentionTab>("home");
  const [filters, setFilters] = useState<DetentionFilterState>(DEFAULT_DETENTION_FILTERS);
  const [selectedCase, setSelectedCase] = useState<JsonRecord | null>(null);
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [focusReviewMode, setFocusReviewMode] = useState(false);
  const [reviewFilterPatch, setReviewFilterPatch] = useState<Partial<CaseReviewFilters>>({});
  const [caseReviewFilters, setCaseReviewFilters] = useState<CaseReviewFilters>(DEFAULT_CASE_REVIEW_FILTERS);
  const [caseReviewLoading, setCaseReviewLoading] = useState(false);
  const [caseReviewLoadStatus, setCaseReviewLoadStatus] = useState("");
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [reviewState, setReviewState] = useState<Record<string, ReviewRecord>>({});
  const [packetIds, setPacketIds] = useState<string[]>([]);
  const [showGlossary, setShowGlossary] = useState(false);
  const [selectedReport, setSelectedReport] = useState("");
  const [presentationMode, setPresentationMode] = useState(false);
  const hydrated = useRef(false);
  const topBarRef = useRef<HTMLDivElement>(null);
  const filterAnchorRef = useRef<HTMLDivElement>(null);
  const tour = useGuidedTour();

  const router = useRouter();
  const searchParams = useSearchParams();
  const showFilters = activeTab === "audit-results";
  const shouldPrefetchCaseReview =
    activeTab === "case-review"
    || Boolean(searchParams.get("review_id"))
    || Boolean(searchParams.get("case_id"));
  useDetentionStickyOffsets(topBarRef, filterAnchorRef, showFilters && Boolean(bundle));

  useEffect(() => {
    loadDashboardData({ manifest: initialManifest }).then((base) => loadDetentionDashboardData(base).then(setBundle));
  }, [initialManifest]);

  useEffect(() => {
    void loadReviewStorageWithFallback().then((snap) => {
      setReviewState(snap.reviewState);
      setPacketIds(snap.packetIds);
    });
  }, []);

  useEffect(() => {
    scheduleReviewStorageBackup(reviewState, packetIds, []);
  }, [reviewState, packetIds]);

  useEffect(() => {
    if (hydrated.current || !bundle) return;
    const fromUrl = detentionFiltersFromUrl(searchParams);
    if (fromUrl.tab) setActiveTab(parseDetentionTab(fromUrl.tab));
    const { tab: _t, ...filterPatch } = fromUrl;
    const defaultPromptMode = defaultAuditPromptMode(bundle);
    const hasUrlPromptMode = Boolean(searchParams.get("prompt_mode"));
    const initialFilters: DetentionFilterState = {
      ...DEFAULT_DETENTION_FILTERS,
      ...(defaultPromptMode && !hasUrlPromptMode ? { promptMode: defaultPromptMode } : {}),
      ...filterPatch,
    };
    setFilters(initialFilters);
    const crFromUrl = caseReviewFiltersFromUrl(searchParams);
    if (Object.keys(crFromUrl).length) {
      setReviewFilterPatch(crFromUrl);
      setCaseReviewFilters({ ...DEFAULT_CASE_REVIEW_FILTERS, ...crFromUrl });
    }
    const caseId = searchParams.get("case_id");
    const variantId = searchParams.get("variant_id");
    const reviewId = searchParams.get("review_id");
    if (reviewId) {
      setSelectedReviewId(reviewId);
      setActiveTab("case-review");
    } else if (caseId) {
      const matchIndex = bundle.caseReviewIndex.find(
        (e) => e.base_case_id === caseId && (!variantId || e.variant_id === variantId),
      );
      if (matchIndex) {
        setSelectedReviewId(matchIndex.review_record_id);
        setActiveTab("case-review");
      } else {
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
    }
    if (bundle.reports.length && !selectedReport) setSelectedReport(bundle.reports[0].report_name);
    hydrated.current = true;
  }, [searchParams, bundle, selectedReport]);

  const caseReviewFetchStarted = useRef(false);

  useEffect(() => {
    if (!bundle || bundle.caseReviewLoaded || !shouldPrefetchCaseReview) return;
    if (!bundle.caseReviewIndexCount && !bundle.caseReviewRecords.length) return;
    if (caseReviewFetchStarted.current) return;
    caseReviewFetchStarted.current = true;
    let cancelled = false;
    setCaseReviewLoading(true);
    setCaseReviewLoadStatus(bundle.caseReviewSplit ? "Loading review records in background…" : "Loading case review records…");
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
  }, [bundle, shouldPrefetchCaseReview]);

  useEffect(() => {
    if (!shouldPrefetchCaseReview) caseReviewFetchStarted.current = false;
  }, [shouldPrefetchCaseReview]);

  const ensureRecordLoaded = useCallback(
    (reviewId: string) => {
      if (!bundle) return;
      if (bundle.caseReviewRecords.some((r) => caseReviewKey(r) === reviewId)) return;
      const indexEntry = bundle.caseReviewIndex.find((e) => e.review_record_id === reviewId);
      if (!indexEntry?.record_path) return;
      setDetailLoadingId(reviewId);
      fetchCaseReviewRecord(indexEntry.record_path).then((rec) => {
        setDetailLoadingId((current) => (current === reviewId ? null : current));
        if (!rec) return;
        setBundle((prev) =>
          prev
            ? {
                ...prev,
                caseReviewRecords: dedupeCaseReviewRecords([...prev.caseReviewRecords, rec]),
              }
            : prev,
        );
      });
    },
    [bundle],
  );

  const prefetchReviewRecords = useCallback(
    (reviewIds: string[]) => {
      if (!bundle) return;
      const pending = reviewIds.filter(
        (id) =>
          !bundle.caseReviewRecords.some((r) => caseReviewKey(r) === id)
          && bundle.caseReviewIndex.some((e) => e.review_record_id === id),
      );
      for (const id of pending.slice(0, 5)) {
        ensureRecordLoaded(id);
      }
    },
    [bundle, ensureRecordLoaded],
  );

  useEffect(() => {
    const reviewId = searchParams.get("review_id");
    if (!reviewId || !bundle) return;
    if (bundle.caseReviewRecords.some((r) => caseReviewKey(r) === reviewId)) return;
    ensureRecordLoaded(reviewId);
  }, [bundle, searchParams, ensureRecordLoaded]);

  useEffect(() => {
    if (!hydrated.current || !bundle) return;
    const tabParam = searchParams.get("tab");
    if (tabParam) {
      const parsed = parseDetentionTab(tabParam);
      if (parsed !== activeTab) setActiveTab(parsed);
    }
  }, [searchParams, bundle, activeTab]);

  useEffect(() => {
    if (!bundle || selectedReviewId) return;
    if (!focusReviewMode) return;
    const baselineMode = defaultAuditPromptMode(bundle);
    const pool = bundle.caseReviewIndex.filter(
      (e) =>
        (!baselineMode || e.prompt_mode === baselineMode)
        && e.is_flagged
        && (e.review_priority === "high" || e.review_priority === "medium"),
    );
    const first =
      pool[0]
      ?? bundle.caseReviewIndex.find(
        (e) => (!baselineMode || e.prompt_mode === baselineMode) && e.is_flagged,
      );
    if (first) setSelectedReviewId(first.review_record_id);
  }, [bundle, focusReviewMode, selectedReviewId]);

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
    setActiveTab(tab);
    if (tab !== "case-review") {
      syncUrl({ tab, caseId: null, variantId: null, reviewId: null });
    } else {
      syncUrl({ tab });
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openCaseReview = (
    patch: Partial<CaseReviewFilters>,
    reviewId?: string | null,
    presetId?: string | null,
  ) => {
    if (!bundle) return;
    const baselineMode = defaultAuditPromptMode(bundle);
    const mergedPatch = { ...patch, ...(presetId ? presetPatchById(presetId) ?? {} : {}) };
    const nextPatch: Partial<CaseReviewFilters> = {
      ...DEFAULT_CASE_REVIEW_FILTERS,
      ...(baselineMode ? { promptMode: baselineMode } : {}),
      ...mergedPatch,
    };
    const nextFocusMode = nextPatch.focusMode ?? focusReviewMode;
    if (nextPatch.focusMode) setFocusReviewMode(nextPatch.focusMode);
    const nextFilters = { ...DEFAULT_CASE_REVIEW_FILTERS, ...nextPatch, focusMode: nextFocusMode } as CaseReviewFilters;
    setReviewFilterPatch(nextPatch);
    setCaseReviewFilters(nextFilters);
    const resolvedReviewId = reviewId === undefined ? selectedReviewId : reviewId;
    if (resolvedReviewId) setSelectedReviewId(resolvedReviewId);
    setTab("case-review");
    const qs = presetId
      ? caseReviewFiltersToUrlWithPreset(nextFilters, presetId, {
          tab: "case-review",
          reviewId: resolvedReviewId ?? undefined,
        })
      : caseReviewFiltersToUrl(nextFilters, { tab: "case-review", reviewId: resolvedReviewId ?? undefined });
    router.replace(qs ? `?${qs}` : "/", { scroll: false });
  };

  const startExpertReview = () => {
    if (!bundle) return;
    setFocusReviewMode(true);
    const baselineMode = defaultAuditPromptMode(bundle);
    const pool = bundle.caseReviewIndex.filter(
      (e) =>
        (!baselineMode || e.prompt_mode === baselineMode)
        && e.is_flagged
        && (e.review_priority === "high" || e.review_priority === "medium"),
    );
    const first = pool[0]
      ?? bundle.caseReviewIndex.find(
        (e) => (!baselineMode || e.prompt_mode === baselineMode) && e.is_flagged,
      );
    openCaseReview({ focusMode: true, flaggedOnly: true }, first?.review_record_id ?? null);
  };

  const setFiltersAndSync = (f: DetentionFilterState) => {
    setFilters(f);
    syncUrl({ filters: f });
  };

  const filteredFlagged = useMemo(
    () => (bundle && activeTab === "audit-results" ? filterDetentionRows(bundle.flagged, filters) : []),
    [bundle, filters, activeTab],
  );
  const filteredPairwise = useMemo(
    () => (bundle && activeTab === "audit-results" ? filterDetentionRows(bundle.pairwise, filters) : []),
    [bundle, filters, activeTab],
  );
  const filteredAddressProxy = useMemo(
    () => (bundle && activeTab === "audit-results" ? filterDetentionRows(bundle.addressProxyPairwise, filters) : []),
    [bundle, filters, activeTab],
  );
  const filteredAddressProxyFlagged = useMemo(
    () => (bundle && activeTab === "audit-results" ? filterDetentionRows(bundle.addressProxyFlagged, filters) : []),
    [bundle, filters, activeTab],
  );
  const takeaways = useMemo(() => {
    if (!bundle) return [];
    const baselineMode = defaultAuditPromptMode(bundle);
    const flaggedForTakeaways = baselineMode
      ? filterRowsByPromptMode(bundle.flagged, baselineMode)
      : bundle.flagged;
    const groupForTakeaways = baselineMode
      ? filterRowsByPromptMode(bundle.groupSummary, baselineMode)
      : bundle.groupSummary;
    const schemaVersion =
      str(bundle.manifest.schema_version) ||
      str(bundle.fullMetricSummary[0]?.schema_version) ||
      str(bundle.overview.schema_version);
    return buildDetentionTakeaways({
      groupSummary: groupForTakeaways.length ? groupForTakeaways : bundle.groupSummary,
      flagged: flaggedForTakeaways.length ? flaggedForTakeaways : bundle.flagged,
      isMock: bundle.isMock,
      dataStatus: bundle.dataStatus,
      schemaVersion,
    });
  }, [bundle]);

  const reviewProgress = useMemo(() => {
    if (!bundle) return null;
    const keys = bundle.caseReviewRecords.length
      ? bundle.caseReviewRecords.filter((r) => Boolean(r.review_guidance?.why_flagged)).map((r) => caseReviewKey(r))
      : bundle.flagged.map((r) => reviewKey(r));
    return summarizeExpertReviewProgress(keys, reviewState, packetIds);
  }, [bundle, reviewState, packetIds]);

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
    importReviewStateBackup(file).then(({ reviewState: imported, packetIds: pids }) => {
      setReviewState(imported);
      saveReviewState(imported);
      setPacketIds(pids);
      savePacketIds(pids);
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

  const selectReviewId = useCallback(
    (reviewId: string) => {
      setSelectedReviewId(reviewId);
      const activeCrFilters = { ...caseReviewFilters, focusMode: focusReviewMode };
      setCaseReviewFilters(activeCrFilters);
      syncCaseReviewUrl(activeCrFilters, reviewId);
    },
    [caseReviewFilters, focusReviewMode, syncCaseReviewUrl],
  );

  if (!bundle) {
    return <div className="loading-screen"><p>Loading detention audit dashboard…</p></div>;
  }

  const { isMock } = bundle;
  const glossaryEntries = [...GLOSSARY_ENTRIES, ...DETENTION_GLOSSARY_ENTRIES];

  return (
    <div className={`dashboard-shell detention-dashboard ${presentationMode ? "presentation-mode-active" : ""}`}>
      <DetentionStatusStrip bundle={bundle} />
      <SafetyContextBar bundle={bundle} />

      <div className="detention-top-bar" ref={topBarRef}>
        <DetentionTabNav activeTab={activeTab} onTabChange={setTab} />
        <div className="detention-top-actions">
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowGlossary(true)}>Glossary</button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={tour.start}>Start here</button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPresentationMode(true)}>Presentation</button>
        </div>
      </div>

      {selectedReviewId && activeTab === "case-review" ? (
        <nav className="case-breadcrumb" aria-label="Case breadcrumb">
          <button
            type="button"
            className="link-button"
            onClick={() => {
              setSelectedReviewId(null);
              syncUrl({ tab: "case-review", reviewId: null });
            }}
          >
            Case Review
          </button>
          <span aria-hidden> / </span>
          <span>{selectedReviewId.replace(/::/g, " · ")}</span>
        </nav>
      ) : null}

      {showFilters ? (
        <div className="detention-filter-anchor" ref={filterAnchorRef}>
          <DetentionFilterBar
            flagged={bundle.flagged}
            pairwiseCount={filteredPairwise.length}
            flaggedCount={filteredFlagged.length}
            filters={filters}
            onChange={setFiltersAndSync}
            onReset={() =>
              setFiltersAndSync({
                ...DEFAULT_DETENTION_FILTERS,
                promptMode: defaultAuditPromptMode(bundle),
              })
            }
            sticky
          />
        </div>
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
            filteredAddressProxy={filteredAddressProxy}
            filteredAddressProxyFlagged={filteredAddressProxyFlagged}
            filters={filters}
            takeaways={takeaways}
            isMock={isMock}
            onViewCases={(t) => {
              if (t.filterVariant) setFiltersAndSync({ ...filters, variantType: t.filterVariant });
              if (t.filterIssue) setFiltersAndSync({ ...filters, issueType: t.filterIssue });
              if (t.filterReviewPatch) setReviewFilterPatch(t.filterReviewPatch);
              setTab("case-review");
            }}
            onReviewIssueGroup={({ issueKey, recordIds }) => {
              const baselineMode = defaultAuditPromptMode(bundle);
              const patch = {
                flaggedOnly: true,
                issueType: issueKey,
              };
              const reviewId = pickReviewRecordId(recordIds, { ...patch, promptMode: baselineMode }, bundle.caseReviewIndex);
              openCaseReview(patch, reviewId);
            }}
            onReviewExecutiveFinding={(finding: ExecutiveFinding) => {
              const patch: Partial<CaseReviewFilters> = { flaggedOnly: true };
              if (finding.id.startsWith("variant-")) {
                patch.variantType = finding.id.replace("variant-", "");
              }
              openCaseReview(patch);
            }}
            onOpenVariant={(caseId, variantId) => {
              const promptMode = filters.promptMode || defaultAuditPromptMode(bundle);
              const target = findCaseReviewTarget(bundle, caseId, variantId, promptMode);
              const patch = {
                ...DEFAULT_CASE_REVIEW_FILTERS,
                baseCaseId: caseId,
                variantType: target?.variantType ?? "",
                promptMode,
              };
              setReviewFilterPatch(patch);
              setActiveTab("case-review");
              if (target) {
                setSelectedReviewId(target.reviewId);
                syncCaseReviewUrl(patch, target.reviewId);
              } else {
                syncCaseReviewUrl(patch);
              }
            }}
            reviewProgress={reviewProgress}
          />
        )}

        {activeTab === "case-review" && (
          <DetentionCaseReviewWorkspace
            bundle={bundle}
            reviewState={reviewState}
            packetIds={packetIds}
            selectedId={selectedReviewId}
            onSelectReviewId={selectReviewId}
            onEnsureRecordLoaded={ensureRecordLoaded}
            onPrefetchRecords={prefetchReviewRecords}
            onUpdateReview={updateReview}
            onTogglePacket={togglePacketRecord}
            onRemoveFromPacket={removeFromPacket}
            onExportPacket={exportPacket}
            onImportReviewState={handleImportReviewState}
            focusMode={focusReviewMode}
            onFocusModeChange={setFocusReviewMode}
            initialFilters={reviewFilterPatch}
            onFiltersChange={(crFilters) => {
              setCaseReviewFilters(crFilters);
              syncCaseReviewUrl(crFilters, selectedReviewId);
            }}
            loading={caseReviewLoading}
            loadStatus={caseReviewLoadStatus}
            detailLoadingId={detailLoadingId}
            activePresetId={searchParams.get("cr_preset")}
            onApplyFilterPreset={(presetId) => openCaseReview({}, selectedReviewId, presetId)}
          />
        )}

        {activeTab === "mitigation" && <DetentionMitigationPage bundle={bundle} />}

        {activeTab === "validity" && (
          <DetentionValidityPage
            bundle={bundle}
            onOpenCaseReview={(patch, reviewId, presetId) => openCaseReview(patch, reviewId ?? null, presetId)}
          />
        )}

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
            if (rec) selectReviewId(caseReviewKey(rec));
            else if (bundle.flagged[0]) selectCase(bundle.flagged[0]);
            setTab("case-review");
          }}
        />
      ) : null}

      <GlossaryDrawer open={showGlossary} onClose={() => setShowGlossary(false)} entries={glossaryEntries} />
    </div>
  );
}
