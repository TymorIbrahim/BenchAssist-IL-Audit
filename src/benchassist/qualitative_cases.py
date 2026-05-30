"""Extract qualitative case studies from flagged V2 audit outputs (cautious summaries)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings
from benchassist.report import _df_to_markdown_table

_CAUTION = (
    "Screening signal only; requires human legal review. "
    "Not a finding of discrimination."
)


def _coerce_bool(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _build_interpretation(row: pd.Series) -> str:
    parts: list[str] = []
    if _coerce_bool(row.get("legal_framing_bias_flag")):
        parts.append("Structured legal-framing fields differ from neutral baseline.")
    if _coerce_bool(row.get("action_type_flip")):
        parts.append("Recommended action type changed.")
    if _coerce_bool(row.get("remedy_weaker")):
        parts.append("Remedy strength appears weaker for the variant.")
    if _coerce_bool(row.get("credibility_more_skeptical")):
        parts.append("Credibility framing appears more skeptical.")
    if _coerce_bool(row.get("evidence_burden_higher")):
        parts.append("Evidence burden appears higher.")
    if not parts:
        parts.append("Selected for manual review (limited detail in automated flags).")
    return " ".join(parts) + f" {_CAUTION}"


def extract_qualitative_cases(
    *,
    outputs_df: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    flagged_df: pd.DataFrame | None = None,
    top_n: int = 5,
) -> pd.DataFrame:
    """Build qualitative case rows from outputs + pairwise comparisons."""
    if pairwise_df.empty:
        return pd.DataFrame()

    candidates = pairwise_df.copy()
    if flagged_df is not None and not flagged_df.empty and "variant_id" in flagged_df.columns:
        flagged_ids = set(flagged_df["variant_id"].astype(str))
        flagged_rows = candidates[candidates["variant_id"].astype(str).isin(flagged_ids)]
        if not flagged_rows.empty:
            candidates = flagged_rows

    if "legal_framing_bias_flag" in candidates.columns:
        sort_cols = ["legal_framing_bias_flag"]
        ascending = [False]
        if "remedy_strength_delta" in candidates.columns:
            sort_cols.append("remedy_strength_delta")
            ascending.append(True)
        candidates = candidates.sort_values(sort_cols, ascending=ascending)
    candidates = candidates.head(max(1, top_n))

    outputs_idx = (
        outputs_df.set_index("variant_id", drop=False)
        if "variant_id" in outputs_df.columns
        else pd.DataFrame()
    )
    neutral_idx = (
        outputs_df[outputs_df.get("variant_type") == "neutral_he"].set_index("case_id")
        if "variant_type" in outputs_df.columns
        else pd.DataFrame()
    )

    rows: list[dict[str, Any]] = []
    for _, pair in candidates.iterrows():
        variant_id = str(pair.get("variant_id", ""))
        case_id = pair.get("case_id")
        variant_row = (
            outputs_idx.loc[variant_id]
            if variant_id in outputs_idx.index
            else pd.Series(dtype=object)
        )
        if isinstance(variant_row, pd.DataFrame):
            variant_row = variant_row.iloc[0]

        neutral_row = pd.Series(dtype=object)
        if not neutral_idx.empty and case_id in neutral_idx.index:
            neutral_row = neutral_idx.loc[case_id]
            if isinstance(neutral_row, pd.DataFrame):
                neutral_row = neutral_row.iloc[0]

        rows.append(
            {
                "case_id": case_id,
                "variant_id": variant_id,
                "variant_type": pair.get("variant_type"),
                "demographic_cue": pair.get("demographic_cue"),
                "language": variant_row.get("language", pair.get("language")),
                "model_name": variant_row.get("model_name"),
                "prompt_mode": variant_row.get("prompt_mode"),
                "schema_version": variant_row.get("schema_version"),
                "neutral_input_text": neutral_row.get("input_text", pair.get("neutral_reasoning_text")),
                "variant_input_text": variant_row.get("input_text", pair.get("input_text")),
                "neutral_urgency": pair.get("neutral_urgency_score", neutral_row.get("urgency")),
                "variant_urgency": pair.get("variant_urgency_score", variant_row.get("urgency")),
                "neutral_recommended_action_type": pair.get(
                    "neutral_recommended_action_type",
                    neutral_row.get("recommended_action_type"),
                ),
                "variant_recommended_action_type": pair.get(
                    "variant_recommended_action_type",
                    variant_row.get("recommended_action_type"),
                ),
                "neutral_remedy_strength_score": pair.get(
                    "neutral_remedy_strength_score", neutral_row.get("remedy_strength_score")
                ),
                "variant_remedy_strength_score": pair.get(
                    "variant_remedy_strength_score", variant_row.get("remedy_strength_score")
                ),
                "neutral_evidence_burden_level": neutral_row.get("evidence_burden_level"),
                "variant_evidence_burden_level": variant_row.get("evidence_burden_level"),
                "neutral_party_credibility_framing": neutral_row.get(
                    "party_credibility_framing"
                ),
                "variant_party_credibility_framing": variant_row.get(
                    "party_credibility_framing"
                ),
                "neutral_rights_orientation": neutral_row.get("rights_orientation"),
                "variant_rights_orientation": variant_row.get("rights_orientation"),
                "neutral_procedural_posture": neutral_row.get("procedural_posture"),
                "variant_procedural_posture": variant_row.get("procedural_posture"),
                "neutral_reasoning_text": pair.get(
                    "neutral_reasoning_text", neutral_row.get("reasoning_text")
                ),
                "variant_reasoning_text": pair.get(
                    "reasoning_text", variant_row.get("reasoning_text")
                ),
                "generated_interpretation": _build_interpretation(pair),
            }
        )

    return pd.DataFrame(rows)


def generate_qualitative_report(cases_df: pd.DataFrame, *, output_suffix: str) -> str:
    lines = [
        "# Qualitative Case Studies",
        "",
        "Examples selected for **human legal review**. Automated interpretations are cautious "
        "and may be incomplete.",
        "",
    ]
    if cases_df.empty:
        lines.append("_No cases selected (empty flagged set or missing pairwise data)._")
    else:
        for _, row in cases_df.iterrows():
            lines.append(f"## {row.get('case_id')} / {row.get('variant_type')}")
            lines.append("")
            lines.append(f"**Interpretation (automated):** {row.get('generated_interpretation')}")
            lines.append("")
            lines.append(f"- Variant input (excerpt): {str(row.get('variant_input_text', ''))[:400]}")
            lines.append("")
    lines.append(f"_Suffix: `{output_suffix}`_")
    lines.append("")
    if not cases_df.empty:
        cols = [
            c
            for c in ["case_id", "variant_type", "demographic_cue", "generated_interpretation"]
            if c in cases_df.columns
        ]
        lines.append("## Summary table")
        lines.append("")
        lines.append(_df_to_markdown_table(cases_df[cols]))
    return "\n".join(lines)


def run_qualitative_cases(
    *,
    outputs_path: Path,
    pairwise_path: Path,
    flagged_path: Path | None = None,
    top_n: int = 5,
    output_suffix: str = "cases",
    results_dir: Path | None = None,
) -> dict[str, Any]:
    root = results_dir or get_settings().RESULTS_DIR
    tables = root / "tables"
    report_dir = root / "report"
    tables.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    clean = output_suffix.strip().replace("/", "-")
    outputs_df = pd.read_csv(outputs_path)
    pairwise_df = pd.read_csv(pairwise_path)
    flagged_df = pd.read_csv(flagged_path) if flagged_path and flagged_path.exists() else None

    cases_df = extract_qualitative_cases(
        outputs_df=outputs_df,
        pairwise_df=pairwise_df,
        flagged_df=flagged_df,
        top_n=top_n,
    )

    paths = {
        "csv": tables / f"qualitative_case_studies_{clean}.csv",
        "report": report_dir / f"qualitative_case_studies_{clean}.md",
    }
    cases_df.to_csv(paths["csv"], index=False, encoding="utf-8-sig")
    paths["report"].write_text(
        generate_qualitative_report(cases_df, output_suffix=clean),
        encoding="utf-8",
    )
    return {"paths": paths, "cases": cases_df}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract qualitative audit case studies.")
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--pairwise", type=Path, required=True)
    parser.add_argument("--flagged", type=Path, default=None)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--output-suffix", default="cases")
    parser.add_argument("--results-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    result = run_qualitative_cases(
        outputs_path=args.outputs,
        pairwise_path=args.pairwise,
        flagged_path=args.flagged,
        top_n=args.top_n,
        output_suffix=args.output_suffix,
        results_dir=args.results_dir,
    )
    print(f"Cases extracted: {len(result['cases'])}")
    for name, path in result["paths"].items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
