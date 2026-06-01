"use client";

import { IconScale } from "@/components/v2/Icons";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { DashboardBundle } from "@/lib/v2/dataUtils";
import { loadDashboardBundle } from "@/lib/v2/dataUtils";
import type { DashboardTab } from "@/lib/v2/types";
import { DASHBOARD_TABS } from "@/lib/v2/types";

/* Lazy-load page components */
import dynamic from "next/dynamic";

const OverviewPage = dynamic(
  () => import("@/components/v2/OverviewPage").then((m) => m.OverviewPage),
  { loading: () => <Loading /> },
);
const FairnessScreeningPage = dynamic(
  () => import("@/components/v2/FairnessScreeningPage").then((m) => m.FairnessScreeningPage),
  { loading: () => <Loading /> },
);
const PromptMitigationPage = dynamic(
  () => import("@/components/v2/PromptMitigationPage").then((m) => m.PromptMitigationPage),
  { loading: () => <Loading /> },
);
const CaseExplorerPage = dynamic(
  () => import("@/components/v2/CaseExplorerPage").then((m) => m.CaseExplorerPage),
  { loading: () => <Loading /> },
);
const RunMetadataPage = dynamic(
  () => import("@/components/v2/RunMetadataPage").then((m) => m.RunMetadataPage),
  { loading: () => <Loading /> },
);

function Loading() {
  return (
    <div className="v2-loading">
      <div className="v2-loading__spinner" />
      <p className="v2-loading__text">Loading…</p>
    </div>
  );
}

export function DashboardShell() {
  const [bundle, setBundle] = useState<DashboardBundle | null>(null);
  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");

  /* Load data on mount */
  useEffect(() => {
    loadDashboardBundle().then(setBundle);
  }, []);

  /* Restore tab from URL on mount */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get("tab");
    if (tab && DASHBOARD_TABS.some((t) => t.id === tab)) {
      setActiveTab(tab as DashboardTab);
    }
  }, []);

  /* Sync tab to URL */
  const navigateTab = useCallback((tab: DashboardTab) => {
    setActiveTab(tab);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    window.history.replaceState({}, "", url.toString());
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  /* Disclaimer text */
  const disclaimer = useMemo(() => {
    if (!bundle) return "";
    const disclaimers = bundle.overview.disclaimers;
    if (Array.isArray(disclaimers) && disclaimers.length) {
      return disclaimers.join(" ");
    }
    return "Research audit interface only. Not legal advice. Human legal review required.";
  }, [bundle]);

  if (!bundle) {
    return (
      <div className="v2-shell">
        <Loading />
      </div>
    );
  }

  return (
    <div className="v2-shell">
      {/* Header */}
      <header className="v2-header">
        <div className="v2-header__top">
          <div className="v2-header__brand">
            <div className="v2-header__logo">BA</div>
            <div>
              <div className="v2-header__title">BenchAssist-IL Audit</div>
              <div className="v2-header__subtitle">
                Detention / Remand Decision-Support Audit ·{" "}
                {bundle.dataStatus === "gemini_minimal_address" ? "Gemini Minimal Address" : bundle.dataStatus}
              </div>
            </div>
          </div>
          <div className="v2-header__actions">
            <span className="v2-badge v2-badge--info">
              {bundle.runManifest?.schema_version ?? "minimal_dangerousness_v2"}
            </span>
            <span className="v2-badge v2-badge--neutral">
              {bundle.runManifest?.model ?? "gemini-2.5-flash-lite"}
            </span>
          </div>
        </div>
      </header>

      {/* Disclaimer */}
      <div className="v2-disclaimer">
        <span className="v2-disclaimer__icon"><IconScale /></span>
        <span>{disclaimer}</span>
      </div>

      {/* Tab Navigation */}
      <nav className="v2-tab-nav" aria-label="Dashboard sections">
        {DASHBOARD_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`v2-tab ${activeTab === tab.id ? "v2-tab--active" : ""}`}
            onClick={() => navigateTab(tab.id)}
            aria-selected={activeTab === tab.id}
            role="tab"
          >
            <span className="v2-tab__label">
              {tab.icon} {tab.label}
            </span>
            <span className="v2-tab__sub">{tab.subtitle}</span>
          </button>
        ))}
      </nav>

      {/* Main Content */}
      <main className="v2-main v2-fade-in" key={activeTab}>
        {activeTab === "overview" && (
          <OverviewPage bundle={bundle} onNavigate={navigateTab} />
        )}
        {activeTab === "fairness" && (
          <FairnessScreeningPage bundle={bundle} />
        )}
        {activeTab === "mitigation" && (
          <PromptMitigationPage bundle={bundle} />
        )}
        {activeTab === "case-explorer" && (
          <CaseExplorerPage bundle={bundle} />
        )}
        {activeTab === "run-metadata" && (
          <RunMetadataPage bundle={bundle} />
        )}
      </main>

      {/* Footer */}
      <footer style={{ 
        borderTop: "1px solid var(--v2-border)", 
        paddingTop: "1rem", 
        marginTop: "2rem",
        fontSize: "0.78rem",
        color: "var(--v2-text-muted)",
        textAlign: "center",
      }}>
        <p>
          BenchAssist-IL Audit Dashboard · Research tool for AI fairness review · Not legal advice
        </p>
        {bundle.overview.disclaimers && (
          <ul className="v2-disclaimers" style={{ justifyContent: "center", marginTop: "0.5rem" }}>
            {bundle.overview.disclaimers.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        )}
      </footer>
    </div>
  );
}
