"use client";

import { IconWarning } from "@/components/v2/Icons";

import type { DashboardBundle } from "@/lib/v2/dataUtils";
import { formatRate, formatCount } from "@/lib/v2/dataUtils";
import { StatCard } from "./StatCard";
import { EmptyState } from "./EmptyState";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface RunMetadataPageProps {
  bundle: DashboardBundle;
}

/* ------------------------------------------------------------------ */
/*  Small helpers                                                      */
/* ------------------------------------------------------------------ */

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="v2-run-metadata-page__row">
      <dt>{label}</dt>
      <dd>{value ?? <span className="muted">—</span>}</dd>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function RunMetadataPage({ bundle }: RunMetadataPageProps) {
  const { runManifest, fullMetricSummary, overview } = bundle;

  /* ---------- warnings ---------- */
  const warnings: string[] = [];
  if (!runManifest) warnings.push("Run manifest data is missing.");
  if (!fullMetricSummary) warnings.push("Full metric summary data is missing.");
  if (bundle.isMock) warnings.push("Dashboard is running with mock / synthetic data.");
  if (overview.parse_success_rate < 1 && overview.parse_success_rate > 0) {
    warnings.push(
      `Parse success rate is ${formatRate(overview.parse_success_rate)} — some outputs failed to parse.`,
    );
  }
  if (overview.n_pairwise_comparisons_all_modes === 0 && bundle.pairwise.length === 0) {
    warnings.push("No pairwise comparisons found in the dataset.");
  }

  /* ---------- empty guard ---------- */
  if (!runManifest && !fullMetricSummary && !overview) {
    return (
      <section className="v2-run-metadata-page tab-panel">
        <div className="detention-page-header">
          <div className="page-header-body">
            <h1>Run Metadata &amp; Data Quality</h1>
            <p className="page-note">
              Configuration, parsing statistics, and data provenance
            </p>
          </div>
        </div>
        <EmptyState
          title="No metadata available"
          message="Run manifest and metric summary files are missing."
        />
      </section>
    );
  }

  return (
    <section className="v2-run-metadata-page tab-panel">
      {/* Header */}
      <div className="detention-page-header">
        <div className="page-header-body">
          <h1>Run Metadata &amp; Data Quality</h1>
          <p className="page-note">
            Configuration, parsing statistics, and data provenance
          </p>
        </div>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="v2-run-metadata-page__warnings">
          {warnings.map((w, i) => (
            <div key={i} className="callout callout-caution v2-run-metadata-page__warning-item">
              <IconWarning /> {w}
            </div>
          ))}
        </div>
      )}

      {/* Run configuration */}
      {runManifest && (
        <div className="section-card v2-run-metadata-page__section">
          <h3>Run Configuration</h3>
          <dl className="meta-dl">
            <MetaRow label="Model" value={runManifest.model} />
            <MetaRow label="Schema Version" value={runManifest.schema_version} />
            <MetaRow label="Config Path" value={<code>{runManifest.config_path}</code>} />
            <MetaRow
              label="Prompt Modes"
              value={
                runManifest.prompt_modes?.length ? (
                  <div className="chip-row">
                    {runManifest.prompt_modes.map((m) => (
                      <span key={m} className="badge badge-info">
                        {m}
                      </span>
                    ))}
                  </div>
                ) : (
                  "—"
                )
              }
            />
            <MetaRow label="Run Type" value={runManifest.run_type} />
            <MetaRow label="Generated At" value={runManifest.generated_at} />
          </dl>
          {runManifest.caution && (
            <p className="caution-line">{runManifest.caution}</p>
          )}
        </div>
      )}

      {/* Parse statistics */}
      <div className="section-card v2-run-metadata-page__section">
        <h3>Parse Statistics</h3>
        <div className="stat-grid">
          <StatCard
            label="Total Outputs"
            value={formatCount(
              runManifest?.stats?.completed ?? overview.n_outputs_total,
            )}
          />
          <StatCard
            label="Parse Successes"
            value={formatCount(
              runManifest?.stats?.parse_success ?? overview.n_parse_success,
            )}
          />
          <StatCard
            label="Parse Success Rate"
            value={formatRate(
              runManifest?.stats?.parse_success_rate ?? overview.parse_success_rate,
            )}
          />
          <StatCard
            label="Parse Errors"
            value={formatCount(runManifest?.stats?.parse_errors ?? 0)}
            sub={
              runManifest?.stats?.parse_errors
                ? "outputs could not be parsed"
                : undefined
            }
          />
        </div>
        {runManifest?.stats && (
          <dl className="meta-dl">
            <MetaRow label="Started At" value={runManifest.stats.started_at} />
            <MetaRow label="Finished At" value={runManifest.stats.finished_at} />
            <MetaRow
              label="Total Planned"
              value={formatCount(runManifest.stats.total_planned)}
            />
            <MetaRow
              label="Skipped (Resume)"
              value={formatCount(runManifest.stats.skipped_resume)}
            />
          </dl>
        )}
      </div>

      {/* Data counts */}
      <div className="section-card v2-run-metadata-page__section">
        <h3>Data Counts</h3>
        <div className="stat-grid">
          <StatCard
            label="Strict-Eligible Synthetic"
            value={formatCount(overview.n_strict_eligible_synthetic)}
          />
          <StatCard
            label="Address Proxy Outputs"
            value={formatCount(overview.n_address_proxy_outputs)}
          />
          <StatCard
            label="Pairwise Comparisons"
            value={formatCount(overview.n_pairwise_comparisons_all_modes || overview.n_pairwise_comparisons)}
          />
          <StatCard
            label="Flagged Comparisons"
            value={formatCount(overview.n_flagged_comparisons_all_modes || overview.n_flagged_comparisons)}
          />
          <StatCard
            label="Cross-Prompt Comparisons"
            value={formatCount(overview.n_cross_prompt_comparisons)}
          />
          <StatCard
            label="Cross-Prompt Instability Flags"
            value={formatCount(overview.n_cross_prompt_instability_flags)}
          />
        </div>
      </div>

      {/* Schema info */}
      {fullMetricSummary && (
        <div className="section-card v2-run-metadata-page__section">
          <h3>Schema Information</h3>
          <dl className="meta-dl">
            <MetaRow label="Schema Version" value={fullMetricSummary.schema_version} />
            <MetaRow
              label="Minimal Dangerousness Schema"
              value={
                fullMetricSummary.minimal_dangerousness_schema ? (
                  <span className="badge badge-info">Yes</span>
                ) : (
                  <span className="badge badge-neutral">No</span>
                )
              }
            />
            <MetaRow label="Legacy Metrics Status" value={fullMetricSummary.legacy_metrics_status} />
            <MetaRow label="Evidence Level" value={fullMetricSummary.evidence_level} />
            <MetaRow
              label="Address Proxy in Strict Rates"
              value={
                fullMetricSummary.address_proxy_in_strict_rates ? (
                  <span className="badge badge-caution">Included</span>
                ) : (
                  <span className="badge badge-success">Excluded</span>
                )
              }
            />
          </dl>
          {runManifest?.methodology && (
            <dl className="meta-dl">
              <MetaRow
                label="Strict Fairness Source"
                value={runManifest.methodology.strict_fairness_source}
              />
              <MetaRow
                label="Real Cases in Strict Rates"
                value={
                  runManifest.methodology.real_cases_in_strict_rates ? (
                    <span className="badge badge-caution">Yes</span>
                  ) : (
                    <span className="badge badge-neutral">No</span>
                  )
                }
              />
            </dl>
          )}
        </div>
      )}

      {/* Export timestamp */}
      {runManifest?.generated_at && (
        <div className="section-card v2-run-metadata-page__section">
          <h3>Export Information</h3>
          <dl className="meta-dl">
            <MetaRow label="Export Timestamp" value={runManifest.generated_at} />
            <MetaRow label="Run Type" value={runManifest.run_type} />
          </dl>
        </div>
      )}

      {/* Disclaimers */}
      {overview.disclaimers && overview.disclaimers.length > 0 && (
        <div className="section-card v2-run-metadata-page__section">
          <h3>Disclaimers</h3>
          <ul className="v2-run-metadata-page__disclaimer-list compact-list">
            {overview.disclaimers.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Methodology note */}
      {overview.methodology_note && (
        <div className="section-card v2-run-metadata-page__section">
          <h3>Methodology Note</h3>
          <p className="v2-run-metadata-page__methodology">{overview.methodology_note}</p>
        </div>
      )}

      {fullMetricSummary?.methodology_note &&
        fullMetricSummary.methodology_note !== overview.methodology_note && (
          <div className="section-card v2-run-metadata-page__section">
            <h3>Full Metric Summary — Methodology Note</h3>
            <p className="v2-run-metadata-page__methodology">
              {fullMetricSummary.methodology_note}
            </p>
          </div>
        )}
    </section>
  );
}
