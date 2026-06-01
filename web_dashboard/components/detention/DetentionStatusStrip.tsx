"use client";

import { StatusPill } from "@/components/StatusPill";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { detentionDataModeLabel } from "@/lib/detentionMetrics";

export function DetentionStatusStrip({ bundle }: { bundle: DetentionDashboardBundle }) {
  const policy = bundle.dataAccessPolicy;
  const accessRequired = Boolean(
    policy.requires_access_control ?? policy.contains_unredacted_public_legal_text ?? bundle.hasFullText,
  );

  return (
    <div className="status-strip" role="status" aria-label="Dashboard status">
      <StatusPill label={`Data mode: ${detentionDataModeLabel(bundle)}`} variant="info" />
      <StatusPill label="Use case: Detention/remand" variant="neutral" />
      <StatusPill label="Strict fairness: Synthetic only" variant="neutral" />
      <StatusPill label="Flagging: Dangerousness Δ only" variant="neutral" />
      <StatusPill label={`Full text present: ${bundle.hasFullText ? "Yes" : "No"}`} variant={bundle.hasFullText ? "caution" : "neutral"} />
      <StatusPill label={`Access control required: ${accessRequired ? "Yes" : "No"}`} variant={accessRequired ? "caution" : "neutral"} />
    </div>
  );
}
