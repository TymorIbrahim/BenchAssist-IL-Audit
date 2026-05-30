"use client";

import { useEffect, useState } from "react";
import { ALL_NAV_SECTIONS, NAV_GROUPS, type NavGroup } from "@/lib/navigationGroups";
import type { Manifest } from "@/lib/types";
import { RunSummary } from "./RunSummary";

export function Sidebar({
  manifest,
  activeSection,
  onGlossary,
  navGroups = NAV_GROUPS,
  brandSubtitle = "Legal research audit",
}: {
  manifest: Manifest;
  activeSection: string;
  onGlossary?: () => void;
  navGroups?: NavGroup[];
  brandSubtitle?: string;
}) {
  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <aside className="sidebar" aria-label="Dashboard navigation">
      <div className="sidebar-brand">
        <strong>BenchAssist-IL</strong>
        <span>{brandSubtitle}</span>
      </div>
      <nav aria-label="Section navigation">
        {navGroups.map((group) => (
          <div key={group.title} className="nav-group">
            <div className="nav-group-title">{group.title}</div>
            <ul className="nav-list">
              {group.sections.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className={activeSection === s.id ? "nav-active" : ""}
                    onClick={() => scrollTo(s.id)}
                    aria-current={activeSection === s.id ? "true" : undefined}
                  >
                    <span className="nav-label">{s.label}</span>
                    {s.subtitle ? <span className="nav-subtitle">{s.subtitle}</span> : null}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <RunSummary manifest={manifest} />
      {onGlossary ? (
        <button type="button" className="btn btn-ghost btn-sm glossary-btn" onClick={onGlossary}>Glossary</button>
      ) : null}
      <button type="button" className="back-to-top" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
        Back to top
      </button>
    </aside>
  );
}

export function useActiveSection(sectionIds: string[] = ALL_NAV_SECTIONS.map((s) => s.id)): string {
  const [active, setActive] = useState(sectionIds[0] ?? "");

  useEffect(() => {
    const visible = new Map<string, number>();

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          visible.set(entry.target.id, entry.intersectionRatio);
        }
        let bestId = sectionIds[0] ?? "";
        let bestRatio = 0;
        for (const id of sectionIds) {
          const ratio = visible.get(id) ?? 0;
          if (ratio > bestRatio) {
            bestRatio = ratio;
            bestId = id;
          }
        }
        if (bestRatio > 0) setActive(bestId);
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: [0, 0.1, 0.25, 0.5] },
    );

    for (const id of sectionIds) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [sectionIds]);

  return active;
}
