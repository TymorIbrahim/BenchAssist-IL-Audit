"use client";

import { DETENTION_TABS, type DetentionTab } from "@/lib/detentionNavigation";

export function DetentionTabNav({
  activeTab,
  onTabChange,
}: {
  activeTab: DetentionTab;
  onTabChange: (tab: DetentionTab) => void;
}) {
  return (
    <nav className="detention-tab-nav" aria-label="Dashboard sections">
      {DETENTION_TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`detention-tab ${activeTab === tab.id ? "detention-tab-active" : ""}`}
          onClick={() => onTabChange(tab.id)}
          aria-current={activeTab === tab.id ? "page" : undefined}
        >
          {tab.icon ? <span className="detention-tab-icon" aria-hidden>{tab.icon}</span> : null}
          <span className="detention-tab-label">{tab.label}</span>
          <span className="detention-tab-sub">{tab.subtitle}</span>
        </button>
      ))}
    </nav>
  );
}
