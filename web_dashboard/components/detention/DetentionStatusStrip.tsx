"use client";

import { StatusPill } from "@/components/StatusPill";
import type { DetentionDashboardBundle } from "@/lib/detentionData";

function dataModeLabel(bundle: DetentionDashboardBundle): string {
  if (bundle.isMock) return "Mock";
  if (bundle.dataStatus === "gemini_full") return "Gemini full";
  if (bundle.dataStatus === "gemini") return "Gemini pilot";
  if (bundle.dataStatus === "pilot") return "Pilot";
  if (bundle.dataStatus === "final") return "Final";
  return "Awaiting export";
}

export function DetentionStatusStrip({ bundle }: { bundle: DetentionDashboardBundle }) {
  const policy = bundle.dataAccessPolicy;
  const accessRequired = Boolean(
    policy.requires_access_control ?? policy.contains_unredacted_public_legal_text ?? bundle.hasFullText,
  );

  return (
    <div className="status-strip" role="status" aria-label="Dashboard status">
      <StatusPill label={`Data mode: ${dataModeLabel(bundle)}`} variant="info" />
      <StatusPill label="Use case: Detention/remand" variant="neutral" />
      <StatusPill label="Strict fairness: Synthetic only" variant="neutral" />
      <StatusPill label="Real cases in strict rates: No" variant="success" />
      <StatusPill label={`Full text present: ${bundle.hasFullText ? "Yes" : "No"}`} variant={bundle.hasFullText ? "caution" : "neutral"} />
      <StatusPill label={`Access control required: ${accessRequired ? "Yes" : "No"}`} variant={accessRequired ? "caution" : "neutral"} />
    </div>
  );
}
