"use client";

import { StatusPill } from "./StatusPill";
import { scrollToSection } from "@/lib/navigation";

const SUMMARY =
  "We test whether the model changes the legal framing of the same housing dispute when names, language style, demographic cues, intersectional cues, or narrative framing change.";

const BADGES = [
  "Not legal advice",
  "Not an AI judge",
  "Synthetic audit setting",
  "Human legal review required",
];

const REVIEWER_PATH = [
  { section: "main-findings", label: "View main findings" },
  { section: "flagged-cases", label: "Inspect flagged cases" },
  { section: "case-explorer", label: "Compare a case" },
  { section: "reports", label: "Open final report" },
];

export function ExecutiveLanding({ onOpenPresentation }: { onOpenPresentation?: () => void }) {
  return (
    <div className="executive-landing">
      <header className="executive-header">
        <h1 className="executive-title">BenchAssist-IL Audit</h1>
        <p className="executive-subtitle">
          A Responsible AI audit of a toy, non-binding judicial bench-memo assistant for Israeli housing disputes.
        </p>
        <p className="executive-summary">{SUMMARY}</p>
      </header>

      <div className="trust-badge-row">
        {BADGES.map((b) => (
          <StatusPill key={b} label={b} variant="caution" />
        ))}
      </div>

      <div className="reviewer-path-panel">
        <h2>Open reviewer path</h2>
        <p className="muted">Jump directly to the sections most useful for legal and RAI review.</p>
        <div className="reviewer-path-buttons">
          {REVIEWER_PATH.map((item) => (
            <button key={item.section} type="button" className="btn btn-secondary" onClick={() => scrollToSection(item.section)}>
              {item.label}
            </button>
          ))}
        </div>
        <p className="best-start muted">
          <strong>Best starting point:</strong> If you only have five minutes, review Main Findings, open one high-priority flagged case, and read Methodology & limitations.
        </p>
        {onOpenPresentation ? (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenPresentation}>Open presentation panel</button>
        ) : null}
      </div>
    </div>
  );
}
