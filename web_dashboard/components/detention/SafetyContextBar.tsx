"use client";

import { useState } from "react";
import type { DetentionDashboardBundle } from "@/lib/detentionData";

interface SafetyChip {
  id: string;
  label: string;
  detail: string;
}

function buildChips(bundle: DetentionDashboardBundle): SafetyChip[] {
  const chips: SafetyChip[] = [
    {
      id: "research",
      label: "Research only",
      detail: "This dashboard supports Responsible AI audit research and expert review. It does not provide legal advice or make detention decisions.",
    },
    {
      id: "not-advice",
      label: "Not legal advice",
      detail: "Outputs are non-binding audit signals from a toy decision-support assistant. Not an AI judge.",
    },
    {
      id: "synthetic",
      label: "Synthetic strict audit",
      detail: "Strict fairness metrics use synthetic counterfactual rows only, where legally relevant facts are held constant.",
    },
    {
      id: "real-excluded",
      label: "Real cases excluded from strict rates",
      detail: "Real Israeli public legal examples support realism and legal reliability review. They are not included in strict synthetic fairness rates.",
    },
  ];
  if (bundle.hasFullText) {
    chips.push({
      id: "access",
      label: "Access control required",
      detail: "Full unredacted legal text is present for internal expert review. Deploy only behind access control. Do not rely on URL secrecy.",
    });
  }
  return chips;
}

export function SafetyContextBar({ bundle }: { bundle: DetentionDashboardBundle }) {
  const [open, setOpen] = useState(false);
  const chips = buildChips(bundle);

  return (
    <>
      <div className="safety-context-bar" role="region" aria-label="Safety and methodology context">
        <div className="safety-context-chips">
          {chips.map((chip) => (
            <button
              key={chip.id}
              type="button"
              className="safety-chip"
              onClick={() => setOpen(true)}
              title={chip.detail}
            >
              {chip.label}
            </button>
          ))}
        </div>
        <button type="button" className="btn btn-ghost btn-sm safety-details-btn" onClick={() => setOpen(true)}>
          Why this matters
        </button>
      </div>

      {open ? (
        <div className="drawer-backdrop" role="presentation" onClick={() => setOpen(false)}>
          <aside
            className="methodology-drawer"
            role="dialog"
            aria-labelledby="safety-drawer-title"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="drawer-header">
              <h2 id="safety-drawer-title">Safety & methodology</h2>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setOpen(false)} aria-label="Close">
                Close
              </button>
            </header>
            <div className="drawer-body">
              <p className="drawer-lead">
                This dashboard is for research and expert review. It does not provide legal advice or make detention decisions.
              </p>
              {chips.map((chip) => (
                <details key={chip.id} className="drawer-detail" open={chip.id === "research"}>
                  <summary>{chip.label}</summary>
                  <p>{chip.detail}</p>
                </details>
              ))}
              <details className="drawer-detail">
                <summary>Metrics are audit signals</summary>
                <p>
                  Findings may indicate possible concerns requiring human legal review. They are not proof of unlawful
                  discrimination and must not be treated as final legal conclusions.
                </p>
              </details>
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}
