"use client";

import { useState } from "react";
import { Card } from "@/components/Card";
import { StatusPill } from "@/components/StatusPill";
import type { JsonRecord } from "@/lib/types";
import { str } from "@/lib/format";

const GUIDED_STEPS = [
  { id: 1, title: "Choose issue type", desc: "Select the audit signal category you want to review first." },
  { id: 2, title: "Review top flagged cases", desc: "Start with high-priority cases in the triage board." },
  { id: 3, title: "Compare neutral vs variant", desc: "Use the case comparison workspace for side-by-side review." },
  { id: 4, title: "Answer checklist", desc: "Complete the legal reviewer checklist for each case." },
  { id: 5, title: "Add to packet", desc: "Add cases worth discussing to your reviewer packet." },
  { id: 6, title: "Export packet", desc: "Export JSON, CSV, or Markdown for your legal meeting." },
];

export function DetentionGuidedReview({
  flagged,
  issueTypes,
  onStartReview,
  onExportPacket,
  packetCount,
}: {
  flagged: JsonRecord[];
  issueTypes: string[];
  onStartReview: (issueType: string) => void;
  onExportPacket: () => void;
  packetCount: number;
}) {
  const [issueType, setIssueType] = useState("");
  const [step, setStep] = useState(1);

  const highCount = flagged.filter((r) => str(r.review_priority) === "High").length;

  return (
    <div className="guided-review-detention">
      <div className="guided-steps-bar">
        {GUIDED_STEPS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`guided-step-pill ${step === s.id ? "active" : step > s.id ? "done" : ""}`}
            onClick={() => setStep(s.id)}
          >
            {s.id}. {s.title}
          </button>
        ))}
      </div>

      <Card title={GUIDED_STEPS[step - 1]?.title ?? "Guided review"}>
        <p>{GUIDED_STEPS[step - 1]?.desc}</p>

        {step === 1 ? (
          <>
            <label>Issue type
              <select value={issueType} onChange={(e) => setIssueType(e.target.value)}>
                <option value="">All issue types</option>
                {issueTypes.map((t) => <option key={t} value={t}>{t.slice(0, 80)}</option>)}
              </select>
            </label>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => { onStartReview(issueType); setStep(2); }}>Continue</button>
          </>
        ) : null}

        {step === 2 ? (
          <>
            <p><StatusPill label={`${highCount} high-priority cases`} variant="concern" /> · {flagged.length} total flagged</p>
            <p className="muted">Open the triage board below or switch to Case Review tab.</p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setStep(3)}>Continue to comparison</button>
          </>
        ) : null}

        {step >= 3 && step <= 5 ? (
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setStep(step + 1)}>Next step</button>
        ) : null}

        {step === 6 ? (
          <>
            <p>{packetCount} case(s) in your local reviewer packet.</p>
            <button type="button" className="btn btn-primary btn-sm" onClick={onExportPacket}>Export reviewer packet</button>
          </>
        ) : null}
      </Card>
    </div>
  );
}
