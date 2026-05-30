"use client";

import { Card } from "@/components/Card";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { formatCount, toBool } from "@/lib/format";

export function DetentionIdentityAuditSection({
  bundle,
  onReviewCases,
}: {
  bundle: DetentionDashboardBundle;
  onReviewCases?: () => void;
}) {
  const identity = bundle.flagged.filter((r) => toBool(r.identity_leakage_flag));
  const unsupported = bundle.flagged.filter((r) => toBool(r.unsupported_risk_inference_flag));
  const proxyVariants = bundle.groupSummary.filter((g) => {
    const vt = String(g.variant_type || "");
    return vt.includes("name") || vt.includes("proxy") || vt.includes("intersectional");
  });

  if (!identity.length && !unsupported.length) return null;

  return (
    <section className="section-card identity-audit-section">
      <h3>Identity &amp; proxy signals</h3>
      <p className="muted section-intro">
        Screening for identity/proxy language and unsupported inferences — audit signals only, not proof of discrimination.
      </p>
      <div className="findings-grid">
        <Card title="Identity / proxy leakage">
          <p className="stat-large">{formatCount(identity.length)}</p>
          <p className="muted">Comparisons where model reasoning may reference identity or proxy cues.</p>
        </Card>
        <Card title="Unsupported risk inference">
          <p className="stat-large">{formatCount(unsupported.length)}</p>
          <p className="muted">Risk assessments that may not be grounded in stated legal facts.</p>
        </Card>
        <Card title="Identity-sensitive variant groups">
          <p className="stat-large">{formatCount(proxyVariants.length)}</p>
          <p className="muted">Variant types testing names, proxies, or intersectional cues.</p>
        </Card>
      </div>
      {onReviewCases ? (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onReviewCases}>
          Review identity-flagged cases
        </button>
      ) : null}
    </section>
  );
}
