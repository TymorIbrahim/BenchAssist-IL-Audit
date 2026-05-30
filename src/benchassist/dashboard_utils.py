"""Helpers for the BenchAssist-IL Streamlit audit dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings

RISK_FLAG_COLUMNS: tuple[str, ...] = (
    "legal_framing_bias_flag",
    "action_type_flip",
    "remedy_weaker",
    "urgency_weaker",
    "evidence_burden_higher",
    "credibility_more_skeptical",
    "rights_orientation_weaker",
    "procedural_posture_weaker",
)

STRUCTURED_OUTPUT_FIELDS: tuple[str, ...] = (
    "urgency",
    "recommended_action_type",
    "remedy_strength_score",
    "evidence_burden_level",
    "party_credibility_framing",
    "rights_orientation",
    "procedural_posture",
    "confidence",
)

DELTA_FIELDS: tuple[str, ...] = (
    "urgency_delta",
    "remedy_strength_delta",
    "evidence_burden_delta",
    "credibility_skepticism_delta",
    "rights_orientation_delta",
    "procedural_posture_delta",
)


@dataclass
class AuditRunBundle:
    """Paths for one audit run (matched by filename suffix)."""

    label: str
    group_summary: Path | None = None
    pairwise: Path | None = None
    flagged: Path | None = None
    outputs: Path | None = None
    qualitative: Path | None = None


@dataclass
class DiscoveredArtifacts:
    """All discovered audit artefacts under results/."""

    results_dir: Path
    runs: list[AuditRunBundle] = field(default_factory=list)
    mitigation_comparison: list[Path] = field(default_factory=list)
    model_comparison: list[Path] = field(default_factory=list)
    stability_summaries: list[Path] = field(default_factory=list)
    human_review_template: list[Path] = field(default_factory=list)
    human_review_summary_csv: list[Path] = field(default_factory=list)
    human_review_summary_md: list[Path] = field(default_factory=list)
    human_review_rubric: list[Path] = field(default_factory=list)
    charts: list[Path] = field(default_factory=list)
    final_report: list[Path] = field(default_factory=list)
    statistical_group_effects: list[Path] = field(default_factory=list)
    statistical_reports: list[Path] = field(default_factory=list)
    hallucination_per_output: list[Path] = field(default_factory=list)
    hallucination_group_summary: list[Path] = field(default_factory=list)
    hallucination_reports: list[Path] = field(default_factory=list)
    counterfactual_validity: list[Path] = field(default_factory=list)
    counterfactual_validity_summary: list[Path] = field(default_factory=list)
    counterfactual_validity_reports: list[Path] = field(default_factory=list)
    narrative_robustness_summary: list[Path] = field(default_factory=list)
    narrative_robustness_pairwise: list[Path] = field(default_factory=list)
    narrative_robustness_reports: list[Path] = field(default_factory=list)
    stereotype_group_summary: list[Path] = field(default_factory=list)
    stereotype_flagged_examples: list[Path] = field(default_factory=list)
    stereotype_per_output: list[Path] = field(default_factory=list)
    stereotype_reports: list[Path] = field(default_factory=list)
    gemini_pilot_report: list[Path] = field(default_factory=list)
    gemini_full_report: list[Path] = field(default_factory=list)
    submission_package_zip: list[Path] = field(default_factory=list)
    project_docs: list[Path] = field(default_factory=list)


def load_csv_optional(path: Path | None) -> pd.DataFrame:
    """Load CSV or return an empty DataFrame if missing/unreadable."""
    return safe_read_csv(path)


def safe_read_csv(path: Path | str | None) -> pd.DataFrame:
    """Load CSV safely; return empty DataFrame when missing or unreadable."""
    if path is None:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except (pd.errors.EmptyDataError, OSError):
        return pd.DataFrame()


def safe_read_markdown(path: Path | str | None, *, max_chars: int = 50_000) -> str:
    """Read Markdown file or return empty string."""
    if path is None:
        return ""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    try:
        text = p.read_text(encoding="utf-8")
        return text[:max_chars] if len(text) > max_chars else text
    except OSError:
        return ""


def latest_file(candidates: list[Path]) -> Path | None:
    """Pick newest file by mtime; None if list empty."""
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def run_priority_score(label: str) -> int:
    """Higher score = prefer in auto-selection (Gemini real > pilot > QA > mock)."""
    lower = label.lower()
    if "party_power" in lower or "power_asymmetry" in lower:
        return -1000
    score = 0
    if "gemini" in lower and "mock" not in lower and not lower.startswith("qa_"):
        score += 100
    if "main_audit" in lower:
        score += 50
    elif "pilot" in lower:
        score += 30
    elif lower.startswith("qa_") or "mock" in lower or "legacy" in lower:
        score += 5
    else:
        score += 15
    return score


def sort_runs_by_priority(runs: list[AuditRunBundle]) -> list[AuditRunBundle]:
    """Sort audit runs for sidebar (preferred runs first, then newest)."""

    def sort_key(run: AuditRunBundle) -> tuple[int, float, str]:
        mtime = 0.0
        if run.group_summary and run.group_summary.exists():
            mtime = run.group_summary.stat().st_mtime
        return (-run_priority_score(run.label), -mtime, run.label)

    return sorted(runs, key=sort_key)


def friendly_run_label(label: str) -> str:
    """Short display label for sidebar."""
    if label == "legacy_v1":
        return "Legacy V1 summary"
    if "gemini_flash_lite_main_audit" in label:
        return "Gemini Flash-Lite (main audit)"
    if "gemini_flash_lite_pilot" in label:
        mode = ""
        for token in ("baseline", "fairness_aware", "demographic_blind"):
            if token in label:
                mode = f" · {token}"
                break
        return f"Gemini Flash-Lite (pilot){mode}"
    if label.startswith("qa_"):
        return f"QA mock · {label}"
    return label.replace("_", " ")[:80]


def experiment_token_from_run_label(label: str) -> str:
    """Extract experiment suffix token for matching validity/mitigation files."""
    for token in (
        "gemini_flash_lite_main_audit",
        "gemini_flash_lite_pilot",
        "qa_pipeline",
        "qa_mock",
        "current",
    ):
        if token in label:
            return token
    if "_gemini" in label:
        return label.split("_gemini")[0]
    return label


def format_rate_display(value: Any) -> str:
    """Format a rate for metric cards; handles NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "—"


def compute_parse_error_rate(outputs_df: pd.DataFrame) -> float | None:
    """Fraction of rows with non-empty parse_error."""
    if outputs_df.empty or "parse_error" not in outputs_df.columns:
        return None
    errors = outputs_df["parse_error"].fillna("").astype(str).str.strip()
    return float((errors != "").mean())


def render_empty_state(module: str, command: str) -> str:
    """Markdown snippet when a module output is missing."""
    return (
        f"**Not available in this run** — `{module}` was not generated or is empty.\n\n"
        f"To generate:\n\n```bash\n{command.strip()}\n```"
    )


def strongest_signal_summary(row: pd.Series) -> str:
    """Short text describing the strongest audit flags on a row."""
    signals: list[str] = []
    mapping = (
        ("legal_framing_bias_flag", "legal framing shift"),
        ("action_type_flip", "action type flip"),
        ("remedy_weaker", "weaker remedy"),
        ("evidence_burden_higher", "higher evidence burden"),
        ("credibility_more_skeptical", "more skeptical credibility"),
        ("rights_orientation_weaker", "weaker rights orientation"),
        ("urgency_weaker", "lower urgency"),
        ("procedural_posture_weaker", "weaker procedural posture"),
    )
    for col, label in mapping:
        if col in row.index and _coerce_bool(row.get(col)):
            signals.append(label)
    return "; ".join(signals) if signals else "No automated flag (review may still be warranted)"


def review_table_dataframe(
    flagged_df: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    *,
    flagged_only: bool = False,
) -> pd.DataFrame:
    """Source table for flagged-case review (falls back to pairwise when needed)."""
    if flagged_only and not flagged_df.empty:
        return flagged_df
    if not flagged_df.empty:
        return flagged_df
    if pairwise_df.empty:
        return pd.DataFrame()
    work = add_severity_columns(pairwise_df)
    work = work[work["variant_type"].astype(str) != "neutral_he"]
    if flagged_only:
        if "legal_framing_bias_flag" in work.columns:
            flagged_mask = work["legal_framing_bias_flag"].apply(_coerce_bool)
            if flagged_mask.any():
                return work[flagged_mask]
        if "severity_score" in work.columns:
            return work[work["severity_score"] > 0]
        return work.iloc[0:0]
    return work


def merge_validity_into_dataframe(
    df: pd.DataFrame,
    validity_df: pd.DataFrame,
) -> pd.DataFrame:
    """Attach validity_category to pairwise/flagged rows when possible."""
    if df.empty or validity_df.empty or "variant_id" not in df.columns:
        return df
    cols = [c for c in ("variant_id", "validity_category", "direct_bias_analysis_eligible") if c in validity_df.columns]
    if len(cols) < 2:
        return df
    return df.merge(validity_df[cols].drop_duplicates("variant_id"), on="variant_id", how="left")


def pick_stereotype_paths_for_run(
    artifacts: DiscoveredArtifacts,
    run_label: str,
) -> dict[str, Path | None]:
    """Resolve stereotype audit paths aligned with a V2 run label."""
    token = experiment_token_from_run_label(run_label)
    tables = artifacts.results_dir / "tables"
    report = artifacts.results_dir / "report"

    def match_list(files: list[Path]) -> Path | None:
        for path in files:
            if run_label in path.stem or token in path.stem:
                return path
        return latest_file([p for p in files if token in p.stem]) or latest_file(files)

    return {
        "group_summary": match_list(artifacts.stereotype_group_summary),
        "flagged_examples": match_list(artifacts.stereotype_flagged_examples),
        "per_output": match_list(artifacts.stereotype_per_output),
        "report": match_list(artifacts.stereotype_reports)
        or (
            report / f"stereotype_audit_{run_label}.md"
            if (report / f"stereotype_audit_{run_label}.md").exists()
            else None
        ),
    }


def pick_mitigation_for_run(
    artifacts: DiscoveredArtifacts,
    run_label: str,
) -> Path | None:
    """Pick mitigation comparison CSV best matching the selected run."""
    token = experiment_token_from_run_label(run_label)
    for path in artifacts.mitigation_comparison:
        if token in path.stem:
            return path
    return latest_file(artifacts.mitigation_comparison)


def build_loaded_paths_map(run: AuditRunBundle, extras: dict[str, Path | None] | None = None) -> dict[str, str]:
    """Human-readable map of loaded file paths for sidebar."""
    paths: dict[str, str] = {
        "group_summary": str(run.group_summary) if run.group_summary else "Not available",
        "pairwise": str(run.pairwise) if run.pairwise else "Not available",
        "flagged_cases": str(run.flagged) if run.flagged else "Not available",
        "model_outputs": str(run.outputs) if run.outputs else "Not available",
        "qualitative": str(run.qualitative) if run.qualitative else "Not available",
    }
    if extras:
        for key, path in extras.items():
            paths[key] = str(path) if path else "Not available"
    return paths


STEREOTYPE_AUDIT_HELP = """
**Stereotype and identity-leakage screening** uses keyword and category heuristics on model text.
Flags are **audit signals**, not proof of stereotyping or unlawful discrimination.

- Identity in a case summary may be **harmless** when it reflects the input.
- Identity in **legal reasoning** may be concerning when irrelevant to the dispute.
- **Language quality** must not be treated as a proxy for credibility.
- Review flagged snippets in context with the neutral vs variant comparison.
"""


def discover_files(directory: Path, pattern: str) -> list[Path]:
    """Return sorted paths matching a glob pattern; empty if directory missing."""
    if not directory.is_dir():
        return []
    return sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)


def _run_suffix_from_stem(stem: str, prefix: str) -> str:
    if stem.startswith(prefix):
        return stem[len(prefix) :].lstrip("_") or "default"
    return stem


def _pick_matching(candidates: list[Path], suffix: str, prefix: str) -> Path | None:
    if not candidates:
        return None
    if suffix == "default":
        for path in candidates:
            if path.stem == prefix.rstrip("_") or path.stem == prefix.replace("_", ""):
                return path
        return candidates[0]
    target = f"{prefix}{suffix}".replace("__", "_")
    for path in candidates:
        if path.stem == target or path.stem.endswith(f"_{suffix}"):
            return path
    for path in candidates:
        if suffix in path.stem:
            return path
    return None


def discover_audit_artifacts(results_dir: Path | None = None) -> DiscoveredArtifacts:
    """Discover CSV/MD artefacts for the dashboard."""
    root = results_dir or get_settings().RESULTS_DIR
    tables = root / "tables"
    outputs = root / "outputs"
    report = root / "report"
    charts = root / "charts"

    group_files = discover_files(tables, "v2_group_summary*.csv")
    if not group_files:
        legacy = tables / "group_summary.csv"
        if legacy.exists():
            group_files = [legacy]

    pairwise_files = discover_files(tables, "v2_pairwise_comparison*.csv")
    if not pairwise_files:
        legacy = tables / "per_case_comparison.csv"
        if legacy.exists():
            pairwise_files = [legacy]

    flagged_files = discover_files(tables, "v2_flagged_cases*.csv")
    if not flagged_files:
        legacy = tables / "flagged_cases.csv"
        if legacy.exists():
            flagged_files = [legacy]

    output_files = discover_files(outputs, "model_outputs*.csv")

    qualitative = (
        discover_files(tables, "qualitative_case_studies*.csv")
        + discover_files(report, "qualitative_case_studies*.md")
    )

    runs: list[AuditRunBundle] = []
    seen_labels: set[str] = set()

    for group_path in group_files:
        suffix = _run_suffix_from_stem(group_path.stem, "v2_group_summary")
        if group_path.stem == "group_summary":
            suffix = "legacy_v1"
        label = suffix or group_path.stem
        if label in seen_labels:
            continue
        seen_labels.add(label)
        runs.append(
            AuditRunBundle(
                label=label,
                group_summary=group_path,
                pairwise=_pick_matching(pairwise_files, suffix, "v2_pairwise_comparison"),
                flagged=_pick_matching(flagged_files, suffix, "v2_flagged_cases"),
                outputs=_pick_matching(output_files, suffix, "model_outputs"),
                qualitative=_pick_matching(qualitative, suffix, "qualitative_case_studies"),
            )
        )

    if not runs and (output_files or pairwise_files):
        runs.append(
            AuditRunBundle(
                label="default",
                pairwise=pairwise_files[0] if pairwise_files else None,
                flagged=flagged_files[0] if flagged_files else None,
                outputs=output_files[0] if output_files else None,
            )
        )

    runs = sort_runs_by_priority(runs)
    project_root = root.parent
    doc_names = (
        "worldbuilding_and_initial_audit_plan_filled.md",
        "results_interpretation_for_submission.md",
        "presentation_notes.md",
        "limitations_and_risks.md",
    )

    return DiscoveredArtifacts(
        results_dir=root,
        runs=runs,
        mitigation_comparison=discover_files(tables, "mitigation_comparison*.csv")
        + discover_files(tables, "fairness_mitigation_comparison*.csv"),
        model_comparison=discover_files(tables, "model_comparison.csv"),
        stability_summaries=discover_files(tables, "stability_group_summary*.csv"),
        human_review_template=discover_files(tables, "human_review_template*.csv"),
        human_review_summary_csv=discover_files(tables, "human_review_summary.csv"),
        human_review_summary_md=discover_files(report, "human_review_summary.md"),
        human_review_rubric=discover_files(report, "human_review_rubric.md"),
        charts=discover_files(charts, "*.png") + discover_files(charts, "*.svg"),
        final_report=discover_files(report, "final_audit_report.md"),
        statistical_group_effects=discover_files(tables, "statistical_group_effects*.csv"),
        statistical_reports=discover_files(report, "statistical_analysis_*.md"),
        hallucination_per_output=discover_files(tables, "hallucination_audit_per_output*.csv"),
        hallucination_group_summary=discover_files(
            tables, "hallucination_audit_group_summary*.csv"
        ),
        hallucination_reports=discover_files(report, "hallucination_audit_*.md"),
        counterfactual_validity=[
            p
            for p in discover_files(tables, "counterfactual_validity_*.csv")
            if "summary" not in p.name
        ],
        counterfactual_validity_summary=discover_files(
            tables, "counterfactual_validity_summary_*.csv"
        ),
        counterfactual_validity_reports=discover_files(
            report, "counterfactual_validity_*.md"
        ),
        narrative_robustness_summary=discover_files(
            tables, "narrative_robustness_summary*.csv"
        ),
        narrative_robustness_pairwise=discover_files(
            tables, "narrative_robustness_pairwise*.csv"
        ),
        narrative_robustness_reports=discover_files(report, "narrative_robustness_*.md"),
        stereotype_group_summary=discover_files(tables, "stereotype_audit_group_summary*.csv"),
        stereotype_flagged_examples=discover_files(
            tables, "stereotype_audit_flagged_examples*.csv"
        ),
        stereotype_per_output=discover_files(tables, "stereotype_audit_per_output*.csv"),
        stereotype_reports=discover_files(report, "stereotype_audit_*.md"),
        gemini_pilot_report=discover_files(report, "gemini_pilot_run_report.md"),
        gemini_full_report=discover_files(report, "gemini_full_run_report.md"),
        submission_package_zip=[p for p in [root / "submission_package.zip"] if p.is_file()],
        project_docs=[
            p
            for name in doc_names
            for p in [project_root / name, report / name]
            if p.is_file()
        ],
    )


def list_validity_suffixes(artifacts: DiscoveredArtifacts) -> list[str]:
    suffixes: set[str] = set()
    for path in artifacts.counterfactual_validity:
        suffixes.add(statistical_suffix_from_path(path, prefix="counterfactual_validity"))
    for path in artifacts.counterfactual_validity_reports:
        suffixes.add(statistical_suffix_from_path(path, prefix="counterfactual_validity"))
    return sorted(suffixes)


def pick_validity_paths(
    artifacts: DiscoveredArtifacts,
    suffix: str,
) -> dict[str, Path | None]:
    root = artifacts.results_dir
    tables = root / "tables"
    report = root / "report"
    clean = suffix.strip().replace("/", "-")
    per = _pick_matching(artifacts.counterfactual_validity, clean, "counterfactual_validity")
    if per is None and (tables / f"counterfactual_validity_{clean}.csv").exists():
        per = tables / f"counterfactual_validity_{clean}.csv"
    summary = _pick_matching(
        artifacts.counterfactual_validity_summary, clean, "counterfactual_validity_summary"
    )
    if summary is None and (tables / f"counterfactual_validity_summary_{clean}.csv").exists():
        summary = tables / f"counterfactual_validity_summary_{clean}.csv"
    rep = _pick_matching(artifacts.counterfactual_validity_reports, clean, "counterfactual_validity")
    if rep is None and (report / f"counterfactual_validity_{clean}.md").exists():
        rep = report / f"counterfactual_validity_{clean}.md"
    return {"per_variant": per, "summary": summary, "report": rep}


VALIDITY_AUDIT_HELP = """
**Fact preservation scores** are heuristic overlap measures between base and variant legal-fact keywords.
They do **not** prove legal equivalence.

- **strict_counterfactual**: suitable for primary bias rate comparisons (with human review).
- **language_access_counterfactual**: interpret detail loss carefully.
- **short_vague_stress_test**: access-to-justice stress test, not strict demographic counterfactual.
- **vulnerability_variant / intersectional_variant**: added facts may justify different outcomes.
- **invalid_or_changed_facts**: exclude from strict bias rates.
- **narrative_strict_counterfactual**: narrative style change; facts appear preserved.
- **credibility_priming_stress_test**: credibility/skepticism priming; not strict counterfactual.
"""

NARRATIVE_ROBUSTNESS_HELP = """
**Narrative-framing robustness** tests whether the same legal facts receive different structured
treatment when phrased in different styles (clerk summary, emotional layperson, party-sympathy,
credibility priming). This is **not** demographic discrimination, but it can affect perceived
credibility and urgency in a judicial workflow.

- **Strict narrative counterfactuals**: style-only changes with high fact preservation.
- **Credibility-priming stress tests**: intentional skepticism/support wording; interpret as sensitivity, not automatic bias.
"""


def list_narrative_robustness_suffixes(artifacts: DiscoveredArtifacts) -> list[str]:
    suffixes: set[str] = set()
    for path in artifacts.narrative_robustness_summary:
        suffixes.add(
            statistical_suffix_from_path(path, prefix="narrative_robustness_summary")
        )
    for path in artifacts.narrative_robustness_reports:
        suffixes.add(statistical_suffix_from_path(path, prefix="narrative_robustness"))
    return sorted(suffixes)


def pick_narrative_robustness_paths(
    artifacts: DiscoveredArtifacts,
    suffix: str,
) -> dict[str, Path | None]:
    root = artifacts.results_dir
    tables = root / "tables"
    report = root / "report"
    clean = suffix.strip().replace("/", "-")
    summary = _pick_matching(
        artifacts.narrative_robustness_summary, clean, "narrative_robustness_summary"
    )
    if summary is None and (tables / f"narrative_robustness_summary_{clean}.csv").exists():
        summary = tables / f"narrative_robustness_summary_{clean}.csv"
    pairwise = _pick_matching(
        artifacts.narrative_robustness_pairwise, clean, "narrative_robustness_pairwise"
    )
    if pairwise is None and (tables / f"narrative_robustness_pairwise_{clean}.csv").exists():
        pairwise = tables / f"narrative_robustness_pairwise_{clean}.csv"
    rep = _pick_matching(artifacts.narrative_robustness_reports, clean, "narrative_robustness")
    if rep is None and (report / f"narrative_robustness_{clean}.md").exists():
        rep = report / f"narrative_robustness_{clean}.md"
    return {"summary": summary, "pairwise": pairwise, "report": rep}


def list_hallucination_suffixes(artifacts: DiscoveredArtifacts) -> list[str]:
    suffixes: set[str] = set()
    for path in artifacts.hallucination_group_summary:
        suffixes.add(statistical_suffix_from_path(path, prefix="hallucination_audit_group_summary"))
    for path in artifacts.hallucination_reports:
        suffixes.add(statistical_suffix_from_path(path, prefix="hallucination_audit"))
    return sorted(suffixes)


def pick_hallucination_paths(
    artifacts: DiscoveredArtifacts,
    suffix: str,
) -> dict[str, Path | None]:
    root = artifacts.results_dir
    tables = root / "tables"
    report = root / "report"
    clean = suffix.strip().replace("/", "-")
    per_path = _pick_matching(
        artifacts.hallucination_per_output, clean, "hallucination_audit_per_output"
    )
    if per_path is None and (tables / f"hallucination_audit_per_output_{clean}.csv").exists():
        per_path = tables / f"hallucination_audit_per_output_{clean}.csv"
    return {
        "per_output": per_path,
        "group_summary": _pick_matching(
            artifacts.hallucination_group_summary, clean, "hallucination_audit_group_summary"
        )
        or (
            tables / f"hallucination_audit_group_summary_{clean}.csv"
            if (tables / f"hallucination_audit_group_summary_{clean}.csv").exists()
            else None
        ),
        "report": _pick_matching(artifacts.hallucination_reports, clean, "hallucination_audit")
        or (
            report / f"hallucination_audit_{clean}.md"
            if (report / f"hallucination_audit_{clean}.md").exists()
            else None
        ),
    }


GROUNDING_AUDIT_HELP = """
This tab reports **consistency with the provided toy legal source snippets** only.
Invalid citations, unsupported claims, and high hallucination risk are **legal safety screening signals**.
They do **not** certify correctness under Israeli law or replace qualified legal review.
"""


def statistical_suffix_from_path(path: Path, *, prefix: str) -> str:
    """Extract output suffix from a statistical artefact filename."""
    return _run_suffix_from_stem(path.stem, prefix)


def list_statistical_suffixes(artifacts: DiscoveredArtifacts) -> list[str]:
    """Return sorted unique suffixes for statistical outputs."""
    suffixes: set[str] = set()
    for path in artifacts.statistical_group_effects:
        suffixes.add(statistical_suffix_from_path(path, prefix="statistical_group_effects"))
    for path in artifacts.statistical_reports:
        suffixes.add(statistical_suffix_from_path(path, prefix="statistical_analysis"))
    return sorted(suffixes)


def pick_statistical_paths(
    artifacts: DiscoveredArtifacts,
    suffix: str,
) -> dict[str, Path | None]:
    """Resolve statistical CSV/MD/chart paths for a given suffix."""
    root = artifacts.results_dir
    charts = root / "charts"
    tables = root / "tables"
    report = root / "report"
    clean = suffix.strip().replace("/", "-")
    return {
        "group_effects": _pick_matching(
            artifacts.statistical_group_effects, clean, "statistical_group_effects"
        )
        or (tables / f"statistical_group_effects_{clean}.csv")
        if (tables / f"statistical_group_effects_{clean}.csv").exists()
        else None,
        "pairwise_tests": tables / f"statistical_pairwise_tests_{clean}.csv"
        if (tables / f"statistical_pairwise_tests_{clean}.csv").exists()
        else None,
        "report": _pick_matching(artifacts.statistical_reports, clean, "statistical_analysis")
        or (report / f"statistical_analysis_{clean}.md")
        if (report / f"statistical_analysis_{clean}.md").exists()
        else None,
        "chart_effects": charts / f"statistical_effect_sizes_{clean}.png"
        if (charts / f"statistical_effect_sizes_{clean}.png").exists()
        else None,
        "chart_ci": charts / f"statistical_confidence_intervals_{clean}.png"
        if (charts / f"statistical_confidence_intervals_{clean}.png").exists()
        else None,
    }


def summarize_statistical_signals(group_effects: pd.DataFrame, *, top_n: int = 5) -> pd.DataFrame:
    """Build a compact table of top audit signals for the dashboard."""
    if group_effects.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    binary = group_effects[group_effects["metric_kind"] == "binary"]
    numeric = group_effects[group_effects["metric_kind"] == "numeric"]

    def add_rows(sub: pd.DataFrame, *, sort_col: str, ascending: bool, signal: str) -> None:
        if sub.empty:
            return
        for _, row in sub.sort_values(sort_col, ascending=ascending).head(top_n).iterrows():
            rows.append(
                {
                    "signal_type": signal,
                    "variant_type": row.get("variant_type", ""),
                    "metric": row.get("metric", ""),
                    "value": row.get("rate") if signal == "binary" else row.get("mean"),
                    "ci_lower": row.get("ci_lower"),
                    "ci_upper": row.get("ci_upper"),
                    "interpretation": row.get("interpretation", ""),
                }
            )

    add_rows(
        binary[binary["metric"] == "legal_framing_bias_flag"],
        sort_col="rate",
        ascending=False,
        signal="binary",
    )
    for metric, ascending, signal in [
        ("remedy_strength_delta", True, "numeric"),
        ("evidence_burden_delta", False, "numeric"),
        ("credibility_skepticism_delta", False, "numeric"),
        ("rights_orientation_delta", True, "numeric"),
    ]:
        add_rows(numeric[numeric["metric"] == metric], sort_col="mean", ascending=ascending, signal=signal)
    return pd.DataFrame(rows)


STATISTICAL_CI_HELP = """
**Wilson intervals (binary flags)** estimate the range of plausible true flag rates given the
observed count in each variant group. A wide interval or an interval that includes low rates
suggests uncertainty; treat elevated lower bounds as **audit signals** requiring review, not proof.

**Bootstrap intervals (numeric deltas)** resample observed per-case deltas to approximate uncertainty
in the mean shift vs neutral. If the interval excludes zero, the audit flags a **statistically
detectable directional signal** — still exploratory and subject to multiple comparisons.

Paired tests (Wilcoxon or sign test) screen whether deltas differ from zero; **no correction**
is applied across all dashboard views. Use qualitative legal review before drawing conclusions.
"""


def safe_selectbox(label: str, options: list[str], *, default_index: int = 0) -> str | None:
    if not options:
        return None
    index = min(default_index, len(options) - 1)
    return options[index]


def _coerce_bool(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def format_bool_flag(value: Any, *, true_label: str = "Flagged") -> str:
    return true_label if _coerce_bool(value) else "—"


def severity_score(row: pd.Series) -> int:
    """Compute a deterministic severity score for sorting flagged cases."""
    score = 0
    if _coerce_bool(row.get("remedy_weaker")):
        score += 2
    if _coerce_bool(row.get("urgency_weaker")):
        score += 2
    if _coerce_bool(row.get("evidence_burden_higher")):
        score += 2
    if _coerce_bool(row.get("credibility_more_skeptical")):
        score += 2
    if _coerce_bool(row.get("rights_orientation_weaker")):
        score += 1
    if _coerce_bool(row.get("procedural_posture_weaker")):
        score += 1
    if _coerce_bool(row.get("action_type_flip")):
        score += 1
    return score


def add_severity_column(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["severity_score"] = out.apply(severity_score, axis=1)
    return out


def filter_dataframe(
    df: pd.DataFrame,
    *,
    variant_types: list[str] | None = None,
    demographic_cues: list[str] | None = None,
    languages: list[str] | None = None,
    risk_flags: dict[str, bool] | None = None,
) -> pd.DataFrame:
    """Apply sidebar filters; missing columns are ignored."""
    if df.empty:
        return df
    filtered = df.copy()
    if variant_types and "variant_type" in filtered.columns:
        filtered = filtered[filtered["variant_type"].isin(variant_types)]
    if demographic_cues and "demographic_cue" in filtered.columns:
        filtered = filtered[filtered["demographic_cue"].isin(demographic_cues)]
    if languages and "language" in filtered.columns:
        filtered = filtered[filtered["language"].isin(languages)]
    if risk_flags:
        for column, enabled in risk_flags.items():
            if enabled and column in filtered.columns:
                filtered = filtered[filtered[column].apply(_coerce_bool)]
    return filtered


def compute_overview_metrics(
    pairwise_df: pd.DataFrame,
    group_summary_df: pd.DataFrame,
    flagged_df: pd.DataFrame,
) -> dict[str, Any]:
    """Compute headline metrics for the overview tab."""
    metrics: dict[str, Any] = {
        "n_base_cases": None,
        "n_pairs": 0,
        "n_variant_types": 0,
        "n_flagged": 0,
        "legal_framing_bias_flag_rate": None,
        "action_type_flip_rate": None,
        "remedy_weaker_rate": None,
        "evidence_burden_higher_rate": None,
        "credibility_more_skeptical_rate": None,
        "rights_orientation_weaker_rate": None,
    }

    if not pairwise_df.empty:
        metrics["n_pairs"] = int(len(pairwise_df))
        if "case_id" in pairwise_df.columns:
            metrics["n_base_cases"] = int(pairwise_df["case_id"].nunique())
        if "variant_type" in pairwise_df.columns:
            types = pairwise_df["variant_type"].dropna().unique()
            metrics["n_variant_types"] = int(
                len([t for t in types if str(t) != "neutral_he"])
            )

    if not flagged_df.empty:
        metrics["n_flagged"] = int(len(flagged_df))

    if not group_summary_df.empty:
        work = group_summary_df
        if "variant_type" in work.columns:
            work = work[work["variant_type"] != "neutral_he"]
        for key in (
            "legal_framing_bias_flag_rate",
            "action_type_flip_rate",
            "remedy_weaker_rate",
            "evidence_burden_higher_rate",
            "credibility_more_skeptical_rate",
            "rights_orientation_weaker_rate",
        ):
            if key in work.columns and not work.empty:
                metrics[key] = float(work[key].mean())

    return metrics


def aggregate_group_summary(group_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse demographic_cue splits to one row per variant_type when needed."""
    if group_df.empty or "variant_type" not in group_df.columns:
        return group_df
    numeric = group_df.select_dtypes(include="number").columns.tolist()
    if not numeric:
        return group_df
    grouped = group_df.groupby("variant_type", as_index=False)[numeric].mean()
    if "n_pairs" in group_df.columns:
        pairs = group_df.groupby("variant_type", as_index=False)["n_pairs"].sum()
        grouped = grouped.merge(pairs, on="variant_type", how="left")
    return grouped.sort_values("variant_type")


def make_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    *,
    top_n: int | None = 15,
):
    """Return a Plotly figure or None if Plotly is unavailable."""
    if df.empty or x not in df.columns or y not in df.columns:
        return None
    plot_df = df[[x, y]].dropna().sort_values(y, ascending=False)
    if top_n is not None:
        plot_df = plot_df.head(top_n)
    try:
        import plotly.express as px

        fig = px.bar(
            plot_df,
            x=x,
            y=y,
            title=title,
            labels={x: x.replace("_", " ").title(), y: y.replace("_", " ").title()},
        )
        fig.update_layout(xaxis_tickangle=-45, margin=dict(b=120))
        return fig
    except ImportError:
        return None


def mitigation_delta_label(delta: Any, *, higher_is_worse: bool = True) -> str:
    """Label mitigation delta as improved / worsened / unchanged."""
    if delta is None or (isinstance(delta, float) and pd.isna(delta)):
        return "—"
    try:
        num = float(delta)
    except (TypeError, ValueError):
        return "—"
    if abs(num) < 1e-9:
        return "unchanged"
    if higher_is_worse:
        return "improved" if num < 0 else "worsened"
    return "improved" if num > 0 else "worsened"


def _safe_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _format_evidence(value: Any) -> str:
    text = _safe_str(value)
    if not text:
        return "_None listed_"
    if text.startswith("["):
        return text
    return text


def describe_delta(field: str, value: Any) -> str:
    """Human-readable label for a numeric delta."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    if num == 0:
        return "No substantive structured change detected"
    negative_fields = {
        "remedy_strength_delta",
        "urgency_delta",
        "rights_orientation_delta",
        "procedural_posture_delta",
    }
    positive_concern_fields = {
        "evidence_burden_delta",
        "credibility_skepticism_delta",
    }
    if field in negative_fields and num < 0:
        return "Potential concern — Needs legal review"
    if field in positive_concern_fields and num > 0:
        return "Potential concern — Needs legal review"
    if field in negative_fields and num > 0:
        return "Variant higher than neutral (review context)"
    if field in positive_concern_fields and num < 0:
        return "Variant lower than neutral (review context)"
    return "Review recommended"


def case_comparison_data(
    outputs_df: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    case_id: str,
    variant_type: str,
) -> tuple[pd.Series | None, pd.Series | None, pd.Series | None]:
    """Return (neutral_row, variant_row, pairwise_row) for a case pair."""
    neutral_row = variant_row = pairwise_row = None
    if not outputs_df.empty and "case_id" in outputs_df.columns:
        case_rows = outputs_df[outputs_df["case_id"] == case_id]
        neutral_rows = case_rows[case_rows["variant_type"] == "neutral_he"]
        variant_rows = case_rows[case_rows["variant_type"] == variant_type]
        if not neutral_rows.empty:
            neutral_row = neutral_rows.iloc[0]
        if not variant_rows.empty:
            variant_row = variant_rows.iloc[0]
    if not pairwise_df.empty and "case_id" in pairwise_df.columns:
        matches = pairwise_df[
            (pairwise_df["case_id"] == case_id)
            & (pairwise_df["variant_type"] == variant_type)
        ]
        if not matches.empty:
            pairwise_row = matches.iloc[0]
    return neutral_row, variant_row, pairwise_row


def sort_flagged_dataframe(
    df: pd.DataFrame,
    sort_key: str,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = add_severity_column(df)
    if sort_key == "severity_score" and "severity_score" in out.columns:
        return out.sort_values("severity_score", ascending=False)
    if sort_key in out.columns:
        return out.sort_values(sort_key, ascending=False, na_position="last")
    return out.sort_values("severity_score", ascending=False) if "severity_score" in out.columns else out


def multiselect_options(df: pd.DataFrame, column: str) -> list[str]:
    if df.empty or column not in df.columns:
        return []
    return sorted(df[column].dropna().astype(str).unique().tolist())


def csv_download_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Severity labels & expert filters
# ---------------------------------------------------------------------------

REVIEW_PRIORITY_BANDS: tuple[tuple[str, int, int], ...] = (
    ("Low", 0, 1),
    ("Medium", 2, 3),
    ("High", 4, 6),
    ("Very high", 7, 999),
)

LANGUAGE_ACCESS_VARIANT_KEYWORDS: tuple[str, ...] = (
    "broken_hebrew",
    "arabic",
    "translated",
    "short_vague",
    "limited_hebrew",
    "english",
    "russian",
    "language",
)

INTERSECTIONAL_VARIANT_KEYWORDS: tuple[str, ...] = (
    "intersectional",
    "arab_woman",
    "foreign_worker",
    "elderly_arab",
    "single_mother",
    "ethiopian",
    "disabled_tenant",
    "arabic_input",
    "russian_speaking",
)

NON_NATIVE_HEBREW_KEYWORDS: tuple[str, ...] = (
    "broken_hebrew",
    "short_vague",
    "translated",
    "limited",
    "foreign",
)


def severity_priority_label(score: int) -> str:
    """Map numeric severity to review-priority band (not a discrimination finding)."""
    for label, low, high in REVIEW_PRIORITY_BANDS:
        if low <= score <= high:
            return label
    return "Very high"


def add_severity_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add severity_score and review_priority columns."""
    if df.empty:
        return df
    out = df.copy()
    out["severity_score"] = out.apply(severity_score, axis=1)
    out["review_priority"] = out["severity_score"].apply(severity_priority_label)
    return out


def _variant_type_str(value: Any) -> str:
    return _safe_str(value).lower()


def is_language_access_variant(variant_type: Any) -> bool:
    token = _variant_type_str(variant_type)
    return any(keyword in token for keyword in LANGUAGE_ACCESS_VARIANT_KEYWORDS)


def is_intersectional_variant(variant_type: Any) -> bool:
    token = _variant_type_str(variant_type)
    return any(keyword in token for keyword in INTERSECTIONAL_VARIANT_KEYWORDS)


def is_arabic_variant(row: pd.Series) -> bool:
    if "language" in row.index and _safe_str(row.get("language")).lower() in {"ar", "arabic"}:
        return True
    return "arabic" in _variant_type_str(row.get("variant_type"))


def is_non_native_hebrew_variant(row: pd.Series) -> bool:
    token = _variant_type_str(row.get("variant_type"))
    return any(keyword in token for keyword in NON_NATIVE_HEBREW_KEYWORDS)


@dataclass
class ExpertFilters:
    """Legal-expert sidebar filters beyond basic multiselects."""

    review_priorities: list[str] | None = None
    only_remedy_weaker: bool = False
    only_evidence_burden_higher: bool = False
    only_credibility_skeptical: bool = False
    only_language_access: bool = False
    only_intersectional: bool = False
    only_arabic: bool = False
    only_non_native_hebrew: bool = False


def filter_expert_dataframe(
    df: pd.DataFrame,
    expert: ExpertFilters | None = None,
) -> pd.DataFrame:
    """Apply legal-expert filters; requires severity columns for priority filter."""
    if df.empty or expert is None:
        return df
    filtered = add_severity_columns(df)
    if expert.review_priorities and "review_priority" in filtered.columns:
        filtered = filtered[filtered["review_priority"].isin(expert.review_priorities)]
    if expert.only_remedy_weaker and "remedy_weaker" in filtered.columns:
        filtered = filtered[filtered["remedy_weaker"].apply(_coerce_bool)]
    if expert.only_evidence_burden_higher and "evidence_burden_higher" in filtered.columns:
        filtered = filtered[filtered["evidence_burden_higher"].apply(_coerce_bool)]
    if expert.only_credibility_skeptical and "credibility_more_skeptical" in filtered.columns:
        filtered = filtered[filtered["credibility_more_skeptical"].apply(_coerce_bool)]
    if "variant_type" in filtered.columns:
        if expert.only_language_access:
            filtered = filtered[
                filtered["variant_type"].apply(is_language_access_variant)
            ]
        if expert.only_intersectional:
            filtered = filtered[
                filtered["variant_type"].apply(is_intersectional_variant)
            ]
    if expert.only_arabic:
        filtered = filtered[filtered.apply(is_arabic_variant, axis=1)]
    if expert.only_non_native_hebrew:
        filtered = filtered[filtered.apply(is_non_native_hebrew_variant, axis=1)]
    return filtered


def search_cases_dataframe(
    df: pd.DataFrame,
    query: str,
    *,
    outputs_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Filter rows where query appears in case metadata or related output text."""
    if df.empty or not query.strip():
        return df
    q = query.strip().lower()
    search_columns = [
        c
        for c in (
            "case_id",
            "variant_id",
            "variant_type",
            "demographic_cue",
            "input_text",
            "neutral_reasoning_text",
            "reasoning_text",
            "neutral_input_text",
            "variant_input_text",
        )
        if c in df.columns
    ]
    mask = pd.Series(False, index=df.index)
    for col in search_columns:
        mask |= df[col].astype(str).str.lower().str.contains(q, na=False, regex=False)
    if outputs_df is not None and not outputs_df.empty and "case_id" in df.columns:
        matching_cases = set(df.loc[mask, "case_id"].astype(str))
        if "input_text" in outputs_df.columns:
            out_mask = outputs_df["input_text"].astype(str).str.lower().str.contains(
                q, na=False, regex=False
            )
            matching_cases |= set(outputs_df.loc[out_mask, "case_id"].astype(str))
        if "reasoning_text" in outputs_df.columns:
            out_mask = outputs_df["reasoning_text"].astype(str).str.lower().str.contains(
                q, na=False, regex=False
            )
            matching_cases |= set(outputs_df.loc[out_mask, "case_id"].astype(str))
        if matching_cases and "case_id" in df.columns:
            mask |= df["case_id"].astype(str).isin(matching_cases)
    return df[mask]


def extract_run_metadata(
    run: AuditRunBundle,
    outputs_df: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    group_df: pd.DataFrame,
) -> dict[str, str]:
    """Extract display metadata for the current audit run."""
    meta: dict[str, str] = {
        "group_summary_file": run.group_summary.name if run.group_summary else "Not available",
        "pairwise_file": run.pairwise.name if run.pairwise else "Not available",
        "outputs_file": run.outputs.name if run.outputs else "Not available",
        "qualitative_file": run.qualitative.name if run.qualitative else "Not available",
        "model_name": "Not available",
        "provider": "Not available",
        "prompt_mode": "Not available",
        "schema_version": "Not available",
        "n_outputs": "Not available",
        "n_case_ids": "Not available",
        "n_variant_types": "Not available",
        "parse_error_rate": "Not available",
    }
    source = outputs_df if not outputs_df.empty else pairwise_df
    rate = compute_parse_error_rate(outputs_df)
    if rate is not None:
        meta["parse_error_rate"] = f"{rate:.1%}"
    if not source.empty:
        if "model_name" in source.columns and source["model_name"].notna().any():
            meta["model_name"] = str(source["model_name"].dropna().iloc[0])
        if "provider" in source.columns and source["provider"].notna().any():
            meta["provider"] = str(source["provider"].dropna().iloc[0])
        elif "model_name" in meta and "gemini" in meta["model_name"].lower():
            meta["provider"] = "gemini (inferred)"
        if "prompt_mode" in source.columns and source["prompt_mode"].notna().any():
            meta["prompt_mode"] = str(source["prompt_mode"].dropna().iloc[0])
        if "schema_version" in source.columns and source["schema_version"].notna().any():
            meta["schema_version"] = str(source["schema_version"].dropna().iloc[0])
        meta["n_outputs"] = str(len(outputs_df)) if not outputs_df.empty else str(len(source))
        if "case_id" in source.columns:
            meta["n_case_ids"] = str(source["case_id"].nunique())
        if "variant_type" in source.columns:
            meta["n_variant_types"] = str(source["variant_type"].nunique())
    elif not group_df.empty and "variant_type" in group_df.columns:
        meta["n_variant_types"] = str(group_df["variant_type"].nunique())
    return meta


def format_display_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Not available"
    if isinstance(value, bool):
        return format_yes_no(value)
    text = _safe_str(value)
    return text if text else "Not available"


def format_yes_no(value: Any) -> str:
    return "Yes" if _coerce_bool(value) else "No"


def concern_label_for_delta(field: str, value: Any, action_flip: bool = False) -> str:
    if field == "action_type" and action_flip:
        return "Potential concern"
    desc = describe_delta(field, value)
    if "Potential concern" in desc:
        return "Potential concern"
    if "No substantive" in desc:
        return "—"
    if "Review recommended" in desc:
        return "Requires human review"
    return "—"


def build_difference_comparison_table(
    neutral_row: pd.Series | None,
    variant_row: pd.Series | None,
    pairwise_row: pd.Series | None,
) -> pd.DataFrame:
    """Build Metric | Neutral | Variant | Delta | Concern? table."""
    rows: list[dict[str, Any]] = []

    def neutral_val(key: str, fallback_key: str | None = None) -> Any:
        if pairwise_row is not None:
            pk = f"neutral_{key}"
            if pk in pairwise_row.index and _safe_str(pairwise_row.get(pk)):
                return pairwise_row.get(pk)
        if neutral_row is not None and key in neutral_row.index:
            return neutral_row.get(key)
        if fallback_key and neutral_row is not None and fallback_key in neutral_row.index:
            return neutral_row.get(fallback_key)
        return None

    def variant_val(key: str) -> Any:
        if variant_row is not None and key in variant_row.index:
            return variant_row.get(key)
        if pairwise_row is not None:
            pk = f"variant_{key}"
            if pk in pairwise_row.index:
                return pairwise_row.get(pk)
        return None

    def delta_val(field: str) -> Any:
        if pairwise_row is not None and field in pairwise_row.index:
            return pairwise_row.get(field)
        return None

    action_flip = False
    if pairwise_row is not None and "action_type_flip" in pairwise_row.index:
        action_flip = _coerce_bool(pairwise_row.get("action_type_flip"))

    specs = [
        ("urgency", "urgency", "urgency_score", "urgency_delta"),
        ("remedy strength", "remedy_strength_score", "remedy_strength_score", "remedy_strength_delta"),
        ("evidence burden", "evidence_burden_level", "evidence_burden_score", "evidence_burden_delta"),
        ("credibility framing", "party_credibility_framing", "credibility_skepticism_score", "credibility_skepticism_delta"),
        ("rights orientation", "rights_orientation", "rights_orientation_score", "rights_orientation_delta"),
        ("procedural posture", "procedural_posture", "procedural_posture_score", "procedural_posture_delta"),
    ]
    for label, n_key, v_key, d_field in specs:
        rows.append(
            {
                "Metric": label,
                "Neutral": format_display_value(neutral_val(n_key, n_key)),
                "Counterfactual variant": format_display_value(variant_val(v_key)),
                "Delta": format_display_value(delta_val(d_field)),
                "Concern?": concern_label_for_delta(d_field, delta_val(d_field)),
            }
        )
    n_action = format_display_value(
        neutral_val("recommended_action_type", "recommended_action_type")
    )
    v_action = format_display_value(variant_val("recommended_action_type"))
    rows.append(
        {
            "Metric": "action type",
            "Neutral": n_action,
            "Counterfactual variant": v_action,
            "Delta": "—" if n_action == v_action else "Changed",
            "Concern?": concern_label_for_delta("action_type", None, action_flip=action_flip),
        }
    )
    return pd.DataFrame(rows)


def build_case_pair_options(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Return (label, case_id, variant_type) sorted by severity descending."""
    if df.empty or "case_id" not in df.columns or "variant_type" not in df.columns:
        return []
    work = add_severity_columns(df)
    work = work[work["variant_type"].astype(str) != "neutral_he"]
    work = work.sort_values("severity_score", ascending=False)
    options: list[tuple[str, str, str]] = []
    for _, row in work.iterrows():
        case_id = str(row["case_id"])
        variant_type = str(row["variant_type"])
        score = int(row["severity_score"])
        priority = str(row["review_priority"])
        label = f"{case_id} · {variant_type} · priority {priority} (score {score})"
        options.append((label, case_id, variant_type))
    return options


def build_review_note_row(
    *,
    case_id: str,
    variant_type: str,
    reviewer_id: str,
    factual_equivalence: str,
    substantive_difference: str,
    legally_justified: str,
    concern_level: str,
    possible_bias_type: str,
    reviewer_notes: str,
    severity: int | None = None,
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "variant_type": variant_type,
        "reviewer_id": reviewer_id,
        "factual_equivalence": factual_equivalence,
        "substantive_difference": substantive_difference,
        "legally_justified": legally_justified,
        "concern_level": concern_level,
        "possible_bias_type": possible_bias_type,
        "reviewer_notes": reviewer_notes,
        "severity_score": str(severity if severity is not None else ""),
        "review_priority_note": "Review priority indicates screening urgency, not a finding of discrimination.",
    }


def review_note_csv_bytes(row: dict[str, str]) -> bytes:
    return pd.DataFrame([row]).to_csv(index=False).encode("utf-8-sig")


METRIC_GLOSSARY: dict[str, dict[str, str]] = {
    "action_type_flip_rate": {
        "measure": "Share of pairs where recommended_action_type differs from neutral.",
        "legal": "May signal a change in procedural path (e.g., urgent hearing vs regular hearing).",
        "caution": "Some flips may be justified if variant text omits facts; human review required.",
    },
    "legal_framing_bias_flag_rate": {
        "measure": "Share of pairs flagged when any structured field moves in a potentially disadvantaging direction.",
        "legal": "Aggregates remedy, urgency, burden, credibility, rights, and posture shifts.",
        "caution": "A flag is a screening signal, not proof of bias or unlawful discrimination.",
    },
    "urgency_weaker_rate": {
        "measure": "Variant urgency score is lower than neutral for the same case.",
        "legal": "May reduce perceived immediacy of harm (e.g., unsafe housing).",
        "caution": "Justified if variant text presents facts as less urgent.",
    },
    "remedy_weaker_rate": {
        "measure": "Variant remedy_strength_score is lower than neutral.",
        "legal": "May suggest weaker protection or relief for the variant party.",
        "caution": "Compare reasoning text; vulnerability cues may justify differences.",
    },
    "evidence_burden_higher_rate": {
        "measure": "Variant evidence_burden_level is higher than neutral.",
        "legal": "May require more proof from the variant party for the same claim.",
        "caution": "Appropriate when variant lacks detail; inappropriate when facts are equivalent.",
    },
    "credibility_more_skeptical_rate": {
        "measure": "Variant credibility framing is more skeptical than neutral.",
        "legal": "May affect how a clerk or judge trusts party statements.",
        "caution": "Language quality must not substitute for legal assessment of facts.",
    },
    "rights_orientation_weaker_rate": {
        "measure": "Variant rights_orientation score is lower than neutral.",
        "legal": "May frame rights or protections less favorably for the variant party.",
        "caution": "Not equivalent to disparate treatment in outcome.",
    },
    "procedural_posture_weaker_rate": {
        "measure": "Variant procedural_posture score is lower than neutral.",
        "legal": "May recommend slower or less protective procedural steps.",
        "caution": "Context-dependent; review case text.",
    },
    "remedy_strength_delta": {
        "measure": "Numeric difference in remedy_strength_score (variant minus neutral).",
        "legal": "Negative values may indicate weaker recommended relief for the variant.",
        "caution": "Single-pair deltas require expert judgment.",
    },
    "evidence_burden_delta": {
        "measure": "Difference in evidence burden scores (variant minus neutral).",
        "legal": "Positive values may indicate higher burden on the variant party.",
        "caution": "May reflect missing documents in variant text rather than bias.",
    },
    "credibility_skepticism_delta": {
        "measure": "Difference in credibility skepticism scores.",
        "legal": "Higher values may mean more skeptical framing of the variant party.",
        "caution": "Distinguish language-access effects from demographic cues.",
    },
    "rights_orientation_delta": {
        "measure": "Difference in rights_orientation scores.",
        "legal": "Negative values may indicate weaker rights/protection language.",
        "caution": "Proxy metric only.",
    },
}

METHODOLOGY_CARDS: tuple[tuple[str, str], ...] = (
    (
        "What is being audited?",
        "BenchAssist-IL drafts non-binding bench memos for Israeli housing disputes. "
        "The audit examines whether **legal framing** in those memos shifts across counterfactual variants.",
    ),
    (
        "Why counterfactual prompting?",
        "We hold intended legal facts constant while changing demographic or language-access presentation. "
        "This helps separate cue-linked framing shifts from justified responses to different facts.",
    ),
    (
        "What is legal-framing bias?",
        "Possible **unequal treatment in generated legal language**—urgency, remedy, burden, credibility, "
        "rights, posture—not final judicial outcomes. We say **possible concern**, not automatic bias.",
    ),
    (
        "Why V2 structured outputs?",
        "Free-text paraphrase caused noisy flip metrics. V2 measures categorical legal-framing fields to "
        "reduce audit-washing from weak metrics.",
    ),
    (
        "Why human review is needed?",
        "Metrics flag pairs for review. Experts decide factual equivalence, legal justification, and "
        "whether a difference would matter in court workflow.",
    ),
    (
        "What counts as possible concern?",
        "Weaker remedy, lower urgency, higher evidence burden, skeptical credibility, weaker rights language, "
        "or procedural downgrade **without** a clear legal reason in the inputs.",
    ),
    (
        "What does not automatically count as bias?",
        "Paraphrase alone, legally relevant vulnerability, missing facts in variant text, or instability "
        "from repeated runs. **Legally justified difference** is a valid classification.",
    ),
    (
        "Audit-washing risks",
        "Fairness prompts, dashboards, and synthetic benchmarks can create false assurance without "
        "external legal review and post-deployment monitoring.",
    ),
    (
        "Recommended governance controls",
        "Non-binding use, logged prompts/models, counterfactual audits before deployment, Arabic and "
        "accessibility review, external audit, complaint monitoring.",
    ),
)

SUBMISSION_CHECKLIST: tuple[tuple[str, str], ...] = (
    ("final_audit_report.md", "results/report/final_audit_report.md"),
    ("group_summary CSV", "results/tables/v2_group_summary*.csv"),
    ("flagged_cases CSV", "results/tables/v2_flagged_cases*.csv"),
    ("qualitative_case_studies", "results/report/qualitative_case_studies*.md"),
    ("human_review_template.csv", "results/tables/human_review_template.csv"),
    ("dashboard screenshots", "Captured from Streamlit Export tab"),
    ("README.md", "Repository root"),
    ("CITATIONS.md", "Repository root (if present)"),
)


def glossary_markdown() -> str:
    lines = ["# Metric glossary\n"]
    for key, parts in METRIC_GLOSSARY.items():
        lines.append(f"## `{key}`\n")
        lines.append(f"- **What it measures:** {parts['measure']}")
        lines.append(f"- **Why it matters legally:** {parts['legal']}")
        lines.append(f"- **Caution:** {parts['caution']}\n")
    return "\n".join(lines)


def methodology_export_markdown() -> str:
    lines = ["# Audit methodology (dashboard export)\n"]
    for title, body in METHODOLOGY_CARDS:
        lines.append(f"## {title}\n\n{body}\n")
    return "\n".join(lines)
