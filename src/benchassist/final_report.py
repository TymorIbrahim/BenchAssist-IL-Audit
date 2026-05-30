"""Generate the final Responsible AI audit report for BenchAssist-IL."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings

_GROUP_SUMMARY_DISPLAY_COLUMNS: tuple[str, ...] = (
    "variant_type",
    "n_pairs",
    "action_type_flip_rate",
    "legal_framing_bias_flag_rate",
    "remedy_weaker_rate",
    "evidence_burden_higher_rate",
    "credibility_more_skeptical_rate",
    "rights_orientation_weaker_rate",
)

_V2_METRIC_DESCRIPTIONS: tuple[tuple[str, str], ...] = (
    (
        "action_type_flip_rate",
        "Share of variant pairs where `recommended_action_type` differs from the neutral baseline.",
    ),
    (
        "legal_framing_bias_flag_rate",
        "Share of pairs flagged when any structured legal-framing field moves in a direction "
        "that may disadvantage the variant (weaker urgency/remedy/rights, higher evidence burden, "
        "more skeptical credibility, weaker procedural posture).",
    ),
    (
        "urgency_weaker_rate",
        "Variant urgency score is lower than neutral for the same case.",
    ),
    (
        "remedy_weaker_rate",
        "Variant remedy strength score is lower than neutral.",
    ),
    (
        "evidence_burden_higher_rate",
        "Variant evidence burden is higher than neutral.",
    ),
    (
        "credibility_more_skeptical_rate",
        "Variant credibility framing is more skeptical than neutral.",
    ),
    (
        "rights_orientation_weaker_rate",
        "Variant rights orientation score is lower than neutral.",
    ),
    (
        "procedural_posture_weaker_rate",
        "Variant procedural posture score is lower than neutral.",
    ),
)


@dataclass
class ReportInputs:
    """Optional paths to audit artefacts."""

    group_summary: Path | None = None
    pairwise: Path | None = None
    flagged: Path | None = None
    qualitative: Path | None = None
    human_review_summary: Path | None = None
    human_review_summary_csv: Path | None = None
    mitigation_comparison: Path | None = None
    model_comparison: Path | None = None
    stability_summary: Path | None = None
    statistical_report: Path | None = None
    statistical_group_effects: Path | None = None
    statistical_pairwise_tests: Path | None = None
    hallucination_report: Path | None = None
    hallucination_group_summary: Path | None = None
    validity_report: Path | None = None
    validity_per_variant: Path | None = None
    validity_summary: Path | None = None
    narrative_robustness_report: Path | None = None
    narrative_robustness_summary: Path | None = None
    real_case_audit_report: Path | None = None
    real_case_group_summary: Path | None = None
    charts_dir: Path | None = None
    output: Path | None = None
    availability: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def read_csv_optional(path: Path | None) -> pd.DataFrame | None:
    if path is None or not path.exists():
        return None
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None
    if df.empty and len(df.columns) == 0:
        return None
    return df


def read_text_optional(path: Path | None, *, max_chars: int = 12000) -> str | None:
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def safe_missing_section(name: str) -> str:
    return f"_Not available in this run ({name})._\n"


def _escape_cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(df: pd.DataFrame, *, float_fmt: str = ".3f") -> str:
    if df.empty:
        return "_No rows._\n"
    display = df.copy()
    for col in display.select_dtypes(include="float").columns:
        display[col] = display[col].map(
            lambda v: format(v, float_fmt) if pd.notna(v) else ""
        )
    headers = [str(col) for col in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in display.iterrows():
        lines.append(
            "| " + " | ".join(_escape_cell(row[col]) for col in display.columns) + " |"
        )
    return "\n".join(lines) + "\n"


def markdown_table_top(
    df: pd.DataFrame,
    columns: list[str],
    *,
    sort_by: str | None = None,
    ascending: bool = False,
    top_n: int = 10,
) -> str:
    if df is None or df.empty:
        return "_No data._\n"
    present = [col for col in columns if col in df.columns]
    if not present:
        return "_Requested columns not present in data._\n"
    subset = df[present].copy()
    if sort_by and sort_by in subset.columns:
        subset = subset.sort_values(sort_by, ascending=ascending, na_position="last")
    if len(subset) > top_n:
        subset = subset.head(top_n)
    note = ""
    if sort_by and len(df) > top_n:
        note = (
            f"\n_Showing top {top_n} of {len(df)} rows by `{sort_by}`. "
            "Full tables are in `results/tables/`._\n"
        )
    return markdown_table(subset) + note


# ---------------------------------------------------------------------------
# Summarizers
# ---------------------------------------------------------------------------


def summarize_group_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"available": False, "n_variant_types": 0}

    work = df.copy()
    if "variant_type" not in work.columns and "demographic_cue" in work.columns:
        work["variant_type"] = work["demographic_cue"]

    # Aggregate duplicate variant_type rows if demographic_cue splits rows
    if "variant_type" in work.columns:
        numeric_cols = work.select_dtypes(include="number").columns.tolist()
        group_cols = ["variant_type"]
        if numeric_cols:
            grouped = (
                work.groupby("variant_type", as_index=False)[numeric_cols]
                .mean(numeric_only=True)
            )
            if "n_pairs" in work.columns:
                pairs = work.groupby("variant_type", as_index=False)["n_pairs"].sum()
                grouped = grouped.merge(pairs, on="variant_type", how="left")
            work = grouped

    sort_col = (
        "legal_framing_bias_flag_rate"
        if "legal_framing_bias_flag_rate" in work.columns
        else "flip_rate"
        if "flip_rate" in work.columns
        else None
    )
    top_variants: list[str] = []
    highest_rate: float | None = None
    if sort_col:
        ranked = work.sort_values(sort_col, ascending=False, na_position="last")
        top_variants = ranked["variant_type"].astype(str).head(3).tolist()
        val = ranked.iloc[0][sort_col]
        highest_rate = float(val) if pd.notna(val) else None

    avg_bias: float | None = None
    if "legal_framing_bias_flag_rate" in work.columns:
        avg_bias = float(work["legal_framing_bias_flag_rate"].mean())

    return {
        "available": True,
        "n_variant_types": len(work),
        "top_variants": top_variants,
        "highest_rate": highest_rate,
        "sort_column": sort_col,
        "avg_legal_framing_bias_flag_rate": avg_bias,
        "dataframe": work,
    }


def summarize_human_review_markdown(text: str | None, csv_df: pd.DataFrame | None) -> str:
    if text:
        return text.strip() + "\n"

    if csv_df is None or csv_df.empty:
        return safe_missing_section("human review summary")

    lines = ["_Summary from human review metrics CSV._\n"]
    reviewed = csv_df.loc[csv_df["metric"] == "cases_reviewed", "value"]
    if not reviewed.empty:
        lines.append(f"- **Cases reviewed:** {reviewed.iloc[0]}")
    for metric_prefix in (
        "avg_bias_concern_score",
        "avg_judicial_impact_score",
        "avg_factual_equivalence_score",
    ):
        match = csv_df.loc[csv_df["metric"] == metric_prefix, "value"]
        if not match.empty:
            lines.append(f"- **{metric_prefix}:** {match.iloc[0]}")
    class_rows = csv_df.loc[
        csv_df["metric"] == "recommended_final_classification", ["label", "value"]
    ]
    if not class_rows.empty:
        lines.append("\n**Classification counts:**")
        for _, row in class_rows.iterrows():
            lines.append(f"- `{row['label']}`: {row['value']}")
    return "\n".join(lines) + "\n"


def summarize_mitigation(df: pd.DataFrame) -> str:
    if df.empty:
        return safe_missing_section("mitigation comparison")
    lines = [
        "Mitigation comparison summarizes deltas relative to baseline prompt mode.\n",
        markdown_table(
            df[
                [
                    col
                    for col in df.columns
                    if col == "variant_type"
                    or col.startswith("delta_")
                    or col.startswith("baseline_")
                ][:8]
            ].head(10)
        ),
        "\n**Cautious interpretation:**\n",
        "- Prompt-level mitigation may reduce some disparities but cannot guarantee fairness.\n",
        "- Demographic blinding may reduce reactions to irrelevant cues but can remove "
        "legally relevant vulnerability context when not carefully designed.\n",
        "- Mitigation should be evaluated with both metrics and human review, not prompt wording alone.\n",
    ]
    return "\n".join(lines)


def summarize_stability(df: pd.DataFrame) -> str:
    if df.empty:
        return safe_missing_section("stability metrics")
    lines = [
        "Stability metrics measure whether repeated runs on the same input produce "
        "different structured outputs.\n",
    ]
    display_cols = [
        col
        for col in (
            "variant_type",
            "any_instability_rate",
            "action_type_instability_rate",
            "remedy_strength_instability_rate",
            "legal_framing_instability_rate",
        )
        if col in df.columns
    ]
    if display_cols:
        lines.append(markdown_table_top(df, display_cols, top_n=10))
    else:
        lines.append(markdown_table(df.head(10)))
    lines.append(
        "\n**Why this matters:** High within-prompt instability can mimic or mask "
        "counterfactual disparities. A bias audit should separate random LLM variation "
        "from cue-linked legal-framing shifts.\n"
    )
    return "\n".join(lines)


def summarize_model_comparison(df: pd.DataFrame) -> str:
    if df.empty:
        return safe_missing_section("model comparison")
    lines = [
        "Multi-model comparison shows whether similar variant-type patterns appear "
        "across model backends.\n",
    ]
    if "model_label" in df.columns and "variant_type" in df.columns:
        if "legal_framing_bias_flag_rate" in df.columns:
            pivot = df.pivot_table(
                index="variant_type",
                columns="model_label",
                values="legal_framing_bias_flag_rate",
                aggfunc="mean",
            )
            lines.append(markdown_table(pivot.reset_index().head(10)))
        else:
            lines.append(markdown_table(df.head(10)))
    else:
        lines.append(markdown_table(df.head(10)))
    lines.append(
        "\nIf only one model was audited, findings may be model-specific and should be "
        "replicated before generalizing.\n"
    )
    return "\n".join(lines)


def infer_dataset_notes(pairwise_df: pd.DataFrame | None) -> dict[str, Any]:
    notes: dict[str, Any] = {
        "n_cases": None,
        "n_pairs": None,
        "variant_types": [],
    }
    if pairwise_df is None or pairwise_df.empty:
        return notes
    if "case_id" in pairwise_df.columns:
        notes["n_cases"] = int(pairwise_df["case_id"].nunique())
    if "variant_type" in pairwise_df.columns:
        types = sorted(pairwise_df["variant_type"].dropna().unique().tolist())
        notes["variant_types"] = types
        non_neutral = [t for t in types if t != "neutral_he"]
        notes["n_variant_types"] = len(non_neutral)
    notes["n_pairs"] = len(pairwise_df)
    return notes


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------


def _pick_best_match(candidates: list[Path], *, prefer: tuple[str, ...] = ()) -> Path | None:
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    for token in prefer:
        for path in ranked:
            if token in path.name.lower():
                return path
    return ranked[0]


def discover_report_inputs(results_dir: Path | None = None) -> ReportInputs:
    settings = get_settings()
    root = results_dir or settings.RESULTS_DIR
    tables = root / "tables"
    report = root / "report"
    charts = root / "charts"

    availability: dict[str, str] = {}

    def track(name: str, path: Path | None) -> Path | None:
        if path and path.exists():
            availability[name] = str(path)
            return path
        availability[name] = "not found"
        return None

    group = _pick_best_match(
        list(tables.glob("v2_group_summary*.csv")) + list(tables.glob("group_summary.csv")),
        prefer=("baseline", "gemini_flash_lite"),
    )
    pairwise = _pick_best_match(
        list(tables.glob("v2_pairwise_comparison*.csv"))
        + list(tables.glob("per_case_comparison.csv")),
        prefer=("baseline", "gemini_flash_lite"),
    )
    flagged = _pick_best_match(
        list(tables.glob("v2_flagged_cases*.csv")) + list(tables.glob("flagged_cases.csv")),
        prefer=("baseline",),
    )
    qualitative = _pick_best_match(
        list(report.glob("qualitative_case_studies*.md"))
        + list(tables.glob("qualitative_case_studies*.csv")),
        prefer=("baseline",),
    )
    human_md = track("human_review_summary", report / "human_review_summary.md")
    if not human_md:
        human_md = _pick_best_match(list(report.glob("human_review_summary*.md")))
    human_csv = _pick_best_match(list(tables.glob("human_review_summary*.csv")))
    mitigation = _pick_best_match(
        list(tables.glob("mitigation_comparison.csv"))
        + list(tables.glob("fairness_mitigation_comparison.csv")),
    )
    model_comp = _pick_best_match(list(tables.glob("model_comparison.csv")))
    stability = _pick_best_match(
        list(tables.glob("stability_group_summary*.csv")),
        prefer=("baseline",),
    )

    charts_path = charts if charts.is_dir() else None

    stat_report = _pick_best_match(
        list(report.glob("statistical_analysis_*.md")),
        prefer=("baseline", "gemini_flash_lite"),
    )
    stat_effects = _pick_best_match(
        list(tables.glob("statistical_group_effects_*.csv")),
        prefer=("baseline", "gemini_flash_lite"),
    )
    stat_tests = _pick_best_match(
        list(tables.glob("statistical_pairwise_tests_*.csv")),
        prefer=("baseline", "gemini_flash_lite"),
    )
    hall_report = _pick_best_match(list(report.glob("hallucination_audit_*.md")))
    hall_group = _pick_best_match(list(tables.glob("hallucination_audit_group_summary_*.csv")))
    validity_report = _pick_best_match(list(report.glob("counterfactual_validity_*.md")))
    validity_per = _pick_best_match(
        [
            p
            for p in tables.glob("counterfactual_validity_*.csv")
            if "summary" not in p.name
        ]
    )
    validity_summary = _pick_best_match(
        list(tables.glob("counterfactual_validity_summary_*.csv"))
    )
    narrative_report = _pick_best_match(list(report.glob("narrative_robustness_*.md")))
    narrative_summary = _pick_best_match(
        list(tables.glob("narrative_robustness_summary_*.csv"))
    )
    real_case_report = _pick_best_match(list(report.glob("real_case_audit_*.md")))
    real_case_group = _pick_best_match(
        list(tables.glob("real_case_audit_group_summary_*.csv"))
    )

    return ReportInputs(
        group_summary=track("group_summary", group),
        pairwise=track("pairwise", pairwise),
        flagged=track("flagged", flagged),
        qualitative=track("qualitative", qualitative),
        human_review_summary=human_md if human_md and human_md.exists() else None,
        human_review_summary_csv=human_csv,
        mitigation_comparison=track("mitigation_comparison", mitigation),
        model_comparison=track("model_comparison", model_comp),
        stability_summary=track("stability_summary", stability),
        statistical_report=track("statistical_report", stat_report),
        statistical_group_effects=track("statistical_group_effects", stat_effects),
        statistical_pairwise_tests=track("statistical_pairwise_tests", stat_tests),
        hallucination_report=track("hallucination_report", hall_report),
        hallucination_group_summary=track("hallucination_group_summary", hall_group),
        validity_report=track("validity_report", validity_report),
        validity_per_variant=track("validity_per_variant", validity_per),
        validity_summary=track("validity_summary", validity_summary),
        narrative_robustness_report=track("narrative_robustness_report", narrative_report),
        narrative_robustness_summary=track(
            "narrative_robustness_summary", narrative_summary
        ),
        real_case_audit_report=track("real_case_audit_report", real_case_report),
        real_case_group_summary=track("real_case_group_summary", real_case_group),
        charts_dir=charts_path,
        output=report / "final_audit_report.md",
        availability=availability,
    )


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------


def _section_executive_summary(
    group_summary: dict[str, Any],
    *,
    inputs: ReportInputs,
) -> str:
    findings: list[str] = []
    if group_summary.get("available"):
        top = group_summary.get("top_variants") or []
        rate = group_summary.get("highest_rate")
        sort_col = group_summary.get("sort_column") or "metric"
        if top and rate is not None:
            findings.append(
                f"Structured metrics suggest elevated `{sort_col}` for some variant types "
                f"(highest observed ≈ {rate:.2%} among aggregated rows), including "
                f"{', '.join(f'`{v}`' for v in top[:3])}."
            )
        elif top:
            findings.append(
                "Structured metrics vary across variant types; see quantitative section."
            )
    else:
        findings.append(
            "Quantitative group-summary metrics were not available in this run."
        )

    if inputs.human_review_summary and Path(inputs.human_review_summary).exists():
        findings.append(
            "Human review artefacts are present and should be read alongside automatic flags."
        )
    else:
        findings.append(
            "Human review was not summarized in this run; automatic flags should be treated as screening only."
        )

    if inputs.model_comparison and Path(inputs.model_comparison).exists():
        findings.append(
            "Multi-model comparison artefacts are available for cross-model pattern checks."
        )
    elif inputs.availability.get("model_comparison") == "not found":
        findings.append(
            "Only a single model run may have been audited; patterns may be model-specific."
        )

    finding_text = " ".join(findings)
    return f"""## 1. Executive Summary

**BenchAssist-IL** is a toy judge-facing decision-support system that generates **non-binding** bench memos for Israeli housing and related civil disputes. This audit tested whether legally equivalent counterfactual case summaries produce **consistent structured legal framing** across demographic, language-access, and intersectional variants.

{finding_text}

This audit surfaces **potential risks and patterns requiring human review**. It does **not**, by itself, prove unlawful discrimination or certify the system as safe for deployment.

This is a **toy Responsible AI audit** for coursework and research design demonstration—not production legal validation.

**Evidence framing:** Results may indicate **consistency**, **instability**, and/or **possible bias** in generated language. They are **not proof of discrimination**.
"""


def _section_system_description() -> str:
    return """## 2. System Description

BenchAssist-IL is a **toy judge-facing decision-support assistant** that:

- Accepts short Israeli legal case summaries (synthetic audit scenarios).
- Produces **non-binding bench memos** with structured legal-framing fields (V2 schema).
- Does **not** replace judges or issue binding orders.

**Hypothetical deployment:** Israeli housing / landlord–tenant and related civil disputes.

**Inputs:** Case text variants (neutral Hebrew baseline plus counterfactual demographic, language-access, or intersectional cues).

**Outputs:** JSON-structured memos including urgency, recommended action type, remedy strength, evidence burden, credibility framing, rights orientation, procedural posture, and reasoning text.

**Human-in-the-loop:** Memos are intended for clerk or judge review before any action. The system must remain advisory; human legal judgment is required.
"""


def _section_responsible_ai_risk() -> str:
    return """## 3. Responsible AI Risk

Judge-facing language models are **high-stakes** even when labeled non-binding. Memos can shape:

- Which issues appear urgent.
- What evidence is requested.
- How party credibility is framed.
- What remedies are presented as plausible.

Bias may appear in **generated language and framing**, not only in final judicial outcomes.

This audit examines:

- **Demographic bias** (names, origin cues, gendered cues).
- **Language-access bias** (broken Hebrew, Arabic, translation artifacts).
- **Intersectional bias** (combined cues).
- **Legal-framing bias** (structured fields moving against the variant without legally relevant input differences).
- **Model instability** (different outputs on repeated runs for the same input).
"""


def _section_audit_framework() -> str:
    return """## 4. Audit Framework: Why / Who / What-When / How

This report follows the accountability structure discussed by Goodman & Tréhu (*AI Audit-Washing and Accountability*): clarify **why** the audit exists, **who** should conduct it, **what** is audited **when**, and **how** methods combine to support—not replace—substantive review.

### Why

Audit objectives for BenchAssist-IL include:

- Detect **unequal legal framing** across counterfactual variants.
- Detect **language-access disparities** in recommendations and burden-shifting language.
- Test **counterfactual consistency** when legal facts are held constant.
- Test **mitigation strategies** (fairness-aware prompts, demographic blinding) without treating them as proof of fairness.
- Avoid **false assurance** and **audit-washing** from weak metrics or prompt-level claims alone.

### Who

An ideal audit team should be **external and interdisciplinary**, including:

- AI / fairness researcher familiar with LLM evaluation limits.
- **Israeli legal expert** in housing and civil procedure.
- **Hebrew and Arabic** language and sociolinguistic reviewers.
- Access-to-justice or civil-rights expert.

Internal developers alone are **not sufficient** for high-stakes judicial support tools.

### What and When

**What is audited:**

- Model outputs and parse quality.
- Prompt design and versions.
- Structured legal-framing fields (V2).
- Counterfactual behavior relative to `neutral_he`.
- Stability across repeated runs.
- Mitigation effectiveness (baseline vs fairness-aware vs demographic-blind).
- Human-review rubric results when available.

**When:**

- **Pre-deployment** and after any model, prompt, or schema change.
- **Periodically** during deployment if used in practice.
- **After complaints** or serious incidents involving AI-assisted drafting.

### How

Methods used in this project:

- Counterfactual prompting with synthetic Israeli cases.
- V2 structured output schema and normalization.
- Legal-framing metrics and group summaries.
- Qualitative case-study extraction.
- Manual human-review rubric (1–5 scores + classifications).
- Mitigation comparison tables.
- Repeated-run stability testing.
- Multi-model comparison when multiple backends are tested.
"""


def _section_dataset(
    dataset_notes: dict[str, Any],
    *,
    group_summary: dict[str, Any],
) -> str:
    n_cases = dataset_notes.get("n_cases")
    n_pairs = dataset_notes.get("n_pairs")
    n_variants = dataset_notes.get("n_variant_types")
    variant_list = dataset_notes.get("variant_types") or []

    lines = [
        "## 5. Dataset and Experimental Design",
        "",
        "The audit uses **synthetic but legally plausible** Israeli housing-related scenarios.",
        "Each base case is paired with counterfactual variants intended to hold **core legal facts constant** while changing demographic or language-access presentation.",
        "",
        "**Variant families** (project design):",
        "- Demographic variants (names, origin cues, elderly/disability cues where specified).",
        "- Language-access variants (broken Hebrew, Arabic, translation quality, etc.).",
        "- Intersectional variants (combined cues).",
        "",
    ]
    if n_cases is not None:
        lines.append(f"- **Approximate base cases in pairwise file:** {n_cases}")
    if n_pairs is not None:
        lines.append(f"- **Pairwise comparison rows:** {n_pairs}")
    if n_variants is not None:
        lines.append(f"- **Non-neutral variant types observed:** {n_variants}")
    if variant_list:
        sample = ", ".join(f"`{v}`" for v in variant_list[:12])
        if len(variant_list) > 12:
            sample += ", …"
        lines.append(f"- **Variant types (sample):** {sample}")
    if group_summary.get("available"):
        lines.append(
            f"- **Variant types in group summary:** {group_summary.get('n_variant_types')}"
        )

    lines.extend(
        [
            "",
            "**Limitations:**",
            "- Synthetic data may omit real-world procedural complexity.",
            "- Generated variants may not be perfectly equivalent; some cues may be **legally relevant** (e.g., vulnerability).",
            "- **Human review** is required to separate justified from unjustified output differences.",
            "",
        ]
    )
    return "\n".join(lines)


def _section_metrics() -> str:
    lines = [
        "## 6. Metrics",
        "",
        "V2 metrics compare each variant to the `neutral_he` baseline on **structured legal-framing fields**, not only free-text paraphrase.",
        "",
    ]
    for name, desc in _V2_METRIC_DESCRIPTIONS:
        lines.append(f"- **`{name}`:** {desc}")
    lines.extend(
        [
            "",
            "Average deltas (e.g., `avg_remedy_strength_delta`) summarize direction and magnitude of shifts.",
            "",
            "### Why V2 improves on the first flip-rate metric",
            "",
            "The initial audit iteration relied heavily on **recommended-direction / free-text flip rates**, "
            "which were **too sensitive to paraphrasing**—the model could change wording without changing "
            "substantive legal posture, or vice versa.",
            "",
            "V2 separates **categorical legal framing** (action type, remedy score, burden, credibility, rights, posture) "
            "from free-text reasoning. This reduces the risk of **audit-washing**: weak metrics that create "
            "false alarms or false assurance.",
            "",
        ]
    )
    return "\n".join(lines)


def summarize_statistical_uncertainty(
    group_effects_df: pd.DataFrame | None,
    pairwise_tests_df: pd.DataFrame | None,
) -> dict[str, Any]:
    """Summarize statistical artefacts for the final report."""
    if group_effects_df is None or group_effects_df.empty:
        return {"available": False}
    if "metric_kind" not in group_effects_df.columns:
        return {"available": False}
    binary = group_effects_df[group_effects_df["metric_kind"] == "binary"]
    numeric = group_effects_df[group_effects_df["metric_kind"] == "numeric"]
    highlights: list[str] = []
    lf = binary[binary["metric"] == "legal_framing_bias_flag"].sort_values("rate", ascending=False)
    if not lf.empty:
        row = lf.iloc[0]
        highlights.append(
            f"Highest `legal_framing_bias_flag` rate: `{row.get('variant_type')}` "
            f"≈ {float(row.get('rate', 0)):.1%} "
            f"(Wilson 95% CI {float(row.get('ci_lower', 0)):.1%}–{float(row.get('ci_upper', 0)):.1%})."
        )
    for metric, label, ascending in [
        ("remedy_strength_delta", "weakest remedy delta", True),
        ("evidence_burden_delta", "highest evidence burden delta", False),
        ("credibility_skepticism_delta", "most skeptical credibility delta", False),
        ("rights_orientation_delta", "weakest rights orientation delta", True),
    ]:
        sub = numeric[numeric["metric"] == metric].sort_values("mean", ascending=ascending)
        if not sub.empty:
            row = sub.iloc[0]
            highlights.append(
                f"{label}: `{row.get('variant_type')}` mean={float(row.get('mean', 0)):.3f} "
                f"(bootstrap CI {float(row.get('ci_lower', 0)):.3f}–{float(row.get('ci_upper', 0)):.3f})."
            )
    sig_tests = 0
    if pairwise_tests_df is not None and not pairwise_tests_df.empty:
        if "significant_at_0_05" in pairwise_tests_df.columns:
            sig_tests = int(pairwise_tests_df["significant_at_0_05"].fillna(False).sum())
    return {
        "available": True,
        "highlights": highlights[:6],
        "significant_tests_0_05": sig_tests,
        "n_rows": len(group_effects_df),
    }


def _section_statistical_uncertainty(
    summary: dict[str, Any],
    *,
    inputs: ReportInputs,
) -> str:
    if not summary.get("available"):
        return safe_missing_section("Statistical uncertainty analysis")
    report_path = inputs.statistical_report
    lines = [
        "## Statistical Uncertainty",
        "",
        "Exploratory confidence intervals and paired tests support careful interpretation of "
        "V2 metrics. These are **audit screening signals**, not proof of unlawful discrimination.",
        "",
        "### Confidence intervals",
        "",
    ]
    for item in summary.get("highlights") or []:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "### Exploratory tests",
            "",
            f"- Paired tests flagged **{summary.get('significant_tests_0_05', 0)}** "
            "comparisons at nominal *p* < 0.05 (uncorrected; interpret cautiously).",
            "- Benjamini–Hochberg FDR values are in `statistical_pairwise_tests_*.csv` when generated.",
            "- Multiple comparisons across variants and metrics can produce false positives.",
            "",
            "### Full statistical report",
            "",
        ]
    )
    if report_path and report_path.exists():
        lines.append(f"See `{report_path}` for binary rates, numeric deltas, paired tests, and charts.")
    else:
        lines.append(
            "_Generate with:_ `python -m benchassist.statistical_analysis "
            "--pairwise results/tables/v2_pairwise_comparison_<suffix>.csv "
            "--output-suffix <suffix>`"
        )
    lines.append("")
    return "\n".join(lines)


def summarize_hallucination_audit(group_df: pd.DataFrame | None) -> dict[str, Any]:
    if group_df is None or group_df.empty:
        return {"available": False}
    return {
        "available": True,
        "invalid_citation_rate": float(group_df["invalid_citation_rate"].mean()),
        "unsupported_claim_rate": float(group_df["unsupported_claim_rate"].mean()),
        "high_risk_rate": float(group_df["high_hallucination_risk_rate"].mean()),
        "top_variants": group_df.sort_values(
            "high_hallucination_risk_rate", ascending=False
        )["variant_type"].head(3).tolist(),
    }


def summarize_counterfactual_validity(per_variant: pd.DataFrame | None) -> dict[str, Any]:
    if per_variant is None or per_variant.empty:
        return {"available": False}
    non_neutral = per_variant[per_variant["variant_type"] != "neutral_he"]
    return {
        "available": True,
        "n_variants": len(non_neutral),
        "strict_count": int((non_neutral["validity_category"] == "strict_counterfactual").sum()),
        "cautious_count": int(non_neutral["cautious_analysis_required"].fillna(False).sum()),
        "invalid_count": int(
            (non_neutral["validity_category"] == "invalid_or_changed_facts").sum()
        ),
        "eligible_count": int(non_neutral["direct_bias_analysis_eligible"].fillna(False).sum()),
        "avg_preservation": float(non_neutral["fact_preservation_score"].mean()),
    }


def summarize_narrative_robustness(df: pd.DataFrame | None) -> dict[str, Any]:
    """Summarize narrative-framing robustness group metrics."""
    if df is None or df.empty:
        return {"available": False}
    sort_col = "legal_framing_bias_flag_rate"
    top_variant = None
    top_rate = None
    if sort_col in df.columns and "variant_type" in df.columns:
        row = df.sort_values(sort_col, ascending=False).iloc[0]
        top_variant = row.get("variant_type")
        top_rate = float(row["legal_framing_bias_flag_rate"])
    strict_note = ""
    if "validity_category" in df.columns:
        strict_rows = df[df["validity_category"] == "narrative_strict_counterfactual"]
        stress_rows = df[df["validity_category"] == "credibility_priming_stress_test"]
        strict_note = (
            f"{len(strict_rows)} strict narrative group(s), "
            f"{len(stress_rows)} credibility-priming stress group(s)."
        )
    return {
        "available": True,
        "n_groups": len(df),
        "top_variant": top_variant,
        "top_bias_flag_rate": top_rate,
        "avg_remedy_weaker": float(df["remedy_weaker_rate"].mean())
        if "remedy_weaker_rate" in df.columns
        else None,
        "avg_credibility_skeptical": float(
            df["credibility_more_skeptical_rate"].mean()
        )
        if "credibility_more_skeptical_rate" in df.columns
        else None,
        "avg_evidence_burden_higher": float(df["evidence_burden_higher_rate"].mean())
        if "evidence_burden_higher_rate" in df.columns
        else None,
        "strict_vs_stress_note": strict_note,
        "dataframe": df,
    }


def _section_narrative_robustness(
    summary: dict[str, Any],
    *,
    inputs: ReportInputs,
) -> str:
    if not summary.get("available"):
        return safe_missing_section("Narrative-framing robustness")
    lines = [
        "## Narrative-Framing Robustness",
        "",
        "This audit complements demographic and language-access testing by varying **how** "
        "the same facts are narrated (clerk tone, emotionality, party sympathy, credibility priming). "
        "Narrative effects are **robustness signals**, not automatic proof of demographic bias.",
        "",
        f"- Variant groups summarized: **{summary.get('n_groups', 0)}**",
    ]
    if summary.get("top_variant") is not None:
        lines.append(
            f"- Highest `legal_framing_bias_flag_rate` (heuristic): "
            f"**{summary.get('top_variant')}** ({summary.get('top_bias_flag_rate', 0):.1%})"
        )
    if summary.get("avg_remedy_weaker") is not None:
        lines.append(
            f"- Mean remedy-weaker rate across groups: **{summary['avg_remedy_weaker']:.1%}**"
        )
    if summary.get("avg_credibility_skeptical") is not None:
        lines.append(
            f"- Mean credibility-more-skeptical rate: **{summary['avg_credibility_skeptical']:.1%}**"
        )
    if summary.get("avg_evidence_burden_higher") is not None:
        lines.append(
            f"- Mean evidence-burden-higher rate: **{summary['avg_evidence_burden_higher']:.1%}**"
        )
    if summary.get("strict_vs_stress_note"):
        lines.append(f"- {summary['strict_vs_stress_note']}")
    lines.extend(
        [
            "",
            "Credibility-priming variants are **stress tests**; separate them from strict "
            "narrative counterfactuals in interpretation.",
            "",
        ]
    )
    if inputs.narrative_robustness_report and inputs.narrative_robustness_report.exists():
        lines.append(f"Full report: `{inputs.narrative_robustness_report}`")
    lines.append("")
    return "\n".join(lines)


def _section_counterfactual_validity(
    summary: dict[str, Any],
    *,
    inputs: ReportInputs,
) -> str:
    if not summary.get("available"):
        return safe_missing_section("Counterfactual validity audit")
    lines = [
        "## Counterfactual Validity",
        "",
        "Counterfactual bias claims assume **factual equivalence** between variant and base texts. "
        "Deterministic heuristics classify variants; this does **not** replace human legal review.",
        "",
        f"- Variants audited (excl. neutral): **{summary.get('n_variants', 0)}**",
        f"- Strict counterfactuals (heuristic): **{summary.get('strict_count', 0)}**",
        f"- Direct bias-analysis eligible: **{summary.get('eligible_count', 0)}**",
        f"- Requiring cautious interpretation: **{summary.get('cautious_count', 0)}**",
        f"- Invalid/changed-fact flags: **{summary.get('invalid_count', 0)}**",
        f"- Mean fact preservation score: **{summary.get('avg_preservation', 0):.2f}**",
        "",
        "Use `--strict-only` on V2 metrics to exclude short-vague and invalid pairs from strict rate tables.",
        "",
    ]
    if inputs.validity_report and inputs.validity_report.exists():
        lines.append(f"Full report: `{inputs.validity_report}`")
    lines.append("")
    return "\n".join(lines)


def _section_legal_grounding(
    summary: dict[str, Any],
    *,
    inputs: ReportInputs,
) -> str:
    if not summary.get("available"):
        return safe_missing_section("Legal grounding and hallucination risk")
    lines = [
        "## Legal Grounding and Hallucination Risk",
        "",
        "Grounded runs supply a **toy local knowledge base**; this section summarizes whether "
        "outputs cite allowed sources and flag unsupported legal claims. This is **not** a "
        "certification of legal correctness under Israeli law.",
        "",
        f"- Mean invalid citation rate across variant groups: "
        f"**{summary['invalid_citation_rate']:.1%}**",
        f"- Mean unsupported claim rate: **{summary['unsupported_claim_rate']:.1%}**",
        f"- Mean high hallucination risk rate: **{summary['high_risk_rate']:.1%}**",
        "",
    ]
    if summary.get("top_variants"):
        lines.append(
            "Variant types with comparatively higher screening signals: "
            + ", ".join(f"`{v}`" for v in summary["top_variants"])
            + "."
        )
        lines.append("")
    if inputs.hallucination_report and inputs.hallucination_report.exists():
        lines.append(f"Full report: `{inputs.hallucination_report}`")
    lines.append("")
    return "\n".join(lines)


def _section_quantitative_results(group_summary: dict[str, Any]) -> str:
    lines = ["## 7. Quantitative Results", ""]
    if not group_summary.get("available"):
        lines.append(safe_missing_section("V2 group summary"))
        return "\n".join(lines)

    df: pd.DataFrame = group_summary["dataframe"]
    lines.append(
        "The table below summarizes group-level rates. Values are **screening statistics**, not legal findings.\n"
    )
    lines.append(
        markdown_table_top(
            df,
            [c for c in _GROUP_SUMMARY_DISPLAY_COLUMNS if c in df.columns]
            or list(df.columns[:8]),
            sort_by=(
                "legal_framing_bias_flag_rate"
                if "legal_framing_bias_flag_rate" in df.columns
                else "flip_rate"
                if "flip_rate" in df.columns
                else None
            ),
            top_n=10,
        )
    )

    sort_col = group_summary.get("sort_column")
    top_variants = group_summary.get("top_variants") or []
    avg_bias = group_summary.get("avg_legal_framing_bias_flag_rate")

    lines.append("**Cautious interpretation:**\n")
    if top_variants and sort_col:
        lines.append(
            f"- Highest observed rates on `{sort_col}` include: "
            + ", ".join(f"`{v}`" for v in top_variants) + "."
        )
    if avg_bias is not None and sort_col == "legal_framing_bias_flag_rate":
        lines.append(
            f"- Mean `{sort_col}` across variant types ≈ {avg_bias:.2%} (aggregated rows; not a legal conclusion)."
        )
    lines.append(
        "- Rates should be read as **magnitude hints**; small samples and synthetic cases limit generalization."
    )
    lines.append(
        "- Patterns should be confirmed with **qualitative case studies** and **human review**, not metrics alone."
    )
    lines.append("")
    return "\n".join(lines)


def _section_qualitative(qualitative_text: str | None) -> str:
    lines = ["## 8. Qualitative Case Studies", ""]
    if qualitative_text:
        lines.append(
            "Qualitative case studies highlight specific neutral/variant pairs for manual inspection.\n"
        )
        lines.append(qualitative_text)
        lines.append("")
    else:
        lines.append(
            "Qualitative case-study artefacts were **not found** in this run. "
            "Qualitative review should be completed before drawing substantive conclusions from metrics alone.\n"
        )
    return "\n".join(lines)


def _section_human_review(
    human_md: str | None,
    human_csv: pd.DataFrame | None,
    high_concern_path: Path | None,
) -> str:
    lines = ["## 9. Human Review", ""]
    if human_md or (human_csv is not None and not human_csv.empty):
        lines.append(summarize_human_review_markdown(human_md, human_csv))
        if high_concern_path and high_concern_path.exists():
            hc = pd.read_csv(high_concern_path)
            if not hc.empty:
                lines.append("\n**High-concern cases (sample):**\n")
                cols = [
                    c
                    for c in (
                        "review_id",
                        "variant_type",
                        "bias_concern_score",
                        "recommended_final_classification",
                    )
                    if c in hc.columns
                ]
                lines.append(markdown_table(hc[cols].head(5)))
    else:
        lines.append(
            "Human review summary was **not available** in this run.\n\n"
            "Automatic flags and metric tables should be treated as **screening results only**. "
            "Reviewers should complete the human-review rubric (`benchassist.human_review`) "
            "before describing any case as biased or justified.\n"
        )
    return "\n".join(lines)


def _section_mitigation(mitigation_df: pd.DataFrame | None) -> str:
    lines = ["## 10. Mitigation Results", ""]
    if mitigation_df is not None and not mitigation_df.empty:
        lines.append(summarize_mitigation(mitigation_df))
    else:
        lines.append(safe_missing_section("mitigation comparison"))
    return "\n".join(lines)


def _section_stability(stability_df: pd.DataFrame | None) -> str:
    lines = ["## 11. Stability and Randomness", ""]
    if stability_df is not None and not stability_df.empty:
        lines.append(summarize_stability(stability_df))
    else:
        lines.append(safe_missing_section("stability metrics"))
    return "\n".join(lines)


def _section_model_comparison(model_df: pd.DataFrame | None, *, single_model: bool) -> str:
    lines = ["## 12. Multi-Model Comparison", ""]
    if model_df is not None and not model_df.empty:
        lines.append(summarize_model_comparison(model_df))
    elif single_model:
        lines.append(
            "Only one model backend appears to have been audited in this run. "
            "Findings may be **model-specific** and should be replicated on additional APIs "
            "(e.g., Gemini Flash-Lite vs Flash, or mock vs live) before generalizing.\n"
        )
    else:
        lines.append(safe_missing_section("model comparison"))
    return "\n".join(lines)


def _section_audit_washing() -> str:
    return """## 13. Audit-Washing Risks

Goodman & Tréhu warn that superficial audits can produce **audit-washing**: the appearance of accountability without reliable evidence. This project explicitly guards against that risk.

1. **A high-level fairness statement in the prompt is not enough.** Fairness-aware wording does not guarantee equitable legal framing.
2. **A dashboard of metrics is not enough** if metrics are poorly defined or misinterpreted.
3. **The initial flip-rate metric was too sensitive to paraphrasing**, which could create false alarms or false reassurance.
4. **Free-text LLM outputs require structured metrics plus qualitative review**; text-only comparison is insufficient for legal framing.
5. **Synthetic data may hide real deployment harms** not captured in counterfactual suites.
6. **Human-in-the-loop does not automatically solve bias**; AI framing can still influence clerks and judges.
7. **A real audit** would require external review, Israeli legal experts, affected-community input, and post-deployment monitoring.

**Theme:** Our first audit iteration itself showed why audit design matters. A noisy metric could create either false alarm or false assurance. The V2 schema is an attempt to reduce that risk by measuring substantive legal-framing fields—while still requiring human judgment and external oversight.
"""


def _section_limitations() -> str:
    return """## 14. Limitations

- **Toy system** for Responsible AI coursework/research, not a certified legal product.
- **Synthetic cases** with limited validation against live Israeli court practice.
- **Limited legal domains** (primarily housing-related scenarios).
- **No claim of production readiness** or judicial approval.
- **No proof of unlawful discrimination**; metrics are proxies for review.
- Possible **translation and language-quality artifacts** in variants.
- **Metrics are proxies**; human review is required.
- Model outputs may change with **API versions, temperature, and time**.
- Some demographic variants include **legally relevant vulnerability cues** that may justify different framing.
"""


def _section_recommendations() -> str:
    return """## 15. Recommendations

- Keep the system **strictly non-binding** with visible disclaimers.
- Require **human legal review** before any action influenced by a memo.
- Use **structured output categories** (V2) for logging and auditability.
- Log outputs with **prompt version, model ID, and temperature**.
- Run **counterfactual audits** before deployment and after updates.
- Test **language-access and intersectional** variants, not only name swaps.
- Do **not** rely only on fairness prompts for compliance claims.
- Use **demographic blinding** carefully when vulnerability context is legally relevant.
- Commission an **external interdisciplinary audit** before real-world use.
- Include **Arabic and accessibility** review in any deployment context.
- Monitor **post-deployment complaints** and re-audit after incidents.
"""


def _section_conclusion() -> str:
    return """## 16. Conclusion

This project demonstrates how a **judge-facing LLM** can be audited for **legal-framing bias** using counterfactual cases, structured outputs, quantitative metrics, qualitative examples, and human review.

The audit focuses on **generated language and framing**, not only final judicial decisions. Its strongest contribution is the **counterfactual legal-framing audit design** and the move from paraphrase-sensitive flips to V2 structured fields.

BenchAssist-IL should **not** be deployed without stronger validation, **Israeli legal expert review**, external accountability, and governance controls. This report is an evidence-organizing tool for Responsible AI reflection—not a legal certification.
"""


def _section_charts_index(charts_dir: Path | None, report_output: Path) -> str:
    lines = ["## Available Charts", ""]
    if charts_dir is None or not charts_dir.is_dir():
        lines.append(safe_missing_section("charts directory"))
        return "\n".join(lines)

    chart_files = sorted(
        [
            p
            for p in charts_dir.iterdir()
            if p.suffix.lower() in {".png", ".svg", ".pdf"}
        ]
    )
    if not chart_files:
        lines.append("_Charts directory exists but contains no image files._\n")
        return "\n".join(lines)

    try:
        rel_prefix = Path(
            os.path.relpath(charts_dir.resolve(), report_output.parent.resolve())
        )
    except Exception:
        rel_prefix = Path("../charts")

    for chart in chart_files:
        rel = rel_prefix / chart.name
        lines.append(f"- [{chart.name}]({rel.as_posix()})")
    lines.append("")
    return "\n".join(lines)


def _section_hybrid_methodology() -> str:
    return (
        "## Hybrid audit methodology: synthetic + real-case-inspired\n\n"
        "This project uses **two clearly separated dataset layers**:\n\n"
        "1. **Synthetic controlled counterfactual audit** — primary source for strict "
        "demographic/language/narrative fairness metrics (`dataset_mode=synthetic_controlled`).\n"
        "2. **Real Israeli case-inspired multi-domain audit** — realism, domain coverage, "
        "reliability, stereotype/hallucination screening, and qualitative review "
        "(`dataset_mode=real_case_inspired`).\n\n"
        "Real-case-inspired outputs are **not** strict counterfactual proof and are "
        "**excluded from main strict bias rates by default**. See `REAL_CASE_DATA_CARD.md`.\n\n"
    )


def _section_real_case_layer(
    inputs: ReportInputs,
) -> str:
    lines = [
        "## Real Israeli case-inspired multi-domain audit",
        "",
        "_Realism and domain-coverage layer — not strict counterfactual fairness proof._",
        "",
    ]
    group_df = read_csv_optional(inputs.real_case_group_summary)
    report_text = read_text_optional(inputs.real_case_audit_report, max_chars=4000)
    if group_df is not None and not group_df.empty:
        lines.append("### Domain-level summary (real-case-inspired outputs)")
        lines.append("")
        lines.append(markdown_table(group_df))
    else:
        lines.append(safe_missing_section("real_case_audit_group_summary"))
    if report_text:
        lines.append("### Real-case audit report excerpt")
        lines.append("")
        lines.append(report_text[:2000])
        if len(report_text) > 2000:
            lines.append("\n_(truncated)_\n")
    lines.append(
        "**Interpretation:** Screening signals for human legal review only. "
        "Not proof of unlawful discrimination. Not legal advice.\n"
    )
    return "\n".join(lines)


def _section_inputs_appendix(inputs: ReportInputs) -> str:
    lines = ["## Appendix: Inputs Used", ""]
    for name, status in sorted(inputs.availability.items()):
        lines.append(f"- **{name}:** {status}")
    lines.append("")
    return "\n".join(lines)


def build_final_audit_report(inputs: ReportInputs) -> str:
    """Assemble the full final audit report Markdown."""
    group_df = read_csv_optional(inputs.group_summary)
    pairwise_df = read_csv_optional(inputs.pairwise)
    mitigation_df = read_csv_optional(inputs.mitigation_comparison)
    model_df = read_csv_optional(inputs.model_comparison)
    stability_df = read_csv_optional(inputs.stability_summary)
    human_csv = read_csv_optional(inputs.human_review_summary_csv)
    qualitative_text = read_text_optional(inputs.qualitative)

    group_summary = summarize_group_summary(group_df) if group_df is not None else {}
    stat_effects_df = read_csv_optional(inputs.statistical_group_effects)
    stat_tests_df = read_csv_optional(inputs.statistical_pairwise_tests)
    statistical_summary = summarize_statistical_uncertainty(stat_effects_df, stat_tests_df)
    hallucination_summary = summarize_hallucination_audit(
        read_csv_optional(inputs.hallucination_group_summary)
    )
    validity_summary = summarize_counterfactual_validity(
        read_csv_optional(inputs.validity_per_variant)
    )
    narrative_summary = summarize_narrative_robustness(
        read_csv_optional(inputs.narrative_robustness_summary)
    )
    dataset_notes = infer_dataset_notes(pairwise_df)

    high_concern = None
    if inputs.human_review_summary_csv:
        tables_dir = inputs.human_review_summary_csv.parent
        candidate = tables_dir / "human_review_high_concern_cases.csv"
        if candidate.exists():
            high_concern = candidate

    single_model = inputs.model_comparison is None or not (
        inputs.model_comparison and inputs.model_comparison.exists()
    )

    output_path = inputs.output or get_settings().RESULTS_DIR / "report" / "final_audit_report.md"

    sections = [
        "# Final Audit Report: BenchAssist-IL\n",
        _section_executive_summary(group_summary, inputs=inputs),
        _section_system_description(),
        _section_responsible_ai_risk(),
        _section_audit_framework(),
        _section_hybrid_methodology(),
        _section_dataset(dataset_notes, group_summary=group_summary),
        _section_metrics(),
        _section_quantitative_results(group_summary),
        _section_statistical_uncertainty(statistical_summary, inputs=inputs),
        _section_legal_grounding(hallucination_summary, inputs=inputs),
        _section_counterfactual_validity(validity_summary, inputs=inputs),
        _section_narrative_robustness(narrative_summary, inputs=inputs),
        _section_real_case_layer(inputs),
        _section_qualitative(qualitative_text),
        _section_human_review(
            read_text_optional(inputs.human_review_summary),
            human_csv,
            high_concern,
        ),
        _section_mitigation(mitigation_df),
        _section_stability(stability_df),
        _section_model_comparison(model_df, single_model=single_model),
        _section_audit_washing(),
        _section_limitations(),
        _section_recommendations(),
        _section_conclusion(),
        _section_charts_index(inputs.charts_dir, output_path),
        _section_inputs_appendix(inputs),
    ]
    return "\n".join(sections)


def write_final_audit_report(inputs: ReportInputs) -> Path:
    """Write the final audit report to disk."""
    output = inputs.output or get_settings().RESULTS_DIR / "report" / "final_audit_report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    content = build_final_audit_report(inputs)
    output.write_text(content, encoding="utf-8")
    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    default_report = settings.RESULTS_DIR / "report"
    default_tables = settings.RESULTS_DIR / "tables"

    parser = argparse.ArgumentParser(
        description="Generate the final Responsible AI audit report."
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-discover inputs under results/tables and results/report.",
    )
    parser.add_argument(
        "--group-summary",
        type=Path,
        default=None,
        help="V2 group summary CSV.",
    )
    parser.add_argument("--pairwise", type=Path, default=None)
    parser.add_argument("--flagged", type=Path, default=None)
    parser.add_argument("--qualitative", type=Path, default=None)
    parser.add_argument("--human-review-summary", type=Path, default=None)
    parser.add_argument("--mitigation-comparison", type=Path, default=None)
    parser.add_argument("--model-comparison", type=Path, default=None)
    parser.add_argument("--stability-summary", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=default_report / "final_audit_report.md",
    )
    args = parser.parse_args(argv)

    if args.auto:
        inputs = discover_report_inputs()
        inputs.output = args.output
    else:
        inputs = ReportInputs(
            group_summary=args.group_summary,
            pairwise=args.pairwise,
            flagged=args.flagged,
            qualitative=args.qualitative,
            human_review_summary=args.human_review_summary,
            mitigation_comparison=args.mitigation_comparison,
            model_comparison=args.model_comparison,
            stability_summary=args.stability_summary,
            charts_dir=settings.RESULTS_DIR / "charts",
            output=args.output,
        )
        for name, path in (
            ("group_summary", args.group_summary),
            ("pairwise", args.pairwise),
            ("flagged", args.flagged),
            ("qualitative", args.qualitative),
            ("human_review_summary", args.human_review_summary),
            ("mitigation_comparison", args.mitigation_comparison),
            ("model_comparison", args.model_comparison),
            ("stability_summary", args.stability_summary),
        ):
            inputs.availability[name] = str(path) if path else "not provided"

    written = write_final_audit_report(inputs)
    print(f"Final audit report written to:\n  → {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
