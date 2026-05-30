"use client";

import { StatusPill } from "@/components/StatusPill";
import { assessDetentionReadiness } from "@/lib/detentionReadiness";
import type { DetentionDashboardBundle } from "@/lib/detentionData";

export function DetentionReadinessPanel({ bundle }: { bundle: DetentionDashboardBundle }) {
  const report = assessDetentionReadiness(bundle);

  return (
    <div className="readiness-panel">
      <div className="readiness-header">
        <h3>Dashboard readiness</h3>
        <StatusPill
          label={report.readyForGeminiPilotReview ? "Dashboard ready for expert review: Yes" : "Dashboard ready for expert review: No"}
          variant={report.readyForGeminiPilotReview ? "success" : "caution"}
        />
      </div>
      <ul className="readiness-checks">
        {report.checks.map((c) => (
          <li key={c.id} className={c.ok ? "check-ok" : "check-miss"}>
            <span aria-hidden="true">{c.ok ? "✓" : "○"}</span>
            <span>{c.label}</span>
            <span className="muted">{c.detail}</span>
          </li>
        ))}
      </ul>
      {report.missingRecommended.length ? (
        <p className="readiness-missing">
          <strong>Missing recommended files:</strong> {report.missingRecommended.join(", ")}
        </p>
      ) : null}
    </div>
  );
}
