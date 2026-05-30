"""Real Israeli case-inspired multi-domain reliability audit (not strict counterfactual fairness)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings
from benchassist.dataset_modes import DEFAULT_REAL_CASE_LIMITATIONS, REAL_CASE_ATTRIBUTION

CONFIDENCE_MAP = {"low": 0, "medium": 1, "high": 2}


def _rate(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    return float(series.mean())


def _distribution(series: pd.Series) -> str:
    if series.empty:
        return ""
    counts = series.fillna("unknown").astype(str).value_counts()
    return "; ".join(f"{k}:{v}" for k, v in counts.items())


def analyze_real_case_outputs(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute domain-level and per-output metrics."""
    work = df.copy()
    if "normalized_domain" not in work.columns:
        work["normalized_domain"] = work.get("legal_area", work.get("source_domain", "unknown"))

    per_rows: list[dict[str, Any]] = []
    for _, row in work.iterrows():
        per_rows.append({
            "case_id": row.get("case_id"),
            "variant_id": row.get("variant_id"),
            "normalized_domain": row.get("normalized_domain", "unknown"),
            "language": row.get("language"),
            "recommended_action_type": row.get("recommended_action_type"),
            "urgency": row.get("urgency"),
            "remedy_strength_score": row.get("remedy_strength_score"),
            "evidence_burden_level": row.get("evidence_burden_level"),
            "party_credibility_framing": row.get("party_credibility_framing"),
            "rights_orientation": row.get("rights_orientation"),
            "confidence": row.get("confidence"),
            "parse_error": row.get("parse_error"),
            "limitations": row.get("limitations"),
            "dataset_mode": row.get("dataset_mode", "real_case_inspired"),
        })
    per_df = pd.DataFrame(per_rows)

    group_rows: list[dict[str, Any]] = []
    for domain, grp in per_df.groupby("normalized_domain", dropna=False):
        conf = grp["confidence"].map(lambda x: CONFIDENCE_MAP.get(str(x).lower(), None) if pd.notna(x) else None)
        remedy = pd.to_numeric(grp["remedy_strength_score"], errors="coerce")
        group_rows.append({
            "normalized_domain": domain,
            "n_outputs": len(grp),
            "avg_confidence_score": conf.dropna().mean() if conf.notna().any() else None,
            "urgency_distribution": _distribution(grp["urgency"]),
            "recommended_action_distribution": _distribution(grp["recommended_action_type"]),
            "remedy_strength_avg": remedy.mean() if remedy.notna().any() else None,
            "evidence_burden_distribution": _distribution(grp["evidence_burden_level"]),
            "credibility_framing_distribution": _distribution(grp["party_credibility_framing"]),
            "rights_orientation_distribution": _distribution(grp["rights_orientation"]),
            "parse_error_rate": _rate(grp["parse_error"].notna() & (grp["parse_error"].astype(str).str.len() > 0)),
            "limitation_mentions_rate": _rate(grp["limitations"].fillna("").astype(str).str.len() > 3),
        })
    group_df = pd.DataFrame(group_rows)
    return group_df, per_df


def build_report(
    group_df: pd.DataFrame,
    per_df: pd.DataFrame,
    *,
    output_suffix: str,
    source_note: str = REAL_CASE_ATTRIBUTION,
) -> str:
    lines = [
        "# Real Israeli Case-Inspired Multi-Domain Audit",
        "",
        f"**Output suffix:** {output_suffix}",
        "",
        "> Research audit only. Not legal advice. Not an AI judge. "
        "Real-case-inspired outputs are realism signals — not proof of discrimination.",
        "",
        "## 1. Purpose",
        "Evaluate model behavior on source-derived Israeli legal scenarios across multiple domains.",
        "This layer complements — but does not replace — the synthetic controlled counterfactual audit.",
        "",
        "## 2. Data sources and limitations",
        source_note,
        DEFAULT_REAL_CASE_LIMITATIONS,
        "",
        "## 3. Domains covered",
    ]
    if group_df.empty:
        lines.append("No domain-level data available in this run.")
    else:
        for _, row in group_df.iterrows():
            lines.append(f"- **{row['normalized_domain']}**: {int(row['n_outputs'])} outputs")

    lines.extend([
        "",
        "## 4. Why this is not a strict counterfactual fairness test",
        "Real-case originals are not paired neutral baselines. Approximate variants are exploratory only.",
        "Main strict fairness rates should use `synthetic_controlled` data unless explicitly labeled exploratory.",
        "",
        "## 5. Domain-level output behavior",
    ])
    if not group_df.empty:
        lines.append("| Domain | N | Parse error rate |")
        lines.append("| --- | ---: | ---: |")
        for _, row in group_df.iterrows():
            lines.append(
                f"| {row['normalized_domain']} | {int(row['n_outputs'])} | "
                f"{row.get('parse_error_rate', 0):.2f} |"
            )
    else:
        lines.append("_Not available._")

    lines.extend([
        "",
        "## 6. Legal reliability signals",
        "Review parse errors, limitation mentions, and action/urgency distributions per domain.",
        "",
        "## 7. Stereotype/identity concerns",
        "Run stereotype audit separately if outputs are available.",
        "",
        "## 8. Hallucination/grounding concerns",
        "Run grounded mode + hallucination audit for source fidelity testing.",
        "",
        "## 9. Qualitative examples",
    ])
    sample = per_df.head(5)
    if sample.empty:
        lines.append("_No examples._")
    else:
        for _, r in sample.iterrows():
            lines.append(f"- {r.get('case_id')} / {r.get('variant_id')} ({r.get('normalized_domain')})")

    lines.extend([
        "",
        "## 10. Recommendations",
        "- Use for realism, domain coverage, and qualitative legal review.",
        "- Do not treat as strict demographic fairness proof.",
        "- Human legal expert review required.",
    ])
    return "\n".join(lines)


def run_real_case_audit(
    outputs_path: Path,
    *,
    output_suffix: str = "real_cases",
    tables_dir: Path | None = None,
    report_dir: Path | None = None,
) -> dict[str, Path]:
    settings = get_settings()
    tables = tables_dir or (settings.RESULTS_DIR / "tables")
    reports = report_dir or (settings.RESULTS_DIR / "report")
    tables.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(outputs_path)
    group_df, per_df = analyze_real_case_outputs(df)

    group_path = tables / f"real_case_audit_group_summary_{output_suffix}.csv"
    per_path = tables / f"real_case_audit_per_output_{output_suffix}.csv"
    report_path = reports / f"real_case_audit_{output_suffix}.md"

    group_df.to_csv(group_path, index=False, encoding="utf-8-sig")
    per_df.to_csv(per_path, index=False, encoding="utf-8-sig")
    report_path.write_text(
        build_report(group_df, per_df, output_suffix=output_suffix),
        encoding="utf-8",
    )
    return {"group_summary": group_path, "per_output": per_path, "report": report_path}


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Real-case-inspired multi-domain audit.")
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--output-suffix", default="real_cases")
    args = parser.parse_args(argv)

    paths = run_real_case_audit(args.outputs, output_suffix=args.output_suffix)
    for k, p in paths.items():
        print(f"  {k}: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
