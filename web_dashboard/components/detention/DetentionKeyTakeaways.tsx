"use client";

import { Card } from "@/components/Card";
import { StatusPill } from "@/components/StatusPill";
import type { DetentionTakeaway } from "@/lib/detentionTakeaways";
import type { DetentionTab } from "@/lib/detentionNavigation";

export function DetentionKeyTakeaways({
  takeaways,
  onViewCases,
}: {
  takeaways: DetentionTakeaway[];
  onViewCases: (t: DetentionTakeaway) => void;
}) {
  return (
    <div className="takeaways-grid">
      {takeaways.map((t) => (
        <Card key={t.id} title={t.headline}>
          <p><strong>What changed:</strong> {t.whatChanged}</p>
          <p><strong>Why it matters legally:</strong> {t.whyItMatters}</p>
          <p className="muted">Affected variants/groups: {t.affectedGroups}</p>
          <div className="takeaway-meta">
            <StatusPill label={`Evidence: ${t.evidenceLevel}`} variant="info" />
            <StatusPill label={`Review priority: ${t.reviewPriority}`} variant={t.reviewPriority === "High" ? "concern" : "caution"} />
          </div>
          <p className="caution-line">{t.caution}</p>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => onViewCases(t)}>
            View relevant cases
          </button>
        </Card>
      ))}
    </div>
  );
}
