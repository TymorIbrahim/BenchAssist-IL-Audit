"""Narrative-framing and credibility-priming robustness audit (V2 pairwise metrics)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings
from benchassist.narrative_framing_texts import NARRATIVE_VARIANT_TYPES
from benchassist.report import _df_to_markdown_table

NARRATIVE_VARIANT_SET: frozenset[str] = frozenset(NARRATIVE_VARIANT_TYPES)

CROSS_PAIR_COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("low_vs_high_credibility", "low_credibility_priming", "high_credibility_priming"),
    ("tenant_vs_landlord_framing", "tenant_friendly_framing", "landlord_friendly_framing"),
    ("emotional_vs_neutral_clerk", "tenant_emotional_layperson", "neutral_clerk_summary"),
    ("rights_vs_procedure", "rights_oriented_summary", "procedure_oriented_summary"),
)

_GROUP_AGG: dict[str, tuple[str, str]] = {
    "n_pairs": ("case_id", "count"),
    "action_type_flip_rate": ("action_type_flip", "mean"),
    "legal_framing_bias_flag_rate": ("legal_framing_bias_flag", "mean"),
    "urgency_weaker_rate": ("urgency_weaker", "mean"),
    "remedy_weaker_rate": ("remedy_weaker", "mean"),
    "evidence_burden_higher_rate": ("evidence_burden_higher", "mean"),
    "credibility_more_skeptical_rate": ("credibility_more_skeptical", "mean"),
    "rights_orientation_weaker_rate": ("rights_orientation_weaker", "mean"),
    "procedural_posture_weaker_rate": ("procedural_posture_weaker", "mean"),
    "avg_remedy_strength_delta": ("remedy_strength_delta", "mean"),
    "avg_evidence_burden_delta": ("evidence_burden_delta", "mean"),
    "avg_credibility_skepticism_delta": ("credibility_skepticism_delta", "mean"),
    "avg_rights_orientation_delta": ("rights_orientation_delta", "mean"),
    "avg_procedural_posture_delta": ("procedural_posture_delta", "mean"),
}


def _coerce_bool(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def filter_narrative_pairwise(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    """Keep rows whose variant_type is a narrative-framing variant."""
    if pairwise_df.empty or "variant_type" not in pairwise_df.columns:
        return pd.DataFrame()
    return pairwise_df[
        pairwise_df["variant_type"].astype(str).isin(NARRATIVE_VARIANT_SET)
    ].copy()


def merge_narrative_metadata(
    narrative_df: pd.DataFrame,
    *,
    counterfactual_path: Path | None = None,
    validity_path: Path | None = None,
) -> pd.DataFrame:
    """Attach framing and validity columns when source files exist."""
    if narrative_df.empty:
        return narrative_df

    out = narrative_df.copy()
    meta_cols = (
        "framing_axis",
        "framing_direction",
        "strict_counterfactual_candidate",
        "transformation_style",
    )

    if counterfactual_path and counterfactual_path.exists():
        cf = pd.read_csv(counterfactual_path)
        key = "variant_id" if "variant_id" in cf.columns else None
        if key and key in out.columns:
            merge_cols = [c for c in [*meta_cols, "variant_type"] if c in cf.columns]
            if merge_cols:
                out = out.merge(
                    cf[[key, *merge_cols]].drop_duplicates(key),
                    on=key,
                    how="left",
                    suffixes=("", "_cf"),
                )

    if validity_path and validity_path.exists():
        val = pd.read_csv(validity_path)
        if "variant_id" in val.columns and "variant_id" in out.columns:
            val_cols = [c for c in ("validity_category", "fact_preservation_score") if c in val.columns]
            if val_cols:
                out = out.merge(
                    val[["variant_id", *val_cols]].drop_duplicates("variant_id"),
                    on="variant_id",
                    how="left",
                    suffixes=("", "_val"),
                )
    return out


def compute_narrative_group_summary(narrative_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate V2 pairwise metrics for narrative variants."""
    if narrative_df.empty:
        return pd.DataFrame()

    group_cols = ["variant_type"]
    for col in ("framing_axis", "framing_direction", "validity_category"):
        if col in narrative_df.columns and narrative_df[col].notna().any():
            group_cols.append(col)

    agg_dict: dict[str, tuple[str, str]] = {
        out_col: (src_col, how)
        for out_col, (src_col, how) in _GROUP_AGG.items()
        if src_col in narrative_df.columns
    }
    if not agg_dict:
        return pd.DataFrame()

    grouped = narrative_df.groupby(group_cols, dropna=False)
    parts: list[pd.DataFrame] = []
    for out_col, (src_col, how) in agg_dict.items():
        if how == "count":
            part = grouped[src_col].count().reset_index(name=out_col)
        else:
            part = grouped[src_col].agg(how).reset_index(name=out_col)
        parts.append(part)

    merged = parts[0]
    for part in parts[1:]:
        merged = merged.merge(part, on=group_cols, how="left")
    return merged.round(4)


def compute_cross_pair_comparisons(narrative_df: pd.DataFrame) -> pd.DataFrame:
    """Compare paired narrative variants on the same case (delta of deltas vs baseline)."""
    if narrative_df.empty or "case_id" not in narrative_df.columns:
        return pd.DataFrame()

    numeric_cols = [
        c
        for c in (
            "urgency_delta",
            "remedy_strength_delta",
            "evidence_burden_delta",
            "credibility_skepticism_delta",
            "rights_orientation_delta",
            "procedural_posture_delta",
        )
        if c in narrative_df.columns
    ]
    flag_cols = [
        c
        for c in (
            "legal_framing_bias_flag",
            "action_type_flip",
            "remedy_weaker",
            "credibility_more_skeptical",
        )
        if c in narrative_df.columns
    ]

    rows: list[dict[str, Any]] = []
    indexed = narrative_df.set_index(["case_id", "variant_type"], drop=False)

    for comparison_name, left_type, right_type in CROSS_PAIR_COMPARISONS:
        pair_rows: list[dict[str, Any]] = []
        for case_id in narrative_df["case_id"].unique():
            try:
                left = indexed.loc[(case_id, left_type)]
                right = indexed.loc[(case_id, right_type)]
            except KeyError:
                continue
            if isinstance(left, pd.DataFrame):
                left = left.iloc[0]
            if isinstance(right, pd.DataFrame):
                right = right.iloc[0]

            row: dict[str, Any] = {
                "comparison": comparison_name,
                "case_id": case_id,
                "left_variant_type": left_type,
                "right_variant_type": right_type,
            }
            for col in numeric_cols:
                lv = left.get(col)
                rv = right.get(col)
                if pd.notna(lv) and pd.notna(rv):
                    row[f"{col}_right_minus_left"] = float(rv) - float(lv)
            for col in flag_cols:
                row[f"{col}_left"] = _coerce_bool(left.get(col))
                row[f"{col}_right"] = _coerce_bool(right.get(col))
                row[f"{col}_differs"] = row[f"{col}_left"] != row[f"{col}_right"]
            pair_rows.append(row)

        if not pair_rows:
            continue

        summary: dict[str, Any] = {
            "comparison": comparison_name,
            "left_variant_type": left_type,
            "right_variant_type": right_type,
            "n_cases": len(pair_rows),
        }
        diff_cols = [c for c in pair_rows[0] if c.endswith("_right_minus_left")]
        for col in diff_cols:
            values = [r[col] for r in pair_rows if col in r and pd.notna(r[col])]
            summary[f"mean_{col}"] = round(sum(values) / len(values), 4) if values else None
        for col in flag_cols:
            differs_key = f"{col}_differs"
            if differs_key in pair_rows[0]:
                rate = sum(1 for r in pair_rows if r.get(differs_key)) / len(pair_rows)
                summary[f"{col}_differs_rate"] = round(rate, 4)
        rows.append(summary)

    return pd.DataFrame(rows)


def summarize_narrative_robustness(
    group_summary: pd.DataFrame,
    cross_pairs: pd.DataFrame,
) -> dict[str, Any]:
    """Build a compact summary dict for reports."""
    if group_summary.empty:
        return {"available": False}

    sort_col = "legal_framing_bias_flag_rate"
    top = group_summary
    if sort_col in top.columns:
        top = top.sort_values(sort_col, ascending=False)

    strongest = []
    if not top.empty and sort_col in top.columns:
        for _, row in top.head(5).iterrows():
            strongest.append(
                {
                    "variant_type": row.get("variant_type"),
                    "legal_framing_bias_flag_rate": row.get(sort_col),
                    "remedy_weaker_rate": row.get("remedy_weaker_rate"),
                    "credibility_more_skeptical_rate": row.get(
                        "credibility_more_skeptical_rate"
                    ),
                }
            )

    credibility_rows = cross_pairs[
        cross_pairs["comparison"] == "low_vs_high_credibility"
    ] if not cross_pairs.empty else pd.DataFrame()

    return {
        "available": True,
        "n_variant_groups": len(group_summary),
        "strongest_effects": strongest,
        "cross_pairs": cross_pairs.to_dict(orient="records") if not cross_pairs.empty else [],
        "credibility_comparison": (
            credibility_rows.iloc[0].to_dict() if len(credibility_rows) else {}
        ),
        "max_bias_flag_rate": float(group_summary[sort_col].max())
        if sort_col in group_summary.columns
        else None,
    }


def generate_narrative_robustness_report(
    *,
    group_summary: pd.DataFrame,
    cross_pairs: pd.DataFrame,
    summary: dict[str, Any],
    output_suffix: str,
) -> str:
    """Render the narrative-framing robustness Markdown report."""
    lines = [
        "# Narrative-Framing Robustness Audit",
        "",
        "## 1. Purpose",
        "",
        "This audit tests whether **the same legal facts** receive different structured "
        "legal-framing treatment when the case summary is phrased in different narrative styles. "
        "It complements demographic and language-access counterfactual audits.",
        "",
        "## 2. Why narrative framing matters in judge-facing LLMs",
        "",
        "Bench memos influence perceived urgency, remedy strength, evidence burden, and credibility. "
        "Irrelevant differences in tone, emotionality, or party-sympathetic wording should not "
        "systematically shift those fields when underlying facts are unchanged.",
        "",
        "## 3. Variant types",
        "",
        "Ten deterministic narrative variants per base case:",
        "",
    ]
    for vt in NARRATIVE_VARIANT_TYPES:
        lines.append(f"- `{vt}`")
    lines.extend(
        [
            "",
            "## 4. Strict vs stress-test variants",
            "",
            "- **narrative_strict_counterfactual**: style change with high heuristic fact preservation.",
            "- **credibility_priming_stress_test**: intentional skepticism/support priming; "
            "not a strict factual counterfactual.",
            "- Party-sympathy and emotional variants may require **human legal review** even when "
            "facts appear preserved.",
            "",
            "## 5. Aggregate results",
            "",
        ]
    )

    if group_summary.empty:
        lines.append("_No narrative variant rows found in the pairwise input._\n")
    else:
        display_cols = [
            c
            for c in [
                "variant_type",
                "framing_axis",
                "framing_direction",
                "validity_category",
                "n_pairs",
                "legal_framing_bias_flag_rate",
                "remedy_weaker_rate",
                "evidence_burden_higher_rate",
                "credibility_more_skeptical_rate",
            ]
            if c in group_summary.columns
        ]
        lines.append(_df_to_markdown_table(group_summary[display_cols].head(15)))
        lines.append("")

    lines.extend(["## 6. Strongest framing effects", ""])
    for item in summary.get("strongest_effects", [])[:5]:
        lines.append(
            f"- `{item.get('variant_type')}`: legal_framing_bias_flag_rate="
            f"{item.get('legal_framing_bias_flag_rate')}"
        )
    lines.append("")

    lines.extend(["## 7. Credibility priming results", ""])
    cred = summary.get("credibility_comparison") or {}
    if cred:
        for key, val in cred.items():
            if key.startswith("mean_") or key.endswith("_rate"):
                lines.append(f"- **{key}**: {val}")
    else:
        lines.append("_No low vs high credibility cross-pair data in this run._")
    lines.append("")

    lines.extend(["## 8. Party-sympathy framing results", ""])
    if not cross_pairs.empty:
        party = cross_pairs[
            cross_pairs["comparison"] == "tenant_vs_landlord_framing"
        ]
        if not party.empty:
            lines.append(_df_to_markdown_table(party))
        else:
            lines.append("_Tenant vs landlord framing comparison not available._")
    lines.append("")

    lines.extend(["## 9. Emotionality and layperson framing", ""])
    if not cross_pairs.empty:
        emo = cross_pairs[cross_pairs["comparison"] == "emotional_vs_neutral_clerk"]
        if not emo.empty:
            lines.append(_df_to_markdown_table(emo))
        else:
            lines.append("_Emotional vs neutral clerk comparison not available._")
    lines.append("")

    lines.extend(
        [
            "## 10. Limitations",
            "",
            "- Narrative framing effects are **not** the same as demographic discrimination.",
            "- Stress-test variants reveal **sensitivity** to framing, not necessarily unfairness.",
            "- Pairwise rows may be compared to `neutral_he` demographic baseline depending on the "
            "batch design; interpret cross-variant tables for narrative-only contrasts.",
            "- Heuristic fact-preservation does not replace human legal review.",
            "",
            "## 11. Recommendations",
            "",
            "- Review flagged cases with a legally trained reviewer.",
            "- Separate strict narrative counterfactual rates from credibility-priming stress tests.",
            "- Consider prompt instructions that anchor on documented facts and procedural posture.",
            "- Do not treat screening metrics as findings of judicial bias.",
            "",
            f"_Report suffix: `{output_suffix}`_",
            "",
        ]
    )
    return "\n".join(lines)


def run_narrative_robustness(
    *,
    pairwise_path: Path,
    validity_path: Path | None = None,
    counterfactual_path: Path | None = None,
    output_suffix: str = "narrative",
    results_dir: Path | None = None,
) -> dict[str, Any]:
    """Run narrative robustness analysis and write CSV/Markdown outputs."""
    root = results_dir or get_settings().RESULTS_DIR
    tables = root / "tables"
    report_dir = root / "report"
    tables.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    clean = output_suffix.strip().replace("/", "-")
    pairwise_df = pd.read_csv(pairwise_path)
    narrative_df = filter_narrative_pairwise(pairwise_df)
    narrative_df = merge_narrative_metadata(
        narrative_df,
        counterfactual_path=counterfactual_path,
        validity_path=validity_path,
    )

    group_summary = compute_narrative_group_summary(narrative_df)
    cross_pairs = compute_cross_pair_comparisons(narrative_df)
    summary = summarize_narrative_robustness(group_summary, cross_pairs)

    paths = {
        "summary": tables / f"narrative_robustness_summary_{clean}.csv",
        "pairwise": tables / f"narrative_robustness_pairwise_{clean}.csv",
        "cross_pairs": tables / f"narrative_robustness_cross_pairs_{clean}.csv",
        "report": report_dir / f"narrative_robustness_{clean}.md",
    }

    if group_summary.empty:
        pd.DataFrame(
            columns=[
                "variant_type",
                "n_pairs",
                "legal_framing_bias_flag_rate",
            ]
        ).to_csv(paths["summary"], index=False, encoding="utf-8-sig")
    else:
        group_summary.to_csv(paths["summary"], index=False, encoding="utf-8-sig")
    if narrative_df.empty:
        pd.DataFrame(columns=list(pairwise_df.columns)).head(0).to_csv(
            paths["pairwise"], index=False, encoding="utf-8-sig"
        )
    else:
        narrative_df.to_csv(paths["pairwise"], index=False, encoding="utf-8-sig")
    if cross_pairs.empty:
        pd.DataFrame(columns=["comparison", "n_cases"]).to_csv(
            paths["cross_pairs"], index=False, encoding="utf-8-sig"
        )
    else:
        cross_pairs.to_csv(paths["cross_pairs"], index=False, encoding="utf-8-sig")

    report_text = generate_narrative_robustness_report(
        group_summary=group_summary,
        cross_pairs=cross_pairs,
        summary=summary,
        output_suffix=clean,
    )
    paths["report"].write_text(report_text, encoding="utf-8")

    return {
        "paths": paths,
        "narrative_rows": len(narrative_df),
        "group_summary": group_summary,
        "cross_pairs": cross_pairs,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Narrative-framing robustness audit from V2 pairwise comparisons."
    )
    parser.add_argument(
        "--pairwise",
        type=Path,
        required=True,
        help="V2 pairwise comparison CSV (e.g. v2_pairwise_comparison_<suffix>.csv).",
    )
    parser.add_argument(
        "--validity",
        type=Path,
        default=None,
        help="Optional counterfactual_validity_*.csv for validity_category merge.",
    )
    parser.add_argument(
        "--counterfactuals",
        type=Path,
        default=None,
        help="Optional counterfactual_cases.csv for framing metadata.",
    )
    parser.add_argument(
        "--output-suffix",
        default="narrative",
        help="Suffix for output files (default: narrative).",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Results root (default: RESULTS_DIR from settings).",
    )
    args = parser.parse_args(argv)

    cf = args.counterfactuals
    if cf is None:
        default_cf = get_settings().DATA_DIR / "audit" / "counterfactual_cases.csv"
        if default_cf.exists():
            cf = default_cf

    result = run_narrative_robustness(
        pairwise_path=args.pairwise,
        validity_path=args.validity,
        counterfactual_path=cf,
        output_suffix=args.output_suffix,
        results_dir=args.results_dir,
    )
    print(f"Narrative pairwise rows: {result['narrative_rows']}")
    for name, path in result["paths"].items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
