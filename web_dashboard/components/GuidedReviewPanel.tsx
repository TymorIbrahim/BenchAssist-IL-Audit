"use client";

import { useCallback, useEffect, useState } from "react";
import { scrollToSection } from "@/lib/navigation";

const STORAGE_KEY = "benchassist-guided-review-v1";

export const GUIDED_STEPS = [
  { id: "understand", section: "overview", title: "Understand the system", text: "Read the disclaimer, run summary, and how this toy audit is scoped. Confirm you are reviewing screening signals, not legal conclusions." },
  { id: "main-signals", section: "main-findings", title: "Review main audit signals", text: "Inspect aggregate rates by variant type. Note which dimensions (remedy, evidence, credibility) shift most often." },
  { id: "flagged", section: "flagged-cases", title: "Inspect flagged cases", text: "Triage flagged comparisons by review priority. Read strongest signals and validity category before opening Case Explorer." },
  { id: "explorer", section: "case-explorer", title: "Compare neutral vs variant", text: "Use side-by-side memos and the What changed panel. Ask whether differences are legally justified." },
  { id: "validity", section: "counterfactual-validity", title: "Check validity", text: "Confirm whether variants preserved legal facts. Stress tests need cautious interpretation." },
  { id: "safety", section: "stereotype", title: "Check stereotype and hallucination risks", text: "Review identity leakage and grounding flags where exported. These are separate safety dimensions." },
  { id: "human", section: "human-review", title: "Decide what human reviewers should inspect", text: "Use reviewer questions and download packets for cases that need expert follow-up." },
] as const;

function loadProgress(): Record<string, boolean> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function GuidedReviewPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [progress, setProgress] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setProgress(loadProgress());
  }, [open]);

  const toggle = useCallback((id: string, checked: boolean) => {
    setProgress((prev) => {
      const next = { ...prev, [id]: checked };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  if (!open) return null;

  const done = GUIDED_STEPS.filter((s) => progress[s.id]).length;

  return (
    <div className="guided-panel" role="region" aria-label="Guided review">
      <div className="guided-header">
        <h3>Guided review</h3>
        <span className="guided-progress">{done} / {GUIDED_STEPS.length} completed</span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
      </div>
      <ol className="guided-steps">
        {GUIDED_STEPS.map((step, i) => (
          <li key={step.id} className={progress[step.id] ? "step-done" : ""}>
            <div className="guided-step-head">
              <strong>Step {i + 1} — {step.title}</strong>
              <label className="checkbox-label">
                <input type="checkbox" checked={!!progress[step.id]} onChange={(e) => toggle(step.id, e.target.checked)} />
                Mark step as reviewed
              </label>
            </div>
            <p>{step.text}</p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => scrollToSection(step.section)}>Go to section</button>
          </li>
        ))}
      </ol>
    </div>
  );
}
