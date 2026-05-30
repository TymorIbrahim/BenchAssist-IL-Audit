"use client";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import { PageHeader } from "@/components/detention/PageHeader";
import { DetentionLegalTextViewer } from "@/components/detention/DetentionLegalTextViewer";
import { str, toBool } from "@/lib/format";
import type { DetentionFilterState } from "@/lib/detentionFilters";
import type { JsonRecord } from "@/lib/types";

export function DetentionRealCasePage({
  filteredRealCases,
  selectedRealCase,
  onSelectRealCase,
  realCaseNotes,
  onNotesChange,
  realCasePacketIds,
  onToggleRealCasePacket,
  filters,
  onFilterChange,
}: {
  filteredRealCases: JsonRecord[];
  selectedRealCase: JsonRecord | null;
  onSelectRealCase: (row: JsonRecord | null) => void;
  realCaseNotes: Record<string, string>;
  onNotesChange: (sourceId: string, notes: string) => void;
  realCasePacketIds?: string[];
  onToggleRealCasePacket?: (sourceId: string) => void;
  filters: DetentionFilterState;
  onFilterChange: (f: DetentionFilterState) => void;
}) {
  return (
    <div className="tab-panel">
      <PageHeader
        title="Real Case Review"
        subtitle="Legal document review for realism and reliability — not included in strict synthetic fairness rates."
        badges={[{ label: "Excluded from strict rates", variant: "success" }]}
      />

      {filteredRealCases.length ? (
        <>
          <div className="real-case-toolbar">
            <label className="select-label">
              Source browser
              <select
                value={str(selectedRealCase?.source_id)}
                onChange={(e) => onSelectRealCase(filteredRealCases.find((r) => str(r.source_id) === e.target.value) ?? null)}
              >
                <option value="">Select a case…</option>
                {filteredRealCases.map((r) => (
                  <option key={str(r.source_id)} value={str(r.source_id)}>
                    {str(r.source_id)} — {str(r.likely_case_stage).replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={filters.fullTextRealCases}
                onChange={(e) => onFilterChange({ ...filters, fullTextRealCases: e.target.checked })}
              />
              Full text only
            </label>
          </div>

          {selectedRealCase ? (
            <Card title={str(selectedRealCase.title) || str(selectedRealCase.source_id)}>
              <div className="real-case-meta-row">
                <StatusPill label={str(selectedRealCase.likely_case_stage).replace(/_/g, " ") || "Stage unknown"} variant="info" />
                {toBool(selectedRealCase.sensitive_content_flag ?? selectedRealCase.sensitive_flag) ? <StatusPill label="Sensitive" variant="caution" /> : null}
                <StatusPill label={`Expert: ${str(selectedRealCase.expert_review_status) || "not reviewed"}`} variant="neutral" />
                <StatusPill label={toBool(selectedRealCase.expert_approved_for_dashboard) ? "Approved" : "Pending approval"} variant={toBool(selectedRealCase.expert_approved_for_dashboard) ? "success" : "caution"} />
              </div>
              <dl className="meta-dl">
                <div><dt>Source dataset</dt><dd>{str(selectedRealCase.source_dataset)}</dd></div>
                <div><dt>Source ID</dt><dd>{str(selectedRealCase.source_id)}</dd></div>
                <div><dt>Citation summary</dt><dd>{str(selectedRealCase.citation_summary || selectedRealCase.source_url).slice(0, 200)}</dd></div>
              </dl>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => void navigator.clipboard.writeText(`${str(selectedRealCase.source_id)} — ${str(selectedRealCase.source_dataset)}`)}
              >
                Copy source summary
              </button>
              {onToggleRealCasePacket ? (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onToggleRealCasePacket(str(selectedRealCase.source_id))}
                >
                  {realCasePacketIds?.includes(str(selectedRealCase.source_id)) ? "Remove from packet" : "Add to review packet"}
                </button>
              ) : null}
              <DetentionLegalTextViewer
                row={selectedRealCase}
                notes={realCaseNotes[str(selectedRealCase.source_id)] ?? ""}
                onNotesChange={(n) => onNotesChange(str(selectedRealCase.source_id), n)}
              />
            </Card>
          ) : (
            <EmptyState title="Select a real case" description="Choose a source from the browser to view full legal text and add expert notes." />
          )}
        </>
      ) : (
        <EmptyState
          title="No real-case examples"
          description="Export detention_real_case_examples_fulltext.json for the legal source review workspace."
          command="python -m benchassist.vercel_export --auto --use-case detention --run-dir results/gemini/detention_full --data-status gemini_full"
        />
      )}
    </div>
  );
}
