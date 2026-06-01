"use client";

import { useState } from "react";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { detentionHeadlineMetrics } from "@/lib/detentionMetrics";
import { formatCount } from "@/lib/format";
import type { Manifest } from "@/lib/types";

export function DetentionExportMetadataPanel({ bundle }: { bundle: DetentionDashboardBundle }) {
  const [open, setOpen] = useState(false);
  const { manifest, overview, caseReviewMeta } = bundle;
  const m = manifest as Manifest;
  const provenance = m.export_provenance;
  const headline = detentionHeadlineMetrics(bundle);
  const uniquePairs = bundle.pairwise.length;
  const dedupeNote =
    manifest.row_counts?.["detention_pairwise_comparison.json"] &&
    manifest.row_counts["detention_pairwise_comparison.json"] > uniquePairs
      ? ` (${formatCount(manifest.row_counts["detention_pairwise_comparison.json"])} raw export rows deduped to ${formatCount(uniquePairs)} unique pairs)`
      : "";
  const completeness = m.export_completeness_score;
  const missingDetail = m.missing_optional_files_detail ?? [];

  return (
    <section className="section-card export-metadata-panel">
      <button type="button" className="expandable-section-header" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <h3>Export metadata &amp; provenance</h3>
        <span className="expand-chevron">{open ? "−" : "+"}</span>
      </button>
      {open ? (
        <dl className="meta-dl meta-dl-stack">
          {completeness != null ? (
            <div>
              <dt>Export completeness</dt>
              <dd>
                {completeness}/100
                {m.deploy_blocked ? " · deploy blocked (critical exports missing)" : m.critical_exports_ok ? " · critical exports OK" : ""}
              </dd>
            </div>
          ) : null}
          <div><dt>Exported at</dt><dd>{manifest.timestamp || caseReviewMeta?.exported_at || "—"}</dd></div>
          <div><dt>Data status</dt><dd>{bundle.dataStatus.replace(/_/g, " ")}</dd></div>
          <div><dt>Run label</dt><dd>{String(manifest.run_label || "—")}</dd></div>
          <div><dt>Experiment</dt><dd>{String(manifest.experiment_token || "—")}</dd></div>
          <div><dt>Pairwise comparisons</dt><dd>{formatCount(overview.n_pairwise_comparisons ?? headline.pairwiseCount)}{dedupeNote}</dd></div>
          <div><dt>Flagged comparisons</dt><dd>{formatCount(overview.n_flagged_comparisons ?? headline.flaggedCount)}</dd></div>
          {headline.usesBaselineHeadline ? (
            <div><dt>All prompt modes</dt><dd>{formatCount(headline.pairwiseCountAllModes)} comparisons · {formatCount(headline.flaggedCountAllModes)} flagged</dd></div>
          ) : null}
          {provenance?.headline_metrics_note || overview.methodology_note ? (
            <div>
              <dt>Headline metrics</dt>
              <dd className="muted small">{provenance?.headline_metrics_note || String(overview.methodology_note)}</dd>
            </div>
          ) : null}
          <div><dt>Case review records</dt><dd>{formatCount(bundle.caseReviewIndexCount || bundle.caseReviewRecords.length)}{bundle.caseReviewSplit || provenance?.case_review_split ? " (split per-record JSON)" : ""}</dd></div>
          <div><dt>Strict-excluded outputs</dt><dd>{formatCount(overview.n_strict_excluded_review_outputs ?? 0)}</dd></div>
          <div><dt>Address-proxy outputs</dt><dd>{formatCount(overview.n_address_proxy_review_outputs ?? overview.n_strict_excluded_review_outputs ?? 0)}</dd></div>
          <div><dt>Schema version</dt><dd>{String(manifest.schema_version || overview.schema_version || "—")}</dd></div>
          {provenance?.export_git_sha || provenance?.git_commit ? (
            <div><dt>Export git commit</dt><dd><code>{provenance.export_git_sha || provenance.git_commit}</code></dd></div>
          ) : null}
          {provenance?.parent_run_id ? (
            <div><dt>Parent run</dt><dd><code>{provenance.parent_run_id}</code></dd></div>
          ) : null}
          {provenance?.corpus_version ? (
            <div><dt>Corpus version</dt><dd><code>{provenance.corpus_version}</code></dd></div>
          ) : null}
          {provenance?.flagging_policy ? (
            <div><dt>Flagging policy</dt><dd><code>{provenance.flagging_policy}</code>{provenance.flagging_policy_doc ? <> · <code>{provenance.flagging_policy_doc}</code></> : null}</dd></div>
          ) : null}
          {provenance?.dashboard_export_profile ? (
            <div><dt>Export profile</dt><dd>{provenance.dashboard_export_profile === "demo_redacted" ? "Demo (case text redacted)" : "Full (includes case text)"}</dd></div>
          ) : null}
          {provenance?.pairwise_unique_note ? (
            <div><dt>Pairwise dedupe</dt><dd>{provenance.pairwise_unique_note}</dd></div>
          ) : null}
          {manifest.selected_source_files?.["parsed_outputs.jsonl"] ? (
            <div>
              <dt>Model outputs</dt>
              <dd><code>{String(manifest.selected_source_files["parsed_outputs.jsonl"])}</code></dd>
            </div>
          ) : null}
          {missingDetail.length ? (
            <div>
              <dt>Missing optional files</dt>
              <dd>
                <ul className="missing-files-impact-list">
                  {missingDetail.map((row) => (
                    <li key={row.file}>
                      <code>{row.file}</code> — {row.tabs_affected}. {row.effect}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          ) : manifest.missing_optional_files?.length ? (
            <div><dt>Missing optional files</dt><dd>{manifest.missing_optional_files.join(", ")}</dd></div>
          ) : null}
        </dl>
      ) : (
        <p className="muted section-intro">
          Run ID, export time, completeness score, and dedupe notes for expert trust.
          {completeness != null ? ` Completeness: ${completeness}/100.` : ""}
        </p>
      )}
    </section>
  );
}
