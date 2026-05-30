"use client";

import { useState } from "react";
import type { DetentionDashboardBundle } from "@/lib/detentionData";
import { formatCount } from "@/lib/format";

export function DetentionExportMetadataPanel({ bundle }: { bundle: DetentionDashboardBundle }) {
  const [open, setOpen] = useState(false);
  const { manifest, overview, caseReviewMeta } = bundle;
  const provenance = manifest.export_provenance;
  const uniquePairs = bundle.pairwise.length;
  const dedupeNote =
    manifest.row_counts?.["detention_pairwise_comparison.json"] &&
    manifest.row_counts["detention_pairwise_comparison.json"] > uniquePairs
      ? ` (${formatCount(manifest.row_counts["detention_pairwise_comparison.json"])} raw export rows deduped to ${formatCount(uniquePairs)} unique pairs)`
      : "";

  return (
    <section className="section-card export-metadata-panel">
      <button type="button" className="expandable-section-header" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <h3>Export metadata &amp; provenance</h3>
        <span className="expand-chevron">{open ? "−" : "+"}</span>
      </button>
      {open ? (
        <dl className="meta-dl meta-dl-stack">
          <div><dt>Exported at</dt><dd>{manifest.timestamp || caseReviewMeta?.exported_at || "—"}</dd></div>
          <div><dt>Data status</dt><dd>{bundle.dataStatus.replace(/_/g, " ")}</dd></div>
          <div><dt>Run label</dt><dd>{String(manifest.run_label || "—")}</dd></div>
          <div><dt>Experiment</dt><dd>{String(manifest.experiment_token || "—")}</dd></div>
          <div><dt>Pairwise comparisons</dt><dd>{formatCount(overview.n_pairwise_comparisons ?? uniquePairs)}{dedupeNote}</dd></div>
          <div><dt>Flagged comparisons</dt><dd>{formatCount(overview.n_flagged_comparisons ?? bundle.flagged.length)}</dd></div>
          <div><dt>Case review records</dt><dd>{formatCount(bundle.caseReviewIndexCount || bundle.caseReviewRecords.length)}{bundle.caseReviewSplit || provenance?.case_review_split ? " (split per-record JSON)" : ""}</dd></div>
          <div><dt>Real-case outputs</dt><dd>{formatCount(overview.n_real_case_review_outputs ?? 0)}</dd></div>
          {provenance?.git_commit ? (
            <div><dt>Export git commit</dt><dd><code>{provenance.git_commit}</code></dd></div>
          ) : null}
          {provenance?.pairwise_unique_note ? (
            <div><dt>Pairwise dedupe</dt><dd>{provenance.pairwise_unique_note}</dd></div>
          ) : null}
          {manifest.missing_optional_files?.length ? (
            <div><dt>Missing optional files</dt><dd>{manifest.missing_optional_files.join(", ")}</dd></div>
          ) : null}
        </dl>
      ) : (
        <p className="muted section-intro">Run ID, export time, row counts, and dedupe notes for expert trust.</p>
      )}
    </section>
  );
}
