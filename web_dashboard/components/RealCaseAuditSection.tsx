"use client";

import { Callout } from "./Callout";
import { Card } from "./Card";
import { DataTable } from "./DataTable";
import { EmptyState } from "./EmptyState";
import { StatCard } from "./MetricCard";
import { str } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";

const DOMAIN_LABELS: Record<string, string> = {
  housing: "Housing",
  labor_employment: "Labor & employment",
  social_benefits_welfare: "Social benefits & welfare",
  immigration_status: "Immigration & status",
  consumer_small_claims: "Consumer & small claims",
  accessibility_disability_rights: "Accessibility & disability rights",
  criminal_detention_remand: "Detention / remand (internal expert review)",
};

export function RealCaseAuditSection({
  domainSummary,
  auditSummary,
  auditOutputs,
  examples,
  limitations,
  sourceDataset,
}: {
  domainSummary: JsonRecord[];
  auditSummary: JsonRecord[];
  auditOutputs: JsonRecord[];
  examples: JsonRecord[];
  limitations?: string;
  sourceDataset?: string;
}) {
  const hasData = examples.length > 0 || auditSummary.length > 0;

  if (!hasData) {
    return (
      <EmptyState
        title="Real-case-inspired audit not exported"
        description="Run real-case ingestion, mock batch, real_case_audit, then vercel_export."
        command="python -m benchassist.real_case_ingestion --source local_jsonl --input tests/fixtures/legal_training_sample.jsonl --output-dir data/real_cases"
      />
    );
  }

  const domainCards = domainSummary.length
    ? domainSummary
    : Object.entries(
        examples.reduce<Record<string, number>>((acc, r) => {
          const d = str(r.normalized_domain) || "unknown";
          acc[d] = (acc[d] || 0) + 1;
          return acc;
        }, {}),
      ).map(([normalized_domain, n_examples]) => ({ normalized_domain, n_examples }));

  return (
    <div className="real-case-audit">
      <Callout title="Purpose" variant="info">
        These examples make the audit more realistic and cover more legal domains.
        They are <strong>not</strong> the main strict counterfactual fairness test.
        Results are realism and robustness signals — not proof of discrimination.
      </Callout>

      <div className="stat-grid">
        <StatCard label="Examples exported" value={String(examples.length)} sub="Real-case-inspired" />
        <StatCard label="Domains" value={String(domainCards.length)} sub="Multi-domain coverage" />
        <StatCard label="Source dataset" value={sourceDataset || "—"} sub="Public/licensed material" />
      </div>

      <Card title="Domain coverage">
        <div className="classification-grid">
          {domainCards.map((d) => (
            <div key={str(d.normalized_domain)} className="classification-card">
              <strong>{DOMAIN_LABELS[str(d.normalized_domain)] || str(d.normalized_domain).replace(/_/g, " ")}</strong>
              <p className="muted">{String((d as JsonRecord).n_examples ?? (d as JsonRecord).n_outputs ?? 0)} example(s)</p>
            </div>
          ))}
        </div>
      </Card>

      {auditSummary.length ? (
        <Card title="Domain-level model behavior">
          <DataTable
            rows={auditSummary}
            columns={[
              { key: "normalized_domain", label: "Domain" },
              { key: "n_outputs", label: "N outputs" },
              { key: "recommended_action_distribution", label: "Actions" },
              { key: "urgency_distribution", label: "Urgency" },
              { key: "parse_error_rate", label: "Parse errors" },
            ]}
          />
        </Card>
      ) : null}

      {examples.length ? (
        <Card title="Real-case examples">
          <DataTable
            rows={examples.slice(0, 50)}
            columns={[
              { key: "real_case_id", label: "ID", render: (r) => str(r.real_case_id || r.case_id) },
              { key: "normalized_domain", label: "Domain" },
              { key: "language", label: "Language" },
              { key: "source_dataset", label: "Source" },
              { key: "legal_question_or_issue", label: "Issue", render: (r) => str(r.legal_question_or_issue || r.input_text).slice(0, 120) },
            ]}
            emptyMessage="No examples match filters."
          />
        </Card>
      ) : null}

      {auditOutputs.length ? (
        <Card title="Qualitative outputs (sample)">
          <DataTable
            rows={auditOutputs.slice(0, 25)}
            columns={[
              { key: "case_id", label: "Case" },
              { key: "normalized_domain", label: "Domain" },
              { key: "recommended_action_type", label: "Action" },
              { key: "urgency", label: "Urgency" },
              { key: "confidence", label: "Confidence" },
            ]}
          />
        </Card>
      ) : null}

      <Callout title="Limitations" variant="caution">
        {limitations ||
          "Not strict counterfactual fairness evidence. Source-derived summaries may be imperfect. Legal correctness not certified. Human legal review required. Not legal advice."}
      </Callout>
    </div>
  );
}
