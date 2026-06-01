"use client";

import { IconWarning } from "@/components/v2/Icons";

import { useState, useMemo, useCallback } from "react";
import type { DashboardBundle } from "@/lib/v2/dataUtils";
import {
  formatRate,
  formatCount,
  formatDelta,
  formatVariantLabel,
  computeFlaggedRate,
  getShiftDirection,
} from "@/lib/v2/dataUtils";
import type { FilterState, PairwiseComparison, GroupSummary } from "@/lib/v2/types";
import { DEFAULT_FILTERS } from "@/lib/v2/types";
import { StatCard } from "./StatCard";
import { ShiftBadge } from "./ShiftBadge";
import { FilterBar } from "./FilterBar";
import { BarChartPanel } from "./BarChartPanel";
import { EmptyState } from "./EmptyState";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function isAddressProxyType(variantType: string): boolean {
  const lower = variantType.toLowerCase();
  return lower.startsWith("address") || lower.includes("proxy");
}

function filterAddressProxy(rows: PairwiseComparison[], filters: FilterState): PairwiseComparison[] {
  return rows.filter((row) => {
    if (filters.promptMode && row.prompt_mode !== filters.promptMode) return false;
    if (filters.variantType && row.variant_type !== filters.variantType) return false;
    return true;
  });
}

function getAddressGroupSummaries(
  groupSummary: GroupSummary[],
  addressVariantTypes: string[],
): GroupSummary[] {
  const addrSet = new Set(addressVariantTypes.map((v) => v.toLowerCase()));
  return groupSummary.filter(
    (g) => addrSet.has(g.variant_type.toLowerCase()) || isAddressProxyType(g.variant_type),
  );
}

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface AddressProxyPageProps {
  bundle: DashboardBundle;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function AddressProxyPage({ bundle }: AddressProxyPageProps) {
  /* ---------- state ---------- */
  const [filters, setFilters] = useState<FilterState>({
    ...DEFAULT_FILTERS,
    promptMode: "",
    variantType: "",
  });

  const handleFilterChange = useCallback((next: FilterState) => {
    setFilters(next);
  }, []);

  /* ---------- derived ---------- */
  const allProxy = bundle.addressProxy;
  const filteredProxy = useMemo(() => filterAddressProxy(allProxy, filters), [allProxy, filters]);
  const flaggedProxy = useMemo(
    () => filteredProxy.filter((r) => r.detention_framing_bias_flag),
    [filteredProxy],
  );
  const flaggedRate = computeFlaggedRate(filteredProxy);

  const addrGroupSummaries = useMemo(
    () => getAddressGroupSummaries(bundle.groupSummary, bundle.addressVariantTypes),
    [bundle.groupSummary, bundle.addressVariantTypes],
  );

  const filteredGroupSummaries = useMemo(() => {
    let rows = addrGroupSummaries;
    if (filters.promptMode) rows = rows.filter((g) => g.prompt_mode === filters.promptMode);
    if (filters.variantType) rows = rows.filter((g) => g.variant_type === filters.variantType);
    return rows;
  }, [addrGroupSummaries, filters]);

  /* Chart data — BarChartPanel expects { name, value, fill? }[] */
  const chartData = useMemo(
    () =>
      filteredGroupSummaries.map((g) => ({
        name: formatVariantLabel(g.variant_type),
        value: +(g.flagged_rate * 100).toFixed(1),
        fill: g.flagged_rate > 0.1 ? "#d97706" : "#2563eb",
      })),
    [filteredGroupSummaries],
  );

  /* ---------- empty ---------- */
  if (!allProxy.length && !addrGroupSummaries.length) {
    return (
      <section className="v2-address-proxy-page tab-panel">
        <div className="detention-page-header">
          <div className="page-header-body">
            <h1>Address / SES Proxy Analysis</h1>
            <p className="page-note">
              Proxy-sensitivity signals for expert review — excluded from strict demographic fairness rates
            </p>
          </div>
        </div>
        <EmptyState
          title="No address proxy data"
          message="This run did not include address-proxy variant comparisons."
        />
      </section>
    );
  }

  return (
    <section className="v2-address-proxy-page tab-panel">
      {/* Header */}
      <div className="detention-page-header">
        <div className="page-header-body">
          <h1>Address / SES Proxy Analysis</h1>
          <p className="page-note">
            Proxy-sensitivity signals for expert review — excluded from strict demographic fairness
            rates
          </p>
        </div>
      </div>

      {/* Warning callout */}
      <div className="callout callout-caution v2-address-proxy-page__callout">
        <strong><IconWarning /> Important Context</strong>
        <p className="callout-body">
          Address variants test whether the model&apos;s dangerousness assessment changes when the
          suspect&apos;s address implies a different socioeconomic or geographic profile. These
          results are <strong>NOT</strong> included in the strict demographic fairness screening
          rate. They are presented separately as proxy-sensitivity signals for expert review.
        </p>
      </div>

      {/* Stat cards */}
      <div className="stat-grid">
        <StatCard
          label="Total Address Proxy Comparisons"
          value={formatCount(filteredProxy.length)}
          sub={filters.promptMode || filters.variantType ? "filtered" : "all modes"}
        />
        <StatCard
          label="Flagged Address Proxy"
          value={formatCount(flaggedProxy.length)}
          sub={`of ${formatCount(filteredProxy.length)} comparisons`}
        />
        <StatCard
          label="Address Proxy Flagged Rate"
          value={formatRate(flaggedRate)}
          sub="comparisons with audit signals"
        />
      </div>

      {/* Simplified filter bar — prompt mode and variant type only */}
      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        promptModes={bundle.promptModes}
        variantTypes={bundle.addressVariantTypes}
        baseCaseIds={[]}
        totalCount={allProxy.length}
        filteredCount={filteredProxy.length}
      />

      {/* Bar chart */}
      {chartData.length > 0 && (
        <BarChartPanel
          title="Address Proxy Flagged Rate by Variant Type"
          data={chartData}
          yLabel="%"
          formatValue={(v) => `${v}%`}
        />
      )}

      {/* Group summary table */}
      {filteredGroupSummaries.length > 0 && (
        <div className="section-card v2-address-proxy-page__table-section">
          <h3>Address Proxy Results by Locality / Profile</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Variant Type</th>
                  <th>Prompt Mode</th>
                  <th>N Comparisons</th>
                  <th>Flagged Rate</th>
                  <th>Danger Change Rate</th>
                  <th>Address Mention Rate</th>
                  <th>Identity Mention Rate</th>
                </tr>
              </thead>
              <tbody>
                {filteredGroupSummaries.map((g, i) => (
                  <tr key={`${g.variant_type}-${g.prompt_mode}-${i}`}>
                    <td>{formatVariantLabel(g.variant_type)}</td>
                    <td>{g.prompt_mode}</td>
                    <td>{formatCount(g.n_comparisons)}</td>
                    <td>{formatRate(g.flagged_rate)}</td>
                    <td>{formatRate(g.dangerousness_change_rate)}</td>
                    <td>{formatRate(g.address_mention_rate)}</td>
                    <td>{formatRate(g.identity_or_proxy_mention_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Flagged cases list */}
      {flaggedProxy.length > 0 && (
        <div className="section-card v2-address-proxy-page__flagged-section">
          <h3>Flagged Address-Proxy Comparisons ({flaggedProxy.length})</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Variant Type</th>
                  <th>Prompt Mode</th>
                  <th>Δ Danger Level</th>
                  <th>Audit Flags</th>
                </tr>
              </thead>
              <tbody>
                {flaggedProxy.map((row, i) => (
                  <tr key={`${row.case_id}-${row.variant_id}-${i}`}>
                    <td>{row.case_id}</td>
                    <td>{formatVariantLabel(row.variant_type)}</td>
                    <td>{row.prompt_mode}</td>
                    <td>
                      <ShiftBadge
                        direction={getShiftDirection(row)}
                        delta={row.dangerousness_level_delta}
                      />
                    </td>
                    <td>
                      {row.detention_audit_flags.length > 0 ? (
                        <div className="chip-row">
                          {row.detention_audit_flags.map((flag, fi) => (
                            <span key={fi} className="badge badge-caution">
                              {flag}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {flaggedProxy.length === 0 && filteredProxy.length > 0 && (
        <div className="section-card">
          <p className="muted">No flagged address-proxy comparisons in the current filter selection.</p>
        </div>
      )}
    </section>
  );
}
