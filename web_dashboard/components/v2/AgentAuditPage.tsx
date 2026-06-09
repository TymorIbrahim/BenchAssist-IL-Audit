"use client";

import React, { useEffect, useMemo, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AgentCase {
  case_id: string;
  variant_id: string;
  variant_type: string;
  recommendation: string;
  public_safety_risk: string;
  confidence: number;
  considers_alternative: boolean;
  considers_defense_claim: boolean;
  mentions_sensitive_var: boolean;
  tone_score: number;
}

interface ComparisonMetrics {
  simple_total: number;
  simple_parsed: number;
  simple_detention_rate: number;
  agent_detention_rate: number;
  simple_alternatives_rate: number;
  agent_alternatives_rate: number;
  simple_defense_rate: number;
  agent_defense_rate: number;
  simple_confidence_mean: number;
  agent_confidence_mean: number;
}

interface AuditQualityEntry {
  count: number;
  total: number;
  rate: number;
}

interface RiskByVariant {
  n: number;
  high: number;
  medium: number;
  low: number;
  high_rate: number;
}

interface AgentAuditData {
  pipeline: string;
  model: string;
  total_cases: number;
  parsed_ok: number;
  parse_errors: number;
  parse_success_rate: number;
  recommendations: Record<string, number>;
  recommendation_rates: Record<string, number>;
  confidence_mean: number;
  confidence_std: number;
  confidence_min: number;
  confidence_max: number;
  risk_by_variant: Record<string, RiskByVariant>;
  audit_quality: Record<string, AuditQualityEntry>;
  comparison: ComparisonMetrics;
  cases: AgentCase[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function formatVariant(v: string): string {
  return v.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const REC_COLORS: Record<string, string> = {
  release_with_conditions: "var(--v2-success)",
  alternative_detention: "var(--v2-warning)",
  detention_extension: "var(--v2-danger)",
};

const REC_LABELS: Record<string, string> = {
  release_with_conditions: "Release with Conditions",
  alternative_detention: "Alternative Detention",
  detention_extension: "Detention Extension",
};

const RISK_COLORS: Record<string, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
};

/* ------------------------------------------------------------------ */
/*  Stat Card                                                          */
/* ------------------------------------------------------------------ */

function AgentStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="v2-stat-card">
      <div className="v2-stat-card__label">{label}</div>
      <div className="v2-stat-card__value" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
      {sub && <div className="v2-stat-card__sub">{sub}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Comparison Bar                                                     */
/* ------------------------------------------------------------------ */

function ComparisonBar({
  label,
  simpleVal,
  agentVal,
  format = "pct",
  higherIsBetter = true,
}: {
  label: string;
  simpleVal: number;
  agentVal: number;
  format?: "pct" | "num";
  higherIsBetter?: boolean;
}) {
  const fmt = format === "pct" ? pct : (v: number) => v.toFixed(3);
  const agentBetter = higherIsBetter ? agentVal > simpleVal : agentVal < simpleVal;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "0.75rem 0", borderBottom: "1px solid var(--v2-border)" }}>
      <div style={{ width: "200px", fontWeight: 500, fontSize: "0.85rem" }}>{label}</div>
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8rem", color: "var(--v2-text-muted)", width: "70px", textAlign: "right" }}>Simple</span>
        <div style={{
          flex: 1, height: "24px", background: "var(--v2-surface-alt)", borderRadius: "12px",
          overflow: "hidden", position: "relative",
        }}>
          <div style={{
            width: `${Math.min(simpleVal * 100, 100)}%`,
            height: "100%", background: "var(--v2-text-muted)", opacity: 0.4, borderRadius: "12px",
          }} />
          <span style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", fontSize: "0.75rem", fontWeight: 600 }}>
            {fmt(simpleVal)}
          </span>
        </div>
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8rem", color: "var(--v2-text-muted)", width: "70px", textAlign: "right" }}>Agent</span>
        <div style={{
          flex: 1, height: "24px", background: "var(--v2-surface-alt)", borderRadius: "12px",
          overflow: "hidden", position: "relative",
        }}>
          <div style={{
            width: `${Math.min(agentVal * 100, 100)}%`,
            height: "100%",
            background: agentBetter ? "var(--v2-success)" : "var(--v2-warning)",
            opacity: 0.6, borderRadius: "12px",
          }} />
          <span style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", fontSize: "0.75rem", fontWeight: 600 }}>
            {fmt(agentVal)}
          </span>
        </div>
      </div>
      <div style={{ width: "28px", textAlign: "center", fontSize: "1.1rem" }}>
        {agentBetter ? "✅" : "⚠️"}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function AgentAuditPage() {
  const [data, setData] = useState<AgentAuditData | null>(null);
  const [filterVariant, setFilterVariant] = useState<string>("");
  const [sortBy, setSortBy] = useState<"confidence" | "recommendation" | "risk">("confidence");

  useEffect(() => {
    fetch("/data/agent_audit_summary.json")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, []);

  const filteredCases = useMemo(() => {
    if (!data) return [];
    let cases = data.cases;
    if (filterVariant) cases = cases.filter((c) => c.variant_type === filterVariant);
    return cases.sort((a, b) => {
      if (sortBy === "confidence") return b.confidence - a.confidence;
      if (sortBy === "risk") return (RISK_COLORS[b.public_safety_risk] ? 1 : 0) - (RISK_COLORS[a.public_safety_risk] ? 1 : 0);
      return a.recommendation.localeCompare(b.recommendation);
    });
  }, [data, filterVariant, sortBy]);

  if (!data) {
    return (
      <div className="v2-loading">
        <div className="v2-loading__spinner" />
        <p className="v2-loading__text">Loading Agent Audit data…</p>
      </div>
    );
  }

  const comp = data.comparison;
  const variantTypes = Object.keys(data.risk_by_variant);

  return (
    <div className="v2-fade-in">
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
          🤖 Agentic RAG Audit
        </h1>
        <p style={{ color: "var(--v2-text-muted)", marginTop: "0.5rem", fontSize: "0.9rem", lineHeight: 1.6 }}>
          Results from the legally-grounded agent pipeline — 4-node LangGraph architecture with Israeli law retrieval,
          unified judicial reasoner prompt, and Section 21/21א compliance enforcement.
        </p>
      </div>

      {/* Pipeline Info Banner */}
      <div style={{
        background: "linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(139,92,246,0.1) 100%)",
        border: "1px solid rgba(99,102,241,0.2)",
        borderRadius: "12px", padding: "1.25rem", marginBottom: "1.5rem",
        display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap",
      }}>
        <div style={{ flex: 1, minWidth: "200px" }}>
          <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--v2-text-muted)" }}>Pipeline</div>
          <div style={{ fontWeight: 600, marginTop: "0.25rem" }}>{data.pipeline}</div>
        </div>
        <div>
          <span className="v2-badge v2-badge--info">{data.model}</span>
          <span className="v2-badge v2-badge--neutral" style={{ marginLeft: "0.5rem" }}>Fast Mode</span>
          <span className="v2-badge v2-badge--neutral" style={{ marginLeft: "0.5rem" }}>10 Legal Docs</span>
          <span className="v2-badge v2-badge--neutral" style={{ marginLeft: "0.5rem" }}>270 Law Chunks</span>
        </div>
      </div>

      {/* Headline Stats */}
      <div className="v2-stat-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        <AgentStat label="Total Cases" value={String(data.total_cases)} sub={`${data.parsed_ok} parsed OK`} />
        <AgentStat label="Parse Rate" value={pct(data.parse_success_rate)} accent="var(--v2-success)" sub={`${data.parse_errors} errors`} />
        <AgentStat label="Confidence" value={data.confidence_mean.toFixed(2)} accent="var(--v2-info)" sub={`σ=${data.confidence_std.toFixed(3)}, ${data.confidence_min}–${data.confidence_max}`} />
        <AgentStat label="Detention Rate" value={pct(data.recommendation_rates.detention_extension || 0)} accent="var(--v2-danger)" sub={`${data.recommendations.detention_extension || 0} cases`} />
        <AgentStat label="Alternatives" value={pct(data.audit_quality.considers_alternative?.rate || 0)} accent="var(--v2-success)" sub="Legal obligation §21א" />
        <AgentStat label="Defense Claims" value={pct(data.audit_quality.considers_defense_claim?.rate || 0)} accent="var(--v2-info)" sub={`${data.audit_quality.considers_defense_claim?.count || 0}/${data.parsed_ok}`} />
      </div>

      {/* Recommendation Distribution */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>📊 Recommendation Distribution</h2>
        <div style={{ display: "flex", gap: "0.5rem", borderRadius: "12px", overflow: "hidden", height: "40px" }}>
          {Object.entries(data.recommendation_rates).map(([key, rate]) => (
            <div
              key={key}
              style={{
                flex: rate,
                background: REC_COLORS[key] || "var(--v2-text-muted)",
                opacity: 0.7,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "0.75rem", fontWeight: 600, color: "#fff",
                minWidth: rate > 0.05 ? "80px" : "0px",
              }}
            >
              {rate > 0.05 && `${REC_LABELS[key] || key} ${pct(rate)}`}
            </div>
          ))}
        </div>
      </section>

      {/* Comparison Section */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>⚖️ Simple Pipeline vs Agentic RAG</h2>
        <div style={{ background: "var(--v2-surface)", border: "1px solid var(--v2-border)", borderRadius: "12px", padding: "1.25rem" }}>
          <ComparisonBar label="Considers Alternatives" simpleVal={comp.simple_alternatives_rate} agentVal={comp.agent_alternatives_rate} />
          <ComparisonBar label="Defense Claims" simpleVal={comp.simple_defense_rate} agentVal={comp.agent_defense_rate} />
          <ComparisonBar label="Detention Rate" simpleVal={comp.simple_detention_rate} agentVal={comp.agent_detention_rate} higherIsBetter={false} />
          <ComparisonBar label="Confidence" simpleVal={comp.simple_confidence_mean} agentVal={comp.agent_confidence_mean} />
        </div>
      </section>

      {/* Risk by Variant Type */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>🎯 Risk Assessment by Variant Type</h2>
        <div style={{ background: "var(--v2-surface)", border: "1px solid var(--v2-border)", borderRadius: "12px", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--v2-border)" }}>
                <th style={{ padding: "0.75rem 1rem", textAlign: "left", fontWeight: 600 }}>Variant Type</th>
                <th style={{ padding: "0.75rem 1rem", textAlign: "center", fontWeight: 600 }}>N</th>
                <th style={{ padding: "0.75rem 1rem", textAlign: "center", fontWeight: 600 }}>High Risk</th>
                <th style={{ padding: "0.75rem 1rem", textAlign: "center", fontWeight: 600 }}>Medium Risk</th>
                <th style={{ padding: "0.75rem 1rem", textAlign: "center", fontWeight: 600 }}>Low Risk</th>
                <th style={{ padding: "0.75rem 1rem", textAlign: "left", fontWeight: 600 }}>Distribution</th>
              </tr>
            </thead>
            <tbody>
              {variantTypes.map((vt) => {
                const v = data.risk_by_variant[vt];
                const total = v.high + v.medium + v.low;
                return (
                  <tr key={vt} style={{ borderBottom: "1px solid var(--v2-border)" }}>
                    <td style={{ padding: "0.75rem 1rem", fontWeight: 500 }}>{formatVariant(vt)}</td>
                    <td style={{ padding: "0.75rem 1rem", textAlign: "center" }}>{v.n}</td>
                    <td style={{ padding: "0.75rem 1rem", textAlign: "center", color: RISK_COLORS.high, fontWeight: 600 }}>{v.high}</td>
                    <td style={{ padding: "0.75rem 1rem", textAlign: "center", color: RISK_COLORS.medium, fontWeight: 600 }}>{v.medium}</td>
                    <td style={{ padding: "0.75rem 1rem", textAlign: "center", color: RISK_COLORS.low, fontWeight: 600 }}>{v.low}</td>
                    <td style={{ padding: "0.75rem 1rem" }}>
                      <div style={{ display: "flex", borderRadius: "6px", overflow: "hidden", height: "16px" }}>
                        {total > 0 && (
                          <>
                            <div style={{ width: `${(v.low / total) * 100}%`, background: RISK_COLORS.low, opacity: 0.7 }} />
                            <div style={{ width: `${(v.medium / total) * 100}%`, background: RISK_COLORS.medium, opacity: 0.7 }} />
                            <div style={{ width: `${(v.high / total) * 100}%`, background: RISK_COLORS.high, opacity: 0.7 }} />
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Audit Quality */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>✅ Audit Quality Metrics</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
          {Object.entries(data.audit_quality).map(([key, val]) => {
            const isPositive = key === "considers_defense_claim" || key === "considers_alternative";
            const isNegative = key === "hallucination_detected" || key === "over_adopts_police_framing" || key === "mentions_sensitive_var";
            const good = isPositive ? val.rate > 0.7 : isNegative ? val.rate < 0.1 : true;
            return (
              <div
                key={key}
                style={{
                  background: "var(--v2-surface)", border: "1px solid var(--v2-border)",
                  borderRadius: "12px", padding: "1rem",
                  borderLeft: `4px solid ${good ? "var(--v2-success)" : "var(--v2-warning)"}`,
                }}
              >
                <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--v2-text-muted)" }}>
                  {key.replace(/_/g, " ")}
                </div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: "0.25rem" }}>
                  {pct(val.rate)} {good ? "✅" : "⚠️"}
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--v2-text-muted)" }}>
                  {val.count}/{val.total} cases
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Case Table */}
      <section>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: 0 }}>📋 Individual Case Results ({filteredCases.length})</h2>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <select
              value={filterVariant}
              onChange={(e) => setFilterVariant(e.target.value)}
              style={{
                padding: "0.4rem 0.75rem", borderRadius: "8px",
                border: "1px solid var(--v2-border)", background: "var(--v2-surface)",
                fontSize: "0.8rem", color: "var(--v2-text)",
              }}
            >
              <option value="">All Variants</option>
              {variantTypes.map((vt) => (
                <option key={vt} value={vt}>{formatVariant(vt)}</option>
              ))}
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              style={{
                padding: "0.4rem 0.75rem", borderRadius: "8px",
                border: "1px solid var(--v2-border)", background: "var(--v2-surface)",
                fontSize: "0.8rem", color: "var(--v2-text)",
              }}
            >
              <option value="confidence">Sort by Confidence</option>
              <option value="recommendation">Sort by Recommendation</option>
              <option value="risk">Sort by Risk</option>
            </select>
          </div>
        </div>
        <div style={{
          background: "var(--v2-surface)", border: "1px solid var(--v2-border)",
          borderRadius: "12px", overflow: "auto", maxHeight: "500px",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
            <thead style={{ position: "sticky", top: 0, background: "var(--v2-surface)", zIndex: 1 }}>
              <tr style={{ borderBottom: "2px solid var(--v2-border)" }}>
                <th style={{ padding: "0.6rem 0.75rem", textAlign: "left" }}>Case</th>
                <th style={{ padding: "0.6rem 0.75rem", textAlign: "left" }}>Variant</th>
                <th style={{ padding: "0.6rem 0.75rem", textAlign: "left" }}>Recommendation</th>
                <th style={{ padding: "0.6rem 0.75rem", textAlign: "center" }}>Risk</th>
                <th style={{ padding: "0.6rem 0.75rem", textAlign: "center" }}>Confidence</th>
                <th style={{ padding: "0.6rem 0.75rem", textAlign: "center" }}>Alt?</th>
                <th style={{ padding: "0.6rem 0.75rem", textAlign: "center" }}>Defense?</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.slice(0, 100).map((c, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--v2-border)" }}>
                  <td style={{ padding: "0.5rem 0.75rem", fontWeight: 500 }}>{c.case_id}</td>
                  <td style={{ padding: "0.5rem 0.75rem" }}>
                    <span style={{
                      fontSize: "0.72rem", padding: "0.15rem 0.5rem", borderRadius: "10px",
                      background: "var(--v2-surface-alt)",
                    }}>{formatVariant(c.variant_type)}</span>
                  </td>
                  <td style={{ padding: "0.5rem 0.75rem" }}>
                    <span style={{
                      fontSize: "0.72rem", padding: "0.15rem 0.5rem", borderRadius: "10px",
                      background: REC_COLORS[c.recommendation] || "var(--v2-text-muted)",
                      color: "#fff", fontWeight: 600,
                    }}>{REC_LABELS[c.recommendation] || c.recommendation}</span>
                  </td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center" }}>
                    <span style={{ color: RISK_COLORS[c.public_safety_risk] || "inherit", fontWeight: 600 }}>
                      {c.public_safety_risk}
                    </span>
                  </td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center", fontWeight: 600 }}>{c.confidence.toFixed(2)}</td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center" }}>{c.considers_alternative ? "✅" : "❌"}</td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center" }}>{c.considers_defense_claim ? "✅" : "❌"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredCases.length > 100 && (
          <p style={{ fontSize: "0.8rem", color: "var(--v2-text-muted)", marginTop: "0.5rem" }}>
            Showing first 100 of {filteredCases.length} cases
          </p>
        )}
      </section>
    </div>
  );
}
