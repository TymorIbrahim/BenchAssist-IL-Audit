"""Markdown audit report and chart generation for BenchAssist-IL."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

_REPORT_TITLE = "BenchAssist-IL Fairness Audit Report"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _truncate(text: Any, max_len: int = 220) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    value = str(text).strip().replace("\n", " ")
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _df_to_markdown_table(df: pd.DataFrame, *, float_fmt: str = ".3f") -> str:
    """Render a dataframe as a GitHub-flavoured markdown table."""
    display = df.copy()
    for col in display.select_dtypes(include="float").columns:
        display[col] = display[col].map(lambda v: format(v, float_fmt))

    headers = [str(col) for col in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in display.iterrows():
        cells = [str(row[col]).replace("|", "\\|") for col in display.columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _output_summary(row: pd.Series) -> str:
    return (
        f"**Urgency:** {row.get('urgency', 'N/A')} · "
        f"**Direction:** {row.get('recommended_direction', 'N/A')} · "
        f"**Remedy strength:** {row.get('remedy_strength_score', 'N/A')}\n\n"
        f"**Action:** {_truncate(row.get('recommended_action'))}\n\n"
        f"**Reasoning:** {_truncate(row.get('reasoning'))}"
    )


def _explain_difference(
    neutral: pd.Series,
    variant: pd.Series,
    *,
    flags: str = "",
) -> str:
    """Narrate observed differences between neutral and a demographic variant."""
    points: list[str] = []

    if str(neutral.get("urgency", "")).lower() != str(variant.get("urgency", "")).lower():
        points.append(
            f"Urgency shifted from **{neutral.get('urgency')}** (neutral) "
            f"to **{variant.get('urgency')}** (variant)."
        )
    if (
        str(neutral.get("recommended_direction", "")).lower()
        != str(variant.get("recommended_direction", "")).lower()
    ):
        points.append(
            f"Recommended direction changed from **{neutral.get('recommended_direction')}** "
            f"to **{variant.get('recommended_direction')}**."
        )
    n_remedy = neutral.get("remedy_strength_score")
    v_remedy = variant.get("remedy_strength_score")
    if pd.notna(n_remedy) and pd.notna(v_remedy) and int(n_remedy) != int(v_remedy):
        points.append(
            f"Remedy-strength proxy moved from **{int(n_remedy)}** to **{int(v_remedy)}**."
        )
    n_skep = neutral.get("skepticism_score", 0)
    v_skep = variant.get("skepticism_score", 0)
    if pd.notna(n_skep) and pd.notna(v_skep) and int(v_skep) - int(n_skep) >= 2:
        points.append(
            f"Skepticism language increased (neutral={int(n_skep)}, variant={int(v_skep)})."
        )
    if flags:
        points.append(f"Automated flags: `{flags}`.")

    if not points:
        return (
            "Recorded proxy metrics are largely aligned between neutral and this variant; "
            "any difference may be subtle or limited to wording length."
        )
    return " ".join(points)


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------


def generate_audit_charts(
    group_summary: pd.DataFrame,
    charts_dir: Path,
) -> dict[str, Path]:
    """Generate matplotlib bar charts grouped by variant type."""
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart_specs = [
        ("avg_urgency_score", "urgency_by_variant_type.png", "Average Urgency Score by Variant Type"),
        (
            "avg_remedy_strength_score",
            "remedy_strength_by_variant_type.png",
            "Average Remedy Strength by Variant Type",
        ),
        ("flip_rate", "flip_rate_by_variant_type.png", "Recommendation Flip Rate by Variant Type"),
        (
            "avg_skepticism_score",
            "skepticism_by_variant_type.png",
            "Average Skepticism Score by Variant Type",
        ),
    ]

    plot_df = group_summary.sort_values("variant_type")
    x_labels = plot_df["variant_type"].tolist()
    x_positions = range(len(x_labels))

    saved: dict[str, Path] = {}
    for column, filename, title in chart_specs:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(x_positions, plot_df[column].tolist())
        ax.set_title(title)
        ax.set_xlabel("Variant type")
        ax.set_ylabel(column.replace("_", " ").title())
        ax.set_xticks(list(x_positions))
        ax.set_xticklabels(x_labels, rotation=35, ha="right")
        fig.tight_layout()
        path = charts_dir / filename
        fig.savefig(path, dpi=150)
        plt.close(fig)
        saved[column] = path
        logger.info("Chart saved to %s", path)

    return saved


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def _select_qualitative_examples(
    flagged: pd.DataFrame,
    comparison: pd.DataFrame,
    *,
    n: int = 3,
) -> list[str]:
    """Return up to *n* case_ids to highlight in the qualitative section."""
    if not flagged.empty and "case_id" in flagged.columns:
        ids = flagged["case_id"].drop_duplicates().tolist()
        if "variant_type" in flagged.columns:
            # Prefer distinct cases with non-neutral variants
            pairs = flagged[flagged["variant_type"] != "neutral_he"][["case_id", "variant_type"]]
            if not pairs.empty:
                return pairs["case_id"].drop_duplicates().head(n).tolist()
        return ids[:n]

    if comparison.empty:
        return []

    candidates = comparison[comparison["variant_type"] != "neutral_he"].copy()
    if candidates.empty:
        return []

    candidates["severity"] = (
        candidates["urgency_score_delta"].abs().fillna(0)
        + candidates["remedy_strength_delta"].abs().fillna(0)
        + candidates["skepticism_score"].fillna(0)
        - candidates["neutral_skepticism_score"].fillna(0)
    )
    candidates = candidates.sort_values(
        ["recommendation_flip", "severity"], ascending=[False, False]
    )
    return candidates["case_id"].drop_duplicates().head(n).tolist()


def _build_qualitative_section(
    example_case_ids: list[str],
    model_outputs: pd.DataFrame,
) -> str:
    if not example_case_ids:
        return "_No flagged cases were available for qualitative review._\n"

    sections: list[str] = []
    for index, case_id in enumerate(example_case_ids, start=1):
        case_rows = model_outputs[model_outputs["case_id"] == case_id]
        if case_rows.empty:
            continue

        neutral_rows = case_rows[case_rows["variant_type"] == "neutral_he"]
        variant_rows = case_rows[case_rows["variant_type"] != "neutral_he"]
        if neutral_rows.empty or variant_rows.empty:
            continue

        neutral = neutral_rows.iloc[0]
        variant = variant_rows.iloc[0]
        flags = ""
        if "flags" in variant_rows.columns:
            flag_val = variant_rows.iloc[0].get("flags")
            if pd.notna(flag_val):
                flags = str(flag_val)

        sections.append(
            f"### Example {index}: {case_id} ({variant.get('variant_type')})\n\n"
            f"**Demographic cue:** {variant.get('demographic_cue')}\n\n"
            f"#### Neutral input (excerpt)\n\n"
            f"{_truncate(neutral.get('input_text'), 400)}\n\n"
            f"#### Neutral output summary\n\n"
            f"{_output_summary(neutral)}\n\n"
            f"#### Variant input (excerpt)\n\n"
            f"{_truncate(variant.get('input_text'), 400)}\n\n"
            f"#### Variant output summary\n\n"
            f"{_output_summary(variant)}\n\n"
            f"#### Observed difference\n\n"
            f"{_explain_difference(neutral, variant, flags=flags)}\n"
        )

    return "\n".join(sections) if sections else "_No qualitative examples could be assembled._\n"


def _dataset_summary(model_outputs: pd.DataFrame) -> dict[str, Any]:
    base_case_count = model_outputs["case_id"].nunique()
    variant_count = len(model_outputs)
    variant_types = sorted(model_outputs["variant_type"].dropna().unique().tolist())
    return {
        "base_case_count": int(base_case_count),
        "variant_count": int(variant_count),
        "variant_types": variant_types,
    }


def _model_run_summary(model_outputs: pd.DataFrame) -> dict[str, Any]:
    from benchassist.config import get_settings

    settings = get_settings()
    timestamps = pd.to_datetime(model_outputs["timestamp"], errors="coerce")
    return {
        "provider": settings.MODEL_PROVIDER,
        "model_name": model_outputs["model_name"].dropna().iloc[0]
        if "model_name" in model_outputs.columns and not model_outputs["model_name"].dropna().empty
        else settings.MODEL_NAME,
        "run_count": len(model_outputs),
        "parse_error_count": int(model_outputs["parse_error"].notna().sum())
        if "parse_error" in model_outputs.columns
        else 0,
        "first_timestamp": timestamps.min(),
        "last_timestamp": timestamps.max(),
    }


def generate_audit_report(
    *,
    report_dir: Path | None = None,
    tables_dir: Path | None = None,
    charts_dir: Path | None = None,
    outputs_path: Path | None = None,
) -> Path:
    """Generate ``audit_report.md`` and audit charts from computed tables.

    Args:
        report_dir: Destination for ``audit_report.md`` (default: ``results/report``).
        tables_dir: Directory with audit CSV tables (default: ``results/tables``).
        charts_dir: Directory for PNG charts (default: ``results/charts``).
        outputs_path: Path to ``model_outputs.csv`` (default: ``results/outputs/...``).

    Returns:
        Path to the generated markdown report.
    """
    from benchassist.config import get_settings

    settings = get_settings()
    report_dir = report_dir or (settings.RESULTS_DIR / "report")
    tables_dir = tables_dir or (settings.RESULTS_DIR / "tables")
    charts_dir = charts_dir or (settings.RESULTS_DIR / "charts")
    outputs_path = outputs_path or (settings.RESULTS_DIR / "outputs" / "model_outputs.csv")

    group_summary = pd.read_csv(tables_dir / "group_summary.csv")
    per_case = pd.read_csv(tables_dir / "per_case_comparison.csv")
    flagged_path = tables_dir / "flagged_cases.csv"
    flagged = pd.DataFrame()
    if flagged_path.exists() and flagged_path.stat().st_size > 0:
        try:
            flagged = pd.read_csv(flagged_path)
        except pd.errors.EmptyDataError:
            flagged = pd.DataFrame()
    model_outputs = pd.read_csv(outputs_path)

    dataset = _dataset_summary(model_outputs)
    run_info = _model_run_summary(model_outputs)
    chart_paths = generate_audit_charts(group_summary, charts_dir)

    example_ids = _select_qualitative_examples(flagged, per_case, n=3)
    qualitative = _build_qualitative_section(example_ids, model_outputs)

    flagged_display = flagged.head(10) if not flagged.empty else per_case[
        per_case["recommendation_flip"] == True  # noqa: E712
    ].head(10)
    if flagged_display.empty:
        flagged_display = per_case.head(10)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    charts_rel = "../charts"

    lines = [
        f"# {_REPORT_TITLE}",
        "",
        f"_Generated: {generated_at}_",
        "",
        "## 1. Project Title",
        "",
        "**BenchAssist-IL Fairness Audit** — Responsible AI evaluation of a prototype "
        "Israeli judicial decision-support assistant.",
        "",
        "## 2. System Description",
        "",
        "BenchAssist-IL is a non-binding assistant for judges and clerks. Given a short "
        "case summary, it returns a structured bench memo (legal area, urgency, "
        "recommended direction/action, reasoning, evidence needs, confidence, and "
        "limitations). Outputs are advisory only and must not replace judicial "
        "decision-making.",
        "",
        "## 3. Audit Objective",
        "",
        "This audit tests **counterfactual fairness**: when legal facts are held constant "
        "and only demographic or linguistic cues change (names, ethnicity markers, "
        "language register, etc.), do model recommendations change in ways that suggest "
        "unwarranted bias?",
        "",
        "## 4. Dataset Summary",
        "",
        f"- **Base cases:** {dataset['base_case_count']}",
        f"- **Model runs (variants):** {dataset['variant_count']}",
        f"- **Variant types ({len(dataset['variant_types'])}):** "
        + ", ".join(f"`{v}`" for v in dataset["variant_types"]),
        "",
        "## 5. Model / Run Information",
        "",
        f"- **Provider:** `{run_info['provider']}`",
        f"- **Model name:** `{run_info['model_name']}`",
        f"- **Runs in this report:** {run_info['run_count']}",
        f"- **Parse errors:** {run_info['parse_error_count']}",
        f"- **Run window:** {run_info['first_timestamp']} → {run_info['last_timestamp']}",
        "",
        "## 6. Group-Level Audit Metrics",
        "",
        _df_to_markdown_table(
            group_summary[
                [
                    "variant_type",
                    "demographic_cue",
                    "case_count",
                    "avg_urgency_score",
                    "avg_remedy_strength_score",
                    "avg_output_length_words",
                    "avg_evidence_count",
                    "avg_skepticism_score",
                    "avg_rights_or_protection_score",
                    "flip_rate",
                    "parse_error_rate",
                ]
            ]
        ),
        "",
        "## 7. Top Flagged Cases",
        "",
        _df_to_markdown_table(
            flagged_display[
                [
                    c
                    for c in [
                        "case_id",
                        "variant_type",
                        "demographic_cue",
                        "urgency",
                        "urgency_score_delta",
                        "remedy_strength_delta",
                        "skepticism_score",
                        "recommendation_flip",
                        "flags",
                    ]
                    if c in flagged_display.columns
                ]
            ],
            float_fmt=".2f",
        ),
        "",
        "## 8. Qualitative Examples",
        "",
        qualitative,
        "## 9. Charts",
        "",
        f"![Average urgency by variant type]({charts_rel}/urgency_by_variant_type.png)",
        "",
        f"![Average remedy strength by variant type]({charts_rel}/remedy_strength_by_variant_type.png)",
        "",
        f"![Flip rate by variant type]({charts_rel}/flip_rate_by_variant_type.png)",
        "",
        f"![Skepticism score by variant type]({charts_rel}/skepticism_by_variant_type.png)",
        "",
        "## 10. Limitations",
        "",
        "- BenchAssist-IL is a **toy / course prototype**, not a production system.",
        "- Cases are **synthetic** and may not reflect full legal complexity.",
        "- **Prompt design** may influence outputs independently of fairness.",
        "- **Legal correctness** requires review by qualified legal experts.",
        "- Metrics are **proxies** (urgency, remedy strength, wording cues) and are not "
        "definitive proof of discrimination.",
        "",
        "## 11. Next Steps",
        "",
        "- Expand the dataset with additional legal areas and fact patterns.",
        "- Add **Arabic** counterfactual variants and bilingual inputs.",
        "- Conduct **human legal review** of flagged cases.",
        "- Test **multiple models** (e.g. different Gemini versions, other providers).",
        "- Measure **robustness** across repeated generations with temperature > 0.",
        "",
        "---",
        "",
        "_Report generated by BenchAssist-IL Audit Toolkit._",
        "",
    ]

    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "audit_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Audit report written to %s", report_path)
    return report_path


def generate_report(metrics: dict[str, Any] | None = None, output_dir: Path | None = None) -> Path:
    """Generate the markdown audit report (legacy entry point).

    The *metrics* argument is ignored; the report reads from audit tables and
    ``model_outputs.csv`` produced by earlier pipeline stages.
    """
    _ = metrics
    from benchassist.config import get_settings

    settings = get_settings()
    report_dir = output_dir or (settings.RESULTS_DIR / "report")
    return generate_audit_report(report_dir=report_dir)


def main() -> None:
    """CLI entry point for ``python -m benchassist.report``."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    path = generate_audit_report()
    print(f"✓ Audit report: {path}")


if __name__ == "__main__":
    main()
