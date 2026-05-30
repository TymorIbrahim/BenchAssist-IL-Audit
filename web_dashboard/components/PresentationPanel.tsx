"use client";

import { Card } from "./Card";
import { scrollToSection } from "@/lib/navigation";
import type { DashboardData, JsonRecord } from "@/lib/types";
import { str } from "@/lib/format";

export function PresentationPanel({
  data,
  exampleCase,
  onOpenExample,
}: {
  data: DashboardData;
  exampleCase?: JsonRecord | null;
  onOpenExample?: () => void;
}) {
  const notes = data.reports.find((r) => r.report_name.includes("presentation"));

  return (
    <Card title="For presentation" className="presentation-panel">
      <h4>30-second summary</h4>
      <p>
        We audited a toy Israeli housing bench-memo assistant using synthetic cases and counterfactual variants.
        The dashboard shows screening signals — not legal conclusions — and flagged comparisons for human legal review.
      </p>
      <h4>1-minute summary</h4>
      <p>
        For each housing dispute, we compare neutral vs altered wording (names, language, demographics, narrative framing).
        We measure structured legal dimensions like remedy strength, evidence burden, and credibility framing.
        Flagged cases need expert review; validity checks tell you when comparisons must be interpreted cautiously.
      </p>
      <h4>Best sections to show live</h4>
      <ol className="presentation-live-path">
        {["overview", "audit-story", "main-findings", "case-explorer", "methodology"].map((id) => (
          <li key={id}><button type="button" className="link-button" onClick={() => scrollToSection(id)}>{id.replace(/-/g, " ")}</button></li>
        ))}
      </ol>
      <div className="btn-row">
        {notes ? (
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => scrollToSection("reports")}>Open presentation notes</button>
        ) : null}
        {exampleCase && onOpenExample ? (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onOpenExample}>
            Jump to example: {str(exampleCase.case_id)}
          </button>
        ) : null}
      </div>
    </Card>
  );
}
