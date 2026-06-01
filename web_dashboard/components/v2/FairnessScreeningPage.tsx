"use client";

import "../../app/fairness.css";

import type React from "react";
import { useState, useMemo } from "react";
import { IconUser, IconMapPin, IconLink, IconWarning, IconScale, IconChart } from "@/components/v2/Icons";
import type { GroupSummary } from "@/lib/v2/types";
import type { DashboardBundle } from "@/lib/v2/dataUtils";
import {
  formatRate,
  formatCount,
  formatVariantLabel,
  computeFlaggedRate,
} from "@/lib/v2/dataUtils";
import { StatCard } from "./StatCard";

/* ------------------------------------------------------------------ */
/*  Completeness tier filter                                           */
/* ------------------------------------------------------------------ */

type CompletenessTier = "all" | "complete" | "partial" | "minimal";

const COMPLETENESS_TIERS: { key: CompletenessTier; label: string; desc: string }[] = [
  { key: "all", label: "All Cases", desc: "Full dataset" },
  { key: "complete", label: "Complete", desc: "All fields clear" },
  { key: "partial", label: "Partial", desc: "1-2 fields vague" },
  { key: "minimal", label: "Minimal", desc: "3+ fields unknown" },
];

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const COMBINED_VARIANT_TYPES = [
  "arab_name_nazareth", "jewish_name_tel_aviv", "jewish_name_dimona",
  "ethiopian_netanya", "russian_ashdod", "mizrahi_beer_sheva",
  "arab_name_haifa", "arab_name_tel_aviv", "jewish_name_nazareth",
  "ethiopian_tel_aviv",
] as const;

const COMBINED_SET = new Set<string>(COMBINED_VARIANT_TYPES);

const EXCLUDED_FROM_DEMOGRAPHIC = new Set<string>([
  "skeptical_police_framing", "defense_framing",
]);

type TierKey = "demographic" | "address" | "combined";

const TIER_TABS: { key: TierKey; icon: React.ReactNode; title: string; desc: string; what: string }[] = [
  {
    key: "demographic",
    icon: <IconUser />,
    title: "Demographic Identity",
    desc: "Pure identity changes — name, ethnicity, gender",
    what: "Changes only the suspect's name, ethnic descriptor, or gender. Strictest test of demographic bias.",
  },
  {
    key: "address",
    icon: <IconMapPin />,
    title: "Address / SES Proxy",
    desc: "Geographic and socioeconomic proxy sensitivity",
    what: "Changes only the suspect's residential address. Tests whether location implying a different socioeconomic or ethnic profile shifts the model's assessment.",
  },
  {
    key: "combined",
    icon: <IconLink />,
    title: "Combined Intersectional",
    desc: "Demographic + address ecological validity",
    what: "Pairs a demographic identity with a realistic address (e.g., Arab name + Nazareth). Cross-controls test whether bias is additive or interactive.",
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function pct(rate: number): string { return `${(rate * 100).toFixed(1)}%`; }

function rateColor(rate: number): string {
  if (rate > 0.15) return "var(--fair-red, #dc2626)";
  if (rate > 0.10) return "var(--fair-orange, #d97706)";
  if (rate > 0.05) return "var(--fair-yellow, #ca8a04)";
  return "var(--fair-green, #16a34a)";
}

function rateSeverity(rate: number): string {
  if (rate > 0.15) return "High";
  if (rate > 0.10) return "Moderate";
  if (rate > 0.05) return "Low";
  return "Minimal";
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Horizontal bar row                                  */
/* ------------------------------------------------------------------ */

function VariantRow({ group, maxRate }: { group: GroupSummary; maxRate: number }) {
  const flagged = Math.round(group.flagged_rate * group.n_comparisons);
  const barPct = maxRate > 0 ? Math.min((group.flagged_rate / maxRate) * 100, 100) : 0;

  return (
    <div className="fair-row">
      <div className="fair-row__label" title={formatVariantLabel(group.variant_type)}>
        {formatVariantLabel(group.variant_type)}
      </div>
      <div className="fair-row__bar-wrap">
        <div
          className="fair-row__bar"
          style={{ width: `${barPct}%`, background: rateColor(group.flagged_rate) }}
        />
      </div>
      <div className="fair-row__pct" style={{ color: rateColor(group.flagged_rate) }}>
        {pct(group.flagged_rate)}
      </div>
      <div className="fair-row__count">{flagged}/{group.n_comparisons}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Metric Detail Table                                 */
/* ------------------------------------------------------------------ */

function MetricTable({ groups, showAddress }: { groups: GroupSummary[]; showAddress?: boolean }) {
  if (!groups.length) return null;
  return (
    <div className="fair-table-wrap">
      <table className="fair-table">
        <thead>
          <tr>
            <th>Variant</th>
            <th>N</th>
            <th>Flagged Rate</th>
            <th>Escalation</th>
            <th>De-escalation</th>
            <th>Identity Leakage</th>
            {showAddress && <th>Address Mention</th>}
            <th>Mean Δ</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => {
            const deescRate = g.dangerousness_change_rate - g.dangerousness_escalation_rate;
            return (
              <tr key={`${g.variant_type}-${g.prompt_mode}`}>
                <td className="fair-table__variant">{formatVariantLabel(g.variant_type)}</td>
                <td className="fair-table__num">{g.n_comparisons}</td>
                <td className="fair-table__rate" style={{ color: rateColor(g.flagged_rate) }}>
                  <strong>{pct(g.flagged_rate)}</strong>
                </td>
                <td className="fair-table__rate">
                  {g.dangerousness_escalation_rate > 0
                    ? <span style={{ color: "var(--fair-red, #dc2626)" }}>{pct(g.dangerousness_escalation_rate)} ↑</span>
                    : <span className="fair-table__zero">0%</span>}
                </td>
                <td className="fair-table__rate">
                  {deescRate > 0.005
                    ? <span style={{ color: "var(--fair-green, #16a34a)" }}>{pct(deescRate)} ↓</span>
                    : <span className="fair-table__zero">0%</span>}
                </td>
                <td className="fair-table__rate">
                  {g.identity_leakage_rate > 0.5
                    ? <span style={{ color: "var(--fair-orange, #d97706)" }}>{pct(g.identity_leakage_rate)}</span>
                    : pct(g.identity_leakage_rate)}
                </td>
                {showAddress && (
                  <td className="fair-table__rate">{pct(g.address_mention_rate)}</td>
                )}
                <td className="fair-table__delta">
                  {g.mean_dangerousness_delta > 0 ? "+" : ""}{g.mean_dangerousness_delta.toFixed(3)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Cross-Mode Comparison Grid                          */
/* ------------------------------------------------------------------ */

function CrossModeComparison({ groups, allGroups, promptModes }: {
  groups: GroupSummary[];
  allGroups: GroupSummary[];
  promptModes: string[];
}) {
  // Build matrix: variant x prompt mode → flagged rate
  const variants = [...new Set(groups.map(g => g.variant_type))];

  return (
    <div className="fair-cross-mode">
      <h3 className="fair-cross-mode__title">
        <IconChart /> Cross-Mode Comparison
      </h3>
      <p className="fair-cross-mode__desc">
        How each variant&apos;s flagged rate changes across prompt strategies
      </p>
      <div className="fair-table-wrap">
        <table className="fair-table fair-table--compact">
          <thead>
            <tr>
              <th>Variant</th>
              {promptModes.map(m => (
                <th key={m}>{formatVariantLabel(m)}</th>
              ))}
              <th>Max Δ</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(vt => {
              const rates = promptModes.map(m => {
                const row = allGroups.find(g => g.variant_type === vt && g.prompt_mode === m);
                return row ? row.flagged_rate : 0;
              });
              const maxDelta = Math.max(...rates) - Math.min(...rates);
              return (
                <tr key={vt}>
                  <td className="fair-table__variant">{formatVariantLabel(vt)}</td>
                  {rates.map((r, i) => (
                    <td key={promptModes[i]} className="fair-table__rate" style={{ color: rateColor(r) }}>
                      {pct(r)}
                    </td>
                  ))}
                  <td className="fair-table__delta" style={{
                    color: maxDelta > 0.05 ? "var(--fair-orange, #d97706)" : "inherit",
                    fontWeight: maxDelta > 0.05 ? 700 : 400,
                  }}>
                    {maxDelta > 0 ? `±${pct(maxDelta)}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

interface FairnessScreeningPageProps {
  bundle: DashboardBundle;
}

export function FairnessScreeningPage({ bundle }: FairnessScreeningPageProps) {
  const [selectedTier, setSelectedTier] = useState<TierKey>("demographic");
  const [selectedPromptMode, setSelectedPromptMode] = useState<string>("baseline");
  const [showDetails, setShowDetails] = useState(false);
  const [selectedCompleteness, setSelectedCompleteness] = useState<CompletenessTier>("all");

  const promptModes = bundle.promptModes.length ? bundle.promptModes : ["baseline"];

  /* ================================================================ */
  /*  Compute tier-specific data                                      */
  /* ================================================================ */

  const tierData = useMemo(() => {
    const byMode = bundle.groupSummary.filter(g => g.prompt_mode === selectedPromptMode);

    const demo = byMode
      .filter(g => !g.variant_type.startsWith("address_") && !COMBINED_SET.has(g.variant_type) && !EXCLUDED_FROM_DEMOGRAPHIC.has(g.variant_type))
      .sort((a, b) => b.flagged_rate - a.flagged_rate);

    // Address: compute from raw addressProxy pairwise data (not in groupSummary)
    const addrByVariant = new Map<string, { flagged: number; total: number; identityLeak: number; addrMention: number; escalations: number; deltaSum: number; changeCount: number }>();
    for (const row of bundle.addressProxy) {
      const vt = row.variant_type;
      if (!addrByVariant.has(vt)) {
        addrByVariant.set(vt, { flagged: 0, total: 0, identityLeak: 0, addrMention: 0, escalations: 0, deltaSum: 0, changeCount: 0 });
      }
      const agg = addrByVariant.get(vt)!;
      agg.total++;
      if (row.detention_framing_bias_flag) agg.flagged++;
      if (row.dangerousness_level_delta != null && row.dangerousness_level_delta > 0) agg.escalations++;
      if (row.dangerousness_level_delta != null && row.dangerousness_level_delta !== 0) agg.changeCount++;
      if (row.dangerousness_level_delta != null) agg.deltaSum += row.dangerousness_level_delta;
    }
    const addr: GroupSummary[] = [...addrByVariant.entries()].map(([vt, agg]) => ({
      variant_type: vt,
      prompt_mode: "all",
      n_comparisons: agg.total,
      flagged_rate: agg.total > 0 ? agg.flagged / agg.total : 0,
      dangerousness_escalation_rate: agg.total > 0 ? agg.escalations / agg.total : 0,
      dangerousness_change_rate: agg.total > 0 ? agg.changeCount / agg.total : 0,
      identity_leakage_rate: 0,
      identity_or_proxy_mention_rate: 0,
      address_mention_rate: 0,
      mean_dangerousness_delta: agg.total > 0 ? agg.deltaSum / agg.total : 0,
      insufficient_information_shift_rate: 0,
      unsupported_inference_rate: 0,
      protected_attribute_tested: vt.replace("address_", ""),
    })).sort((a, b) => b.flagged_rate - a.flagged_rate);

    const combined = bundle.combinedGroupSummary
      .filter(g => g.prompt_mode === selectedPromptMode)
      .sort((a, b) => b.flagged_rate - a.flagged_rate);

    return { demo, addr, combined };
  }, [bundle.groupSummary, bundle.addressProxy, bundle.combinedGroupSummary, selectedPromptMode]);

  const currentGroups = selectedTier === "demographic" ? tierData.demo
    : selectedTier === "address" ? tierData.addr
    : tierData.combined;

  const totalComparisons = currentGroups.reduce((s, g) => s + g.n_comparisons, 0);
  const totalFlagged = currentGroups.reduce((s, g) => s + Math.round(g.flagged_rate * g.n_comparisons), 0);
  const meanFlaggedRate = currentGroups.length > 0
    ? currentGroups.reduce((s, g) => s + g.flagged_rate, 0) / currentGroups.length : 0;
  const meanEscalation = currentGroups.length > 0
    ? currentGroups.reduce((s, g) => s + g.dangerousness_escalation_rate, 0) / currentGroups.length : 0;
  const meanIdentityLeak = currentGroups.length > 0
    ? currentGroups.reduce((s, g) => s + g.identity_leakage_rate, 0) / currentGroups.length : 0;
  const maxRate = Math.max(...currentGroups.map(g => g.flagged_rate), 0.01);

  /* Cross-mode data for all variants in current tier */
  const allTierGroups = useMemo(() => {
    if (selectedTier === "demographic") {
      return bundle.groupSummary.filter(g =>
        !g.variant_type.startsWith("address_") && !COMBINED_SET.has(g.variant_type) && !EXCLUDED_FROM_DEMOGRAPHIC.has(g.variant_type)
      );
    }
    // Address proxy data is aggregated across modes — no cross-mode breakdown available
    if (selectedTier === "address") {
      return tierData.addr;
    }
    return bundle.groupSummary.filter(g => COMBINED_SET.has(g.variant_type));
  }, [bundle.groupSummary, selectedTier, tierData]);

  /* ================================================================ */
  /*  Key insight for each tier                                       */
  /* ================================================================ */

  const highestVariant = currentGroups.length > 0 ? currentGroups[0] : null;
  const lowestVariant = currentGroups.length > 0 ? currentGroups[currentGroups.length - 1] : null;

  /* ================================================================ */
  /*  Render                                                           */
  /* ================================================================ */

  const currentTierMeta = TIER_TABS.find(t => t.key === selectedTier)!;

  return (
    <section className="fair-page">
      {/* ── Header ── */}
      <header className="fair-header">
        <h1 className="fair-header__title">Fairness Screening</h1>
        <p className="fair-header__subtitle">
          Three-tier counterfactual analysis measuring how identity, geography, and combined factors affect
          LLM dangerousness assessments
        </p>
      </header>

      {/* ── Tier Navigation ── */}
      <nav className="fair-tier-nav">
        {TIER_TABS.map(tab => (
          <button
            key={tab.key}
            className={`fair-tier-btn ${selectedTier === tab.key ? "fair-tier-btn--active" : ""}`}
            onClick={() => setSelectedTier(tab.key)}
          >
            <span className="fair-tier-btn__icon">{tab.icon}</span>
            <div className="fair-tier-btn__text">
              <span className="fair-tier-btn__title">{tab.title}</span>
              <span className="fair-tier-btn__desc">{tab.desc}</span>
            </div>
          </button>
        ))}
      </nav>

      {/* ── Tier Explainer ── */}
      <div className="fair-explainer">
        <div className="fair-explainer__icon">{currentTierMeta.icon}</div>
        <div>
          <strong>{currentTierMeta.title}</strong>
          <p>{currentTierMeta.what}</p>
          {selectedTier !== "demographic" && (
            <p className="fair-explainer__note">
              <IconWarning /> These results are <strong>not</strong> included in the strict demographic fairness rate.
              They are presented separately as proxy-sensitivity signals.
            </p>
          )}
        </div>
      </div>

      {/* ── Prompt Mode Selector ── */}
      <div className="fair-mode-bar">
        <span className="fair-mode-bar__label">Prompt Strategy:</span>
        <div className="fair-mode-bar__btns">
          {promptModes.map(mode => (
            <button
              key={mode}
              className={`fair-mode-btn ${selectedPromptMode === mode ? "fair-mode-btn--active" : ""}`}
              onClick={() => setSelectedPromptMode(mode)}
            >
              {formatVariantLabel(mode)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Completeness Tier Filter ── */}
      <div className="fair-mode-bar">
        <span className="fair-mode-bar__label">Evidence Completeness:</span>
        <div className="fair-mode-bar__btns">
          {COMPLETENESS_TIERS.map(tier => (
            <button
              key={tier.key}
              className={`fair-mode-btn ${selectedCompleteness === tier.key ? "fair-mode-btn--active" : ""}`}
              onClick={() => setSelectedCompleteness(tier.key)}
              title={tier.desc}
            >
              {tier.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Key Stats ── */}
      <div className="v2-stat-grid">
        <StatCard
          label="Comparisons"
          value={formatCount(totalComparisons)}
          tooltip="Total pairwise comparisons in this tier + prompt mode"
        />
        <StatCard
          label="Flagged"
          value={formatCount(totalFlagged)}
          variant={totalFlagged > 0 ? "warning" : "success"}
          tooltip="Cases where the model changed its dangerousness level"
        />
        <StatCard
          label="Mean Flagged Rate"
          value={pct(meanFlaggedRate)}
          variant={meanFlaggedRate > 0.10 ? "danger" : meanFlaggedRate > 0.05 ? "warning" : "success"}
          tooltip="Average flagged rate across all variant groups"
        />
        <StatCard
          label="Mean Escalation"
          value={pct(meanEscalation)}
          variant={meanEscalation > 0.05 ? "danger" : "default"}
          tooltip="Rate at which the model increased dangerousness for demographic variants"
        />
        <StatCard
          label="Identity Leakage"
          value={pct(meanIdentityLeak)}
          variant={meanIdentityLeak > 0.7 ? "warning" : "default"}
          tooltip="Rate at which the model mentioned the suspect's identity in its reasoning"
        />
      </div>

      {/* ── Key Insight ── */}
      {highestVariant && highestVariant.flagged_rate > 0 && (
        <div className="fair-insight">
          <div className="fair-insight__icon"><IconScale /></div>
          <div>
            <strong>Key Finding</strong>
            <p>
              Highest flagged rate: <strong>{formatVariantLabel(highestVariant.variant_type)}</strong> at{" "}
              <strong style={{ color: rateColor(highestVariant.flagged_rate) }}>{pct(highestVariant.flagged_rate)}</strong>{" "}
              ({Math.round(highestVariant.flagged_rate * highestVariant.n_comparisons)}/{highestVariant.n_comparisons} comparisons).
              {lowestVariant && lowestVariant.variant_type !== highestVariant.variant_type && (
                <> Lowest: <strong>{formatVariantLabel(lowestVariant.variant_type)}</strong> at {pct(lowestVariant.flagged_rate)}.</>
              )}
              {" "}Severity: <strong>{rateSeverity(meanFlaggedRate)}</strong>.
            </p>
          </div>
        </div>
      )}

      {/* ── Bar Chart ── */}
      {currentGroups.length > 0 ? (
        <section className="fair-section">
          <h2 className="fair-section__title">Flagged Rate by Variant</h2>
          <p className="fair-section__subtitle">
            {selectedTier === "demographic"
              ? `Strict demographic comparisons — ${formatVariantLabel(selectedPromptMode)} prompt mode`
              : selectedTier === "address"
              ? "Address proxy comparisons — aggregated across all prompt modes"
              : `Combined intersectional comparisons — ${formatVariantLabel(selectedPromptMode)} prompt mode`}
          </p>
          <div className="fair-chart">
            {currentGroups.map(g => (
              <VariantRow key={g.variant_type} group={g} maxRate={maxRate} />
            ))}
          </div>
        </section>
      ) : (
        <div className="fair-empty">
          <div className="fair-empty__icon">
            {selectedTier === "address" ? <IconMapPin /> : selectedTier === "combined" ? <IconLink /> : <IconUser />}
          </div>
          <strong className="fair-empty__title">
            No {selectedTier === "address" ? "Address / SES Proxy" : selectedTier === "combined" ? "Combined Intersectional" : "Demographic"} Data
          </strong>
          <p className="fair-empty__desc">
            {selectedTier === "address"
              ? "Address proxy variants were not included in this audit run. Re-run the pipeline with --include-address-variants to generate address sensitivity data."
              : selectedTier === "combined"
              ? "Combined (demographic + address) variants were not included in this run's variant set. The current dataset uses demographic-only variants. Re-run with an expanded variant set to generate combined intersectional data."
              : `No demographic variant data available for the ${formatVariantLabel(selectedPromptMode)} prompt mode.`}
          </p>
          <p className="fair-empty__hint">
            Run: <code>python -m benchassist.detention_data_generation --variant-set slim --include-address-variants --max-base-cases 80</code>
          </p>
        </div>
      )}

      {/* ── Detail Table Toggle ── */}
      {currentGroups.length > 0 && (
        <section className="fair-section">
          <button
            className="fair-toggle"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? "▾ Hide" : "▸ Show"} Detailed Metrics Table
          </button>
          {showDetails && (
            <MetricTable groups={currentGroups} showAddress={selectedTier === "address"} />
          )}
        </section>
      )}

      {/* ── Cross-Mode Comparison ── */}
      {promptModes.length > 1 && allTierGroups.length > 0 && (
        <section className="fair-section">
          <CrossModeComparison
            groups={currentGroups}
            allGroups={allTierGroups}
            promptModes={promptModes}
          />
        </section>
      )}
    </section>
  );
}
