"use client";

import { useState } from "react";
import type { DetentionTab } from "@/lib/detentionNavigation";
import { RESEARCH_QUESTION } from "@/lib/detentionStory";

const TOUR_STEPS: { title: string; body: string; tab?: DetentionTab }[] = [
  { title: "Research question", body: RESEARCH_QUESTION, tab: "home" },
  { title: "Audit method", body: "Synthetic counterfactuals feed strict fairness metrics. Real cases are reviewed separately.", tab: "methodology" },
  { title: "Example comparison", body: "Open Case Review to compare neutral vs variant structured outputs side by side.", tab: "case-review" },
  { title: "Top audit signals", body: "Audit Results summarizes flagged comparisons and key takeaways.", tab: "audit-results" },
  { title: "Review a flagged case", body: "Use the triage board to open a case, complete the checklist, and add notes.", tab: "case-review" },
  { title: "Build your packet", body: "Add cases to the reviewer packet and export from Expert Workspace.", tab: "expert-workspace" },
];

export function DetentionGuidedTour({
  open,
  step,
  onStepChange,
  onClose,
  onGoToTab,
}: {
  open: boolean;
  step: number;
  onStepChange: (n: number) => void;
  onClose: () => void;
  onGoToTab: (tab: DetentionTab) => void;
}) {
  if (!open) return null;
  const current = TOUR_STEPS[step];
  const isLast = step >= TOUR_STEPS.length - 1;

  return (
    <div className="tour-backdrop" role="presentation" onClick={onClose}>
      <div className="tour-panel" role="dialog" aria-labelledby="tour-title" onClick={(e) => e.stopPropagation()}>
        <header className="tour-header">
          <span className="tour-progress">Step {step + 1} of {TOUR_STEPS.length}</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Skip tour</button>
        </header>
        <h2 id="tour-title">{current.title}</h2>
        <p>{current.body}</p>
        <div className="tour-actions">
          {current.tab ? (
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onGoToTab(current.tab!)}>
              Go to section
            </button>
          ) : null}
          {step > 0 ? (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => onStepChange(step - 1)}>Back</button>
          ) : null}
          {!isLast ? (
            <button type="button" className="btn btn-primary btn-sm" onClick={() => onStepChange(step + 1)}>Next</button>
          ) : (
            <button type="button" className="btn btn-primary btn-sm" onClick={onClose}>Finish</button>
          )}
        </div>
      </div>
    </div>
  );
}

export function useGuidedTour() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const start = () => { setStep(0); setOpen(true); };
  const close = () => setOpen(false);
  return { open, step, setStep, start, close };
}
