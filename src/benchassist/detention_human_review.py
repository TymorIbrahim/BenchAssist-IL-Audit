"""Detention-specific human expert review templates and inter-rater summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

METADATA_COLUMNS: tuple[str, ...] = (
    "review_id",
    "case_id",
    "variant_id",
    "variant_type",
    "prompt_mode",
    "model_name",
)

COMPARISON_COLUMNS: tuple[str, ...] = (
    "neutral_recommended_action_type",
    "variant_recommended_action_type",
    "neutral_dangerousness_level",
    "variant_dangerousness_level",
    "neutral_obstruction_risk_level",
    "variant_obstruction_risk_level",
    "neutral_suspect_credibility_framing",
    "variant_suspect_credibility_framing",
    "neutral_reasoning_text",
    "variant_reasoning_text",
    "why_flagged",
    "validity_category",
    "fact_preservation_score",
)

REVIEWER_COLUMNS: tuple[str, ...] = (
    "reviewer_id",
    "reviewer_role",
    "review_date",
)

SCORE_COLUMNS: tuple[str, ...] = (
    "factual_equivalence_score",
    "legal_justification_score",
    "bias_concern_score",
    "stereotype_or_irrelevant_assumption_score",
    "judicial_impact_score",
    "procedural_safeguards_fairness_score",
)

CATEGORICAL_COLUMNS: tuple[str, ...] = (
    "is_factual_equivalence_valid",
    "is_difference_substantive",
    "is_difference_legally_justified",
    "possible_bias_type",
    "review_decision",
)

FREE_TEXT_COLUMNS: tuple[str, ...] = (
    "reviewer_notes",
    "recommended_final_classification",
    "suggested_report_quote",
    "follow_up_needed",
)

ALL_TEMPLATE_COLUMNS: tuple[str, ...] = (
    *METADATA_COLUMNS,
    *COMPARISON_COLUMNS,
    *REVIEWER_COLUMNS,
    *SCORE_COLUMNS,
    *CATEGORICAL_COLUMNS,
    *FREE_TEXT_COLUMNS,
)


def generate_detention_human_review_template(
    flagged_df: pd.DataFrame,
    *,
    validity_df: pd.DataFrame | None = None,
    max_rows: int = 100,
) -> pd.DataFrame:
    """Build CSV template from flagged detention comparisons."""
    if flagged_df.empty:
        return pd.DataFrame(columns=list(ALL_TEMPLATE_COLUMNS))

    df = flagged_df.head(max_rows).copy()
    if validity_df is not None and not validity_df.empty:
        df = df.merge(
            validity_df[["variant_id", "validity_category", "fact_preservation_score"]],
            on="variant_id",
            how="left",
        )

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        review_id = f"{row.get('case_id')}-{row.get('variant_id')}"
        rows.append(
            {
                "review_id": review_id,
                "case_id": row.get("case_id"),
                "variant_id": row.get("variant_id"),
                "variant_type": row.get("variant_type"),
                "prompt_mode": row.get("prompt_mode", "baseline"),
                "model_name": row.get("model_name", ""),
                "neutral_recommended_action_type": row.get("neutral_recommended_action_type"),
                "variant_recommended_action_type": row.get("variant_recommended_action_type"),
                "neutral_dangerousness_level": row.get("neutral_dangerousness_level"),
                "variant_dangerousness_level": row.get("variant_dangerousness_level"),
                "neutral_obstruction_risk_level": row.get("neutral_obstruction_risk_level"),
                "variant_obstruction_risk_level": row.get("variant_obstruction_risk_level"),
                "neutral_suspect_credibility_framing": row.get("neutral_suspect_credibility_framing"),
                "variant_suspect_credibility_framing": row.get("variant_suspect_credibility_framing"),
                "neutral_reasoning_text": row.get("neutral_reasoning_text", "")[:500],
                "variant_reasoning_text": row.get("variant_reasoning_text", "")[:500],
                "why_flagged": row.get("review_label") or row.get("detention_audit_flags"),
                "validity_category": row.get("validity_category"),
                "fact_preservation_score": row.get("fact_preservation_score"),
            }
        )
    out = pd.DataFrame(rows)
    for col in ALL_TEMPLATE_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out[list(ALL_TEMPLATE_COLUMNS)]


def summarize_detention_human_reviews(completed_df: pd.DataFrame) -> dict[str, Any]:
    """Aggregate completed expert reviews and inter-rater agreement."""
    if completed_df.empty:
        return {"n_reviews": 0}

    df = completed_df.copy()
    df = df[df["review_decision"].astype(str).str.strip() != ""]

    summary: dict[str, Any] = {
        "n_reviews": len(df),
        "n_unique_cases": df["review_id"].nunique() if "review_id" in df.columns else len(df),
        "decision_counts": df["review_decision"].value_counts().to_dict() if "review_decision" in df.columns else {},
    }

    if "reviewer_id" in df.columns and df["reviewer_id"].astype(str).str.strip().ne("").any():
        dupes = df.groupby("review_id")["reviewer_id"].nunique()
        multi = dupes[dupes >= 2]
        summary["n_cases_with_multiple_reviewers"] = int(len(multi))
        if len(multi) > 0 and "bias_concern_score" in df.columns:
            agreements = []
            for rid in multi.index:
                sub = df[df["review_id"] == rid]
                scores = pd.to_numeric(sub["bias_concern_score"], errors="coerce").dropna()
                if len(scores) >= 2:
                    agreements.append(abs(scores.iloc[0] - scores.iloc[1]) <= 1)
            summary["bias_score_agreement_within_1"] = (
                round(sum(agreements) / len(agreements), 4) if agreements else None
            )

    for col in SCORE_COLUMNS:
        if col in df.columns:
            nums = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(nums):
                summary[f"mean_{col}"] = round(float(nums.mean()), 3)

    summary["audit_closure"] = {
        "min_reviews_for_closure": 20,
        "n_completed": len(df),
        "closure_met": len(df) >= 20,
        "note": "Audit closure requires ≥20 expert-reviewed flagged comparisons.",
    }
    return summary


def export_detention_review_state_json(review_rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"reviews": review_rows}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate detention human review template")
    parser.add_argument("--flagged", type=Path, required=True)
    parser.add_argument("--validity", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    flagged = pd.read_csv(args.flagged)
    validity = pd.read_csv(args.validity) if args.validity and args.validity.exists() else None
    template = generate_detention_human_review_template(flagged, validity_df=validity)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    template.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Wrote {args.output} ({len(template)} rows)")


if __name__ == "__main__":
    main()
