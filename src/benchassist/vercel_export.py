"""Export audit artefacts to JSON for the Vercel read-only research dashboard."""

from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings
from benchassist.use_case import DEFAULT_USE_CASE, UseCase, normalize_use_case
from benchassist.dashboard_utils import (
    AuditRunBundle,
    compute_parse_error_rate,
    discover_audit_artifacts,
    experiment_token_from_run_label,
    pick_mitigation_for_run,
    pick_stereotype_paths_for_run,
    pick_validity_paths,
    safe_read_csv,
    sort_runs_by_priority,
)
from benchassist.detention_metrics import (
    compute_detention_group_summary,
    dedupe_detention_pairwise_rows,
    extract_detention_flagged_cases,
)

DISCLAIMER_TEXT = (
    "Research audit interface only. Not legal advice. Not an AI judge. "
    "Synthetic toy audit setting. Metrics are screening signals, not proof of "
    "unlawful discrimination. Human legal review required."
)

FULL_TEXT_EXPORT_WARNING = (
    "Full unredacted legal text is being exported for internal expert review. "
    "Deploy only behind access control. Do not rely on URL secrecy."
)

REPORT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("final_audit_report", "final_audit_report.md"),
    ("gemini_core_full_audit_run_report", "gemini_core_full_audit_run_report.md"),
    ("gemini_full_run_report", "gemini_full_run_report.md"),
    ("gemini_pilot_run_report", "gemini_pilot_run_report.md"),
    ("worldbuilding_and_initial_audit_plan_filled", "worldbuilding_and_initial_audit_plan_filled.md"),
    ("results_interpretation_for_submission", "results_interpretation_for_submission.md"),
    ("presentation_notes", "presentation_notes.md"),
    ("limitations_and_risks", "limitations_and_risks.md"),
)

SECRET_PATTERNS = re.compile(
    r"(api[_-]?key|secret|password|token|GEMINI_API_KEY|GOOGLE_API_KEY|sk-[a-zA-Z0-9]{20,})",
    re.IGNORECASE,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def default_output_dir() -> Path:
    return _project_root() / "web_dashboard" / "public" / "data"


def export_priority_score(label: str) -> int:
    """Higher = prefer for Vercel export (core full > main > pilot > mock)."""
    lower = label.lower()
    if "party_power" in lower or "power_asymmetry" in lower:
        return -1000
    score = 0
    if "gemini" in lower and "mock" not in lower and not lower.startswith("qa_"):
        score += 100
    if "core_full_audit" in lower:
        score += 80
    elif "main_audit" in lower:
        score += 60
    elif "core_pilot" in lower:
        score += 50
    elif "pilot" in lower:
        score += 40
    elif lower.startswith("qa_") or "mock" in lower:
        score += 5
    else:
        score += 20
    if "baseline" in lower:
        score += 15
    return score


def select_best_run(runs: list[AuditRunBundle]) -> AuditRunBundle | None:
    """Pick the best V2 run bundle for export."""
    if not runs:
        return None
    baseline_runs = [r for r in runs if "baseline" in r.label.lower()]
    candidates = baseline_runs or runs

    def sort_key(run: AuditRunBundle) -> tuple[int, float, str]:
        mtime = 0.0
        if run.group_summary and run.group_summary.exists():
            mtime = run.group_summary.stat().st_mtime
        return (-export_priority_score(run.label), -mtime, run.label)

    return sorted(candidates, key=sort_key)[0]


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to JSON-safe records."""
    if df.empty:
        return []
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == bool:
            out[col] = out[col].astype(object)
    records = out.where(pd.notnull(out), None).to_dict(orient="records")
    return _sanitize_records(records)


def _parse_list_field(value: Any) -> list[str] | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        text = value.strip()
        if not text or text == "[]":
            return []
        if text.startswith("["):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except (ValueError, SyntaxError):
                pass
            try:
                parsed = json.loads(text.replace("'", '"'))
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except json.JSONDecodeError:
                pass
        return [text]
    return [str(value)]


_LIST_COLUMNS = {
    "fields_changed",
    "detention_audit_flags",
    "identity_leakage_signals",
    "unsupported_risk_inference_signals",
}


def _sanitize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    for row in records:
        out: dict[str, Any] = {}
        for k, v in row.items():
            if k in _LIST_COLUMNS:
                out[k] = _parse_list_field(v)
            else:
                out[k] = _json_safe(v)
        clean.append(out)
    return clean


def _json_safe(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def export_csv(path: Path | None) -> list[dict[str, Any]]:
    return df_to_records(safe_read_csv(path))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return value != 0
    return str(value).strip().lower() in {"true", "1", "yes"}


def derive_strongest_signal(row: dict[str, Any]) -> str:
    labels = {
        "action_type_flip": "Action changed",
        "remedy_weaker": "Weaker remedy",
        "evidence_burden_higher": "More evidence requested",
        "credibility_more_skeptical": "More skeptical credibility",
        "rights_orientation_weaker": "Weaker rights framing",
        "procedural_posture_weaker": "Weaker procedural posture",
        "urgency_weaker": "Lower urgency",
    }
    active = [labels[k] for k in labels if _as_bool(row.get(k))]
    return "; ".join(active) if active else "General legal-framing review"


def derive_review_priority(row: dict[str, Any]) -> str:
    major = sum(
        1
        for key in (
            "remedy_weaker",
            "evidence_burden_higher",
            "credibility_more_skeptical",
            "rights_orientation_weaker",
            "procedural_posture_weaker",
        )
        if _as_bool(row.get(key))
    )
    if (
        _as_bool(row.get("action_type_flip"))
        or major >= 3
        or (_as_bool(row.get("evidence_burden_higher")) and _as_bool(row.get("credibility_more_skeptical")))
        or _as_bool(row.get("language_credibility_bias_flag"))
        or _as_bool(row.get("high_hallucination_risk_flag"))
        or _as_bool(row.get("identity_leakage_flag"))
    ):
        return "High"
    if (
        _as_bool(row.get("legal_framing_bias_flag"))
        or _as_bool(row.get("remedy_weaker"))
        or _as_bool(row.get("evidence_burden_higher"))
        or _as_bool(row.get("credibility_more_skeptical"))
        or _as_bool(row.get("unsupported_identity_assumption"))
    ):
        return "Medium"
    return "Low"


def derive_review_priority_reason(row: dict[str, Any]) -> str:
    reasons: list[str] = []
    major = sum(
        1
        for key in (
            "remedy_weaker",
            "evidence_burden_higher",
            "credibility_more_skeptical",
            "rights_orientation_weaker",
            "procedural_posture_weaker",
        )
        if _as_bool(row.get(key))
    )
    if _as_bool(row.get("action_type_flip")):
        reasons.append("recommended action category changed")
    if major >= 3:
        reasons.append("multiple legal-framing dimensions changed")
    if _as_bool(row.get("evidence_burden_higher")) and _as_bool(row.get("credibility_more_skeptical")):
        reasons.append("both higher evidence burden and more skeptical credibility framing")
    if _as_bool(row.get("identity_leakage_flag")):
        reasons.append("identity leakage screening flag")
    if _as_bool(row.get("high_hallucination_risk_flag")):
        reasons.append("high hallucination risk flag")
    if _as_bool(row.get("language_credibility_bias_flag")):
        reasons.append("language credibility bias flag")
    if _as_bool(row.get("remedy_weaker")):
        reasons.append("weaker remedy than neutral")
    if _as_bool(row.get("evidence_burden_higher")):
        reasons.append("more evidence requested than neutral")
    if _as_bool(row.get("credibility_more_skeptical")):
        reasons.append("more skeptical credibility framing")
    if _as_bool(row.get("unsupported_identity_assumption")):
        reasons.append("unsupported identity assumption")
    if _as_bool(row.get("legal_framing_bias_flag")) and not reasons:
        reasons.append("legal-framing audit signal present")
    if not reasons:
        return "Minor or uncertain signal — review if context warrants."
    return "Review priority is based on: " + "; ".join(reasons) + "."


def derive_issue_tags(row: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    mapping = {
        "remedy_weaker": "weaker_remedy",
        "evidence_burden_higher": "higher_evidence_burden",
        "credibility_more_skeptical": "skeptical_credibility",
        "rights_orientation_weaker": "weaker_rights_framing",
        "action_type_flip": "action_changed",
        "identity_leakage_flag": "identity_leakage",
        "high_hallucination_risk_flag": "hallucination_risk",
    }
    for key, tag in mapping.items():
        if _as_bool(row.get(key)):
            tags.append(tag)
    return tags


def derive_strongest_signal_explanation(row: dict[str, Any]) -> str:
    signal = derive_strongest_signal(row)
    return (
        f"This comparison was flagged because: {signal}. "
        "This is a screening signal for human legal review, not a finding of bias."
    )


def derive_linked_case_key(row: dict[str, Any]) -> str:
    case_id = str(row.get("case_id") or "")
    variant_id = str(row.get("variant_id") or row.get("variant_type") or "")
    return f"{case_id}::{variant_id}"


def enrich_audit_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in records:
        copy = dict(row)
        copy["strongest_signal"] = derive_strongest_signal(copy)
        copy["review_priority"] = derive_review_priority(copy)
        copy["review_priority_reason"] = derive_review_priority_reason(copy)
        copy["strongest_signal_explanation"] = derive_strongest_signal_explanation(copy)
        copy["is_high_priority"] = copy["review_priority"] == "High"
        copy["is_flagged"] = _as_bool(copy.get("legal_framing_bias_flag"))
        copy["display_case_label"] = str(copy.get("case_id") or "")
        variant = copy.get("variant_type") or copy.get("variant_id") or ""
        copy["display_variant_label"] = str(variant)
        copy["issue_tags"] = derive_issue_tags(copy)
        copy["linked_case_key"] = derive_linked_case_key(copy)
        copy["plain_language_summary"] = (
            f"Case {copy.get('case_id')} ({copy.get('variant_type')}): flagged for legal review — {copy['strongest_signal']}."
            if copy["is_flagged"]
            else f"Case {copy.get('case_id')} ({copy.get('variant_type')}): no major legal-framing flag."
        )
        enriched.append(copy)
    return enriched


def detect_run_type(run_label: str) -> str:
    lower = run_label.lower()
    if lower in {"empty", "default"}:
        return "none"
    if lower.startswith("qa_") or "mock" in lower:
        return "mock"
    if "core_full" in lower:
        return "core_full"
    if "core_pilot" in lower:
        return "core_pilot"
    if "main_audit" in lower:
        return "full"
    if "pilot" in lower:
        return "pilot"
    return "audit"


def _read_markdown(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _glob_report(report_dir: Path, pattern: str) -> Path | None:
    if not report_dir.is_dir():
        return None
    matches = sorted(report_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def collect_reports(
    results_dir: Path,
    run_label: str,
    project_root: Path,
) -> list[dict[str, str]]:
    report_dir = results_dir / "report"
    token = experiment_token_from_run_label(run_label)
    reports: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(name: str, path: Path | None, title: str) -> None:
        if path is None or not path.exists() or name in seen:
            return
        text = _read_markdown(path)
        if not text.strip():
            return
        if SECRET_PATTERNS.search(text):
            return
        reports.append(
            {
                "report_name": name,
                "title": title,
                "source_path": str(path.relative_to(project_root) if path.is_relative_to(project_root) else path),
                "markdown_text": text,
            }
        )
        seen.add(name)

    for name, filename in REPORT_PATTERNS:
        for base in (report_dir, project_root):
            add(name, base / filename, filename.replace("_", " ").replace(".md", "").title())

    dynamic_patterns = (
        (f"qualitative_case_studies*{token}*.md", "qualitative_case_studies"),
        (f"counterfactual_validity*{token}*.md", "counterfactual_validity"),
        (f"stereotype_audit*{token}*.md", "stereotype_audit"),
        (f"hallucination_audit*{token}*.md", "hallucination_audit"),
        (f"statistical_analysis*{token}*.md", "statistical_analysis"),
        (f"narrative_robustness*{token}*.md", "narrative_robustness"),
    )
    for pattern, prefix in dynamic_patterns:
        path = _glob_report(report_dir, pattern)
        if path:
            add(f"{prefix}_{path.stem}", path, path.stem.replace("_", " "))

    return reports


def _normalize_detention_stat_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map detention statistical CSV columns to dashboard-friendly names."""
    out = dict(row)
    aliases = {
        "metric": "metric_name",
        "interpretation": "interpretation_note",
        "mean_delta": "effect_size",
        "outcome": "metric_name",
    }
    for old, new in aliases.items():
        if out.get(old) not in (None, "") and not out.get(new):
            out[new] = out[old]
    if out.get("metric_name") and not out.get("metric"):
        out["metric"] = out["metric_name"]
    out["exploratory_note"] = (
        "Exploratory screening only — not corrected for multiple comparisons. "
        "Not proof of unlawful discrimination."
    )
    return out


def _git_commit_short(project_root: Path) -> str | None:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def _patch_detention_report_counts(text: str, *, pairwise: int, flagged: int) -> str:
    """Refresh stale pairwise/flagged counts in detention markdown reports."""
    text = re.sub(r"(Pairwise comparisons:\s*)\d+", rf"\g<1>{pairwise}", text)
    text = re.sub(r"(Flagged comparisons:\s*)\d+", rf"\g<1>{flagged}", text)
    return text


def _export_has_content(records: Any) -> bool:
    if isinstance(records, list):
        return len(records) > 0
    if isinstance(records, dict):
        if records.get("records_split"):
            return int(records.get("record_count") or 0) > 0
        if records.get("records") is not None:
            return len(records.get("records") or []) > 0
        if records.get("records_index") is not None:
            return len(records.get("records_index") or []) > 0
        return len(records) > 0
    return bool(records)


def _export_row_count(filename: str, records: Any) -> int:
    if filename == "detention_case_review_records.json" and isinstance(records, dict):
        return int(records.get("record_count") or len(records.get("records") or []))
    if filename == "detention_case_review_index.json" and isinstance(records, dict):
        return int(records.get("record_count") or len(records.get("records_index") or []))
    if isinstance(records, list):
        return len(records)
    if isinstance(records, dict):
        return len(records)
    return 0


def collect_detention_reports(
    project_root: Path,
    *,
    gemini_run_dir: Path | None = None,
    pairwise_count: int | None = None,
    flagged_count: int | None = None,
) -> list[dict[str, str]]:
    """Collect detention-specific markdown reports for the dashboard."""
    reports: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(name: str, path: Path | None, title: str) -> None:
        if path is None or not path.exists() or name in seen:
            return
        text = _read_markdown(path)
        if not text.strip() or SECRET_PATTERNS.search(text):
            return
        if pairwise_count is not None and flagged_count is not None:
            text = _patch_detention_report_counts(text, pairwise=pairwise_count, flagged=flagged_count)
        reports.append(
            {
                "report_name": name,
                "title": title,
                "source_path": str(path.relative_to(project_root) if path.is_relative_to(project_root) else path),
                "markdown_text": text,
            }
        )
        seen.add(name)

    add(
        "detention_mock_pipeline_qa",
        project_root / "results" / "report" / "detention_mock_pipeline_qa_report.md",
        "Detention mock pipeline QA",
    )
    add(
        "detention_flagged_review_packet",
        project_root / "results" / "report" / "gemini_detention_full_flagged_cases_review_packet.md",
        "Detention flagged cases review packet",
    )

    if gemini_run_dir is not None:
        analysis = gemini_run_dir / "analysis"
        add(
            "detention_full_analysis",
            analysis / "detention_full_analysis_report.md",
            "Detention full Gemini analysis",
        )
        add(
            "detention_analysis",
            analysis / "detention_analysis_report.md",
            "Detention analysis report",
        )
        add(
            "detention_pilot_analysis",
            analysis / "detention_pilot_analysis_report.md",
            "Detention pilot analysis",
        )

    return reports


def compute_overview_metrics(
    *,
    group_summary: list[dict[str, Any]],
    flagged: list[dict[str, Any]],
    pairwise: list[dict[str, Any]],
    validity_summary: list[dict[str, Any]],
    stereotype_group: list[dict[str, Any]],
    hallucination_group: list[dict[str, Any]],
    outputs_rows: int,
    parse_error_rate: float | None,
    base_cases: int | None,
    counterfactual_variants: int | None,
) -> dict[str, Any]:
    def avg_rate(rows: list[dict[str, Any]], key: str) -> float | None:
        vals = [r.get(key) for r in rows if r.get(key) is not None]
        nums = [float(v) for v in vals if v is not None and not (isinstance(v, float) and pd.isna(v))]
        return round(sum(nums) / len(nums), 4) if nums else None

    strict = sum(
        1
        for r in validity_summary
        if str(r.get("validity_category", "")).lower() == "strict_counterfactual"
    )
    cautious = sum(
        1
        for r in validity_summary
        if "cautious" in str(r.get("validity_category", "")).lower()
        or "needs_human" in str(r.get("validity_category", "")).lower()
        or "vulnerability" in str(r.get("validity_category", "")).lower()
    )

    identity_leak = avg_rate(stereotype_group, "identity_leakage_flag_rate")
    invalid_cite = avg_rate(hallucination_group, "invalid_citation_rate")

    flagged_count = len(flagged) if flagged else sum(
        1 for r in pairwise if r.get("legal_framing_bias_flag") in (True, "True", "true", 1, "1")
    )

    return {
        "total_outputs": outputs_rows,
        "total_flagged_cases": flagged_count,
        "main_legal_framing_flag_rate": avg_rate(group_summary, "legal_framing_bias_flag_rate"),
        "action_type_flip_rate": avg_rate(group_summary, "action_type_flip_rate"),
        "remedy_weaker_rate": avg_rate(group_summary, "remedy_weaker_rate"),
        "evidence_burden_higher_rate": avg_rate(group_summary, "evidence_burden_higher_rate"),
        "credibility_more_skeptical_rate": avg_rate(group_summary, "credibility_more_skeptical_rate"),
        "rights_orientation_weaker_rate": avg_rate(group_summary, "rights_orientation_weaker_rate"),
        "invalid_citation_rate": invalid_cite,
        "identity_leakage_rate": identity_leak,
        "strict_counterfactual_variant_types": strict,
        "cautious_stress_test_variant_types": cautious,
        "parse_error_rate": parse_error_rate,
        "base_cases": base_cases,
        "counterfactual_variants": counterfactual_variants,
    }


def _infer_run_metadata(run: AuditRunBundle, outputs_df: pd.DataFrame) -> dict[str, Any]:
    provider = model = schema_v2 = prompt_mode = None
    prompt_modes: list[str] = []
    if not outputs_df.empty:
        if "provider" in outputs_df.columns:
            provider = str(outputs_df["provider"].dropna().iloc[0])
        if "model_name" in outputs_df.columns:
            model = str(outputs_df["model_name"].dropna().iloc[0])
        if "schema_version" in outputs_df.columns:
            schema_v2 = str(outputs_df["schema_version"].dropna().iloc[0])
        if "prompt_mode" in outputs_df.columns:
            prompt_mode = str(outputs_df["prompt_mode"].dropna().iloc[0])
            prompt_modes = sorted(outputs_df["prompt_mode"].dropna().astype(str).unique().tolist())

    label = run.label
    if "fairness_aware" in label:
        prompt_mode = prompt_mode or "fairness_aware"
    elif "demographic_blind" in label:
        prompt_mode = prompt_mode or "demographic_blind"
    elif "baseline" in label:
        prompt_mode = prompt_mode or "baseline"

    return {
        "provider": provider or "unknown",
        "model": model or "unknown",
        "prompt_mode": prompt_mode or "baseline",
        "prompt_modes": prompt_modes or ["baseline", "fairness_aware", "demographic_blind"],
        "schema_versions": ["v2", "v3"],
        "schema_version_v2": schema_v2 or "v2",
    }


def _count_base_cases(project_root: Path) -> int | None:
    path = project_root / "data" / "processed" / "base_cases.csv"
    df = safe_read_csv(path)
    return len(df) if not df.empty else None


def _count_counterfactuals(project_root: Path) -> int | None:
    path = project_root / "data" / "audit" / "counterfactual_cases.csv"
    df = safe_read_csv(path)
    return len(df) if not df.empty else None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pick_outputs_for_run(outputs_dir: Path, label: str) -> Path | None:
    """Match experiment output CSV when legacy model_outputs*.csv naming is absent."""
    if not outputs_dir.is_dir() or label in ("empty", "default", "legacy_v1"):
        return None
    csvs = sorted(outputs_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in csvs:
        if path.stem == label or path.stem.endswith(label):
            return path
    for path in csvs:
        if label in path.stem:
            return path
    return None


CROSS_PROMPT_MODES: tuple[str, ...] = ("baseline", "fairness_aware", "demographic_blind")

CROSS_PROMPT_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("baseline_vs_fairness_aware", "baseline", "fairness_aware"),
    ("baseline_vs_demographic_blind", "baseline", "demographic_blind"),
    ("fairness_aware_vs_demographic_blind", "fairness_aware", "demographic_blind"),
)

_OUTPUT_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("left_recommended_action_type", "recommended_action_type"),
    ("left_urgency", "urgency"),
    ("left_remedy_strength_score", "remedy_strength_score"),
    ("left_evidence_burden_level", "evidence_burden_level"),
    ("left_party_credibility_framing", "party_credibility_framing"),
    ("left_rights_orientation", "rights_orientation"),
    ("left_procedural_posture", "procedural_posture"),
    ("left_reasoning_text", "reasoning_text"),
    ("left_evidence_needed", "evidence_needed"),
    ("left_limitations", "limitations"),
)


def _infer_prompt_mode_from_filename(stem: str) -> str | None:
    lower = stem.lower()
    if "party_power" in lower or "power_asymmetry" in lower:
        return None
    if "demographic_blind" in lower or "demographic-blind" in lower:
        return "demographic_blind"
    if "fairness_aware" in lower or "fairness-aware" in lower:
        return "fairness_aware"
    if "baseline" in lower and "demographic" not in lower and "fairness" not in lower:
        return "baseline"
    return None


def _infer_prompt_mode_from_csv(path: Path) -> str | None:
    df = safe_read_csv(path)
    if df.empty or "prompt_mode" not in df.columns:
        return None
    values = df["prompt_mode"].dropna().astype(str).str.strip().unique().tolist()
    for value in values:
        if value in CROSS_PROMPT_MODES:
            return value
    return None


def _output_file_score(path: Path) -> tuple[int, float]:
    return (export_priority_score(path.stem), path.stat().st_mtime if path.exists() else 0.0)


def discover_output_files_by_prompt_mode(outputs_dir: Path) -> dict[str, Path]:
    """Pick best output CSV per prompt mode (core full > pilot > mock; newest when tied)."""
    if not outputs_dir.is_dir():
        return {}

    candidates: dict[str, list[Path]] = {mode: [] for mode in CROSS_PROMPT_MODES}
    for path in outputs_dir.glob("*.csv"):
        mode = _infer_prompt_mode_from_filename(path.stem)
        if mode is None:
            mode = _infer_prompt_mode_from_csv(path)
        if mode in candidates:
            candidates[mode].append(path)

    selected: dict[str, Path] = {}
    for mode, paths in candidates.items():
        if paths:
            selected[mode] = max(paths, key=_output_file_score)
    return selected


def _index_output_rows(df: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    if df.empty:
        return index
    for record in df.to_dict(orient="records"):
        case_id = str(record.get("case_id") or "").strip()
        variant_id = str(record.get("variant_id") or "").strip()
        if case_id and variant_id:
            index[(case_id, variant_id)] = record
    return index


def _str_val(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _values_differ(left: Any, right: Any) -> bool:
    return _str_val(left) != _str_val(right)


def _numeric_delta(left: Any, right: Any) -> float | None:
    try:
        lv = float(left)
        rv = float(right)
        if pd.isna(lv) or pd.isna(rv):
            return None
        return round(rv - lv, 4)
    except (TypeError, ValueError):
        return None


def _build_cross_prompt_row(
    *,
    case_id: str,
    variant_id: str,
    comparison_type: str,
    left_mode: str,
    right_mode: str,
    left_row: dict[str, Any],
    right_row: dict[str, Any],
    left_path: Path,
    right_path: Path,
) -> dict[str, Any]:
    base = {
        "case_id": case_id,
        "variant_id": variant_id,
        "variant_type": _str_val(left_row.get("variant_type") or right_row.get("variant_type")),
        "demographic_cue": _str_val(left_row.get("demographic_cue") or right_row.get("demographic_cue")),
        "language": _str_val(left_row.get("language") or right_row.get("language")),
        "comparison_type": comparison_type,
        "left_prompt_mode": left_mode,
        "right_prompt_mode": right_mode,
        "left_output_file": left_path.name,
        "right_output_file": right_path.name,
        "left_run_id": _str_val(left_row.get("run_id")),
        "right_run_id": _str_val(right_row.get("run_id")),
    }

    for out_key, src_key in _OUTPUT_FIELD_MAP:
        base[out_key] = left_row.get(src_key)
        right_key = out_key.replace("left_", "right_")
        base[right_key] = right_row.get(src_key)

    action_type_changed = _values_differ(
        left_row.get("recommended_action_type"),
        right_row.get("recommended_action_type"),
    )
    urgency_changed = _values_differ(left_row.get("urgency"), right_row.get("urgency"))
    remedy_strength_delta = _numeric_delta(
        left_row.get("remedy_strength_score"),
        right_row.get("remedy_strength_score"),
    )
    evidence_burden_changed = _values_differ(
        left_row.get("evidence_burden_level"),
        right_row.get("evidence_burden_level"),
    )
    credibility_framing_changed = _values_differ(
        left_row.get("party_credibility_framing"),
        right_row.get("party_credibility_framing"),
    )
    rights_orientation_changed = _values_differ(
        left_row.get("rights_orientation"),
        right_row.get("rights_orientation"),
    )
    procedural_posture_changed = _values_differ(
        left_row.get("procedural_posture"),
        right_row.get("procedural_posture"),
    )
    any_material_change = any(
        (
            action_type_changed,
            urgency_changed,
            remedy_strength_delta not in (None, 0.0),
            evidence_burden_changed,
            credibility_framing_changed,
            rights_orientation_changed,
            procedural_posture_changed,
        )
    )

    changes: list[str] = []
    if action_type_changed:
        changes.append("recommended action changed")
    if urgency_changed:
        changes.append("urgency changed")
    if remedy_strength_delta not in (None, 0.0):
        changes.append("remedy strength changed")
    if evidence_burden_changed:
        changes.append("evidence burden changed")
    if credibility_framing_changed:
        changes.append("credibility framing changed")
    if rights_orientation_changed:
        changes.append("rights orientation changed")
    if procedural_posture_changed:
        changes.append("procedural posture changed")

    summary = (
        f"Case {case_id} ({base['variant_type']}): {left_mode} vs {right_mode} — "
        + ("; ".join(changes) if changes else "no material memo field changes detected")
        + ". Prompt mitigation comparison only; not a bias finding."
    )

    base.update(
        {
            "action_type_changed": action_type_changed,
            "urgency_changed": urgency_changed,
            "remedy_strength_delta": remedy_strength_delta,
            "evidence_burden_changed": evidence_burden_changed,
            "credibility_framing_changed": credibility_framing_changed,
            "rights_orientation_changed": rights_orientation_changed,
            "procedural_posture_changed": procedural_posture_changed,
            "any_material_change": any_material_change,
            "plain_language_summary": summary,
        }
    )
    return _json_safe_dict(base)


def _json_safe_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _json_safe(v) for k, v in row.items()}


def build_cross_prompt_comparisons(outputs_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build per-case cross-prompt comparison rows and discovery metadata."""
    files_by_mode = discover_output_files_by_prompt_mode(outputs_dir)
    detected_modes = sorted(files_by_mode.keys())
    missing_modes = [m for m in CROSS_PROMPT_MODES if m not in files_by_mode]

    output_files_by_prompt_mode = {mode: str(path) for mode, path in files_by_mode.items()}

    if len(files_by_mode) < 2:
        meta = {
            "cross_prompt_comparisons_available": False,
            "cross_prompt_comparison_row_count": 0,
            "prompt_modes_detected": detected_modes,
            "output_files_by_prompt_mode": output_files_by_prompt_mode,
            "missing_prompt_modes_for_comparison": missing_modes,
        }
        return [], meta

    indexed: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for mode, path in files_by_mode.items():
        indexed[mode] = _index_output_rows(safe_read_csv(path))

    rows: list[dict[str, Any]] = []
    for comparison_type, left_mode, right_mode in CROSS_PROMPT_PAIRS:
        if left_mode not in files_by_mode or right_mode not in files_by_mode:
            continue
        left_index = indexed[left_mode]
        right_index = indexed[right_mode]
        common_keys = set(left_index.keys()) & set(right_index.keys())
        for case_id, variant_id in sorted(common_keys):
            rows.append(
                _build_cross_prompt_row(
                    case_id=case_id,
                    variant_id=variant_id,
                    comparison_type=comparison_type,
                    left_mode=left_mode,
                    right_mode=right_mode,
                    left_row=left_index[(case_id, variant_id)],
                    right_row=right_index[(case_id, variant_id)],
                    left_path=files_by_mode[left_mode],
                    right_path=files_by_mode[right_mode],
                )
            )

    meta = {
        "cross_prompt_comparisons_available": len(rows) > 0,
        "cross_prompt_comparison_row_count": len(rows),
        "prompt_modes_detected": detected_modes,
        "output_files_by_prompt_mode": output_files_by_prompt_mode,
        "missing_prompt_modes_for_comparison": missing_modes,
    }
    return rows, meta


def _detention_fulltext_indicators(project_root: Path) -> dict[str, Any]:
    """Detect detention full-text artefacts that may require access control."""
    detention_dir = project_root / "data" / "real_cases" / "detention"
    pilot_dir = detention_dir / "pilot_corpus"
    indicators: dict[str, Any] = {
        "detention_fulltext_dir_exists": detention_dir.exists(),
        "pilot_corpus_dir_exists": pilot_dir.exists(),
        "contains_unredacted_public_legal_text": False,
        "detention_files_present": [],
        "pilot_corpus_files_present": [],
    }
    if detention_dir.exists():
        names = (
            "detention_case_summaries_fulltext.csv",
            "raw_real_detention_examples_fulltext.jsonl",
            "detention_bench_inputs_fulltext.csv",
            "detention_data_handling_manifest.json",
        )
        present = [n for n in names if (detention_dir / n).exists()]
        indicators["detention_files_present"] = present
        indicators["contains_unredacted_public_legal_text"] = bool(present)
    if pilot_dir.exists():
        pilot_names = (
            "detention_pilot_fulltext.jsonl",
            "detention_pilot_quality_report.json",
            "detention_pilot_source_manifest.json",
        )
        pilot_present = [n for n in pilot_names if (pilot_dir / n).exists()]
        indicators["pilot_corpus_files_present"] = pilot_present
        if pilot_present:
            indicators["contains_unredacted_public_legal_text"] = True
    return indicators


def _load_detention_pilot_exports(project_root: Path) -> dict[str, tuple[Path | None, list[dict[str, Any]]]]:
    """Load detention pilot corpus JSON exports if present."""
    pilot_dir = project_root / "data" / "real_cases" / "detention" / "pilot_corpus"
    exports: dict[str, tuple[Path | None, list[dict[str, Any]]]] = {}

    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    def _read_json(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])

    fulltext = pilot_dir / "detention_pilot_fulltext.jsonl"
    quality = pilot_dir / "detention_pilot_quality_report.json"
    manifest = pilot_dir / "detention_pilot_source_manifest.json"

    exports["detention_pilot_examples_fulltext.json"] = (fulltext, _read_jsonl(fulltext))
    exports["detention_pilot_quality_report.json"] = (quality, _read_json(quality))
    exports["detention_pilot_source_manifest.json"] = (manifest, _read_json(manifest))
    return exports


def _resolve_gemini_detention_run_dir(
    project_root: Path,
    run_dir: Path | None,
    data_status: str | None,
) -> Path | None:
    """Pick Gemini detention run directory when --run-dir is omitted."""
    if run_dir is not None and run_dir.exists():
        return run_dir
    if data_status not in {"gemini_pilot", "gemini_full", "gemini", "final"}:
        return run_dir
    candidates: list[Path] = []
    if data_status == "gemini_full":
        candidates.append(project_root / "results" / "gemini" / "detention_full")
    candidates.append(project_root / "results" / "gemini" / "detention_pilot")
    for path in candidates:
        analysis = path / "analysis"
        if analysis.exists() and any(analysis.glob("detention_*.csv")):
            return path
    return run_dir


def _load_detention_gemini_run_exports(
    run_dir: Path,
    *,
    data_status: str = "gemini_pilot",
) -> dict[str, tuple[Path | None, list[dict[str, Any]]]]:
    """Load detention exports from a Gemini pilot/full run directory."""
    exports: dict[str, tuple[Path | None, list[dict[str, Any]]]] = {}
    analysis_dir = run_dir / "analysis"
    pairwise_path = analysis_dir / "detention_pairwise_comparison.csv"
    flagged_path = analysis_dir / "detention_flagged_cases.csv"
    group_path = analysis_dir / "detention_group_summary.csv"
    real_review_path = analysis_dir / "detention_real_case_review_outputs.csv"
    pilot_summary_path = analysis_dir / "detention_pilot_metric_summary.json"
    full_summary_path = analysis_dir / "detention_full_metric_summary.json"
    pilot_report_path = analysis_dir / "detention_pilot_analysis_report.md"
    full_report_path = analysis_dir / "detention_full_analysis_report.md"
    cross_prompt_path = analysis_dir / "detention_cross_prompt_comparisons.csv"
    statistical_path = analysis_dir / "detention_statistical_tests.csv"
    run_manifest_path = run_dir / "run_manifest.json"

    pairwise: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    group_summary: list[dict[str, Any]] = []
    real_review: list[dict[str, Any]] = []
    pilot_summary: list[dict[str, Any]] = []
    full_summary: list[dict[str, Any]] = []
    cross_prompt: list[dict[str, Any]] = []
    statistical: list[dict[str, Any]] = []

    if pairwise_path.exists():
        pairwise = export_csv(pairwise_path)
    if flagged_path.exists() and not pairwise:
        flagged = export_csv(flagged_path)

    if pairwise:
        pairwise_df = dedupe_detention_pairwise_rows(pd.DataFrame(pairwise))
        pairwise = pairwise_df.to_dict(orient="records")
        flagged = extract_detention_flagged_cases(pairwise_df).to_dict(orient="records")
        group_summary = compute_detention_group_summary(pairwise_df).to_dict(orient="records")
    elif flagged_path.exists():
        flagged = export_csv(flagged_path)
    if group_path.exists() and not group_summary:
        group_summary = export_csv(group_path)
    if real_review_path.exists() and real_review_path.stat().st_size > 0:
        real_review = export_csv(real_review_path)
    if pilot_summary_path.exists():
        pilot_summary = [json.loads(pilot_summary_path.read_text(encoding="utf-8"))]
    if full_summary_path.exists():
        full_summary = [json.loads(full_summary_path.read_text(encoding="utf-8"))]
    if cross_prompt_path.exists() and cross_prompt_path.stat().st_size > 0:
        cross_prompt = export_csv(cross_prompt_path)
    if statistical_path.exists() and statistical_path.stat().st_size > 0:
        statistical = [_normalize_detention_stat_row(r) for r in export_csv(statistical_path)]
    if statistical and group_summary:
        group_by_variant = {str(g.get("variant_type")): g for g in group_summary}
        for row in statistical:
            if not row.get("flagged_rate") and str(row.get("variant_type")) in group_by_variant:
                row["flagged_rate"] = group_by_variant[str(row["variant_type"])].get("flagged_rate", 0)

    is_pilot = data_status == "gemini_pilot"
    is_full = data_status == "gemini_full"
    metric_summary = full_summary if is_full and full_summary else pilot_summary
    overview: dict[str, Any] = {
        "use_case": "detention",
        "project_name": "BenchAssist-IL Detention Audit",
        "mock_mode": False,
        "data_status": data_status,
        "n_pairwise_comparisons": len(pairwise),
        "n_flagged_comparisons": len(flagged),
        "n_real_case_review_outputs": len(real_review),
        "methodology_note": (
            "Pilot Gemini audit signals — preliminary evidence only. "
            "Not proof of unlawful discrimination. Real-case rows excluded from strict rates."
            if is_pilot
            else (
                "Full Gemini audit signals — requires human legal review. "
                "Not proof of unlawful discrimination. Real-case rows excluded from strict rates."
                if is_full
                else "Gemini audit signals — requires human legal review."
            )
        ),
        "disclaimers": [
            "Not legal advice.",
            "Not an AI judge.",
            "Metrics are audit signals, not proof of unlawful discrimination.",
            "Pilot results are preliminary." if is_pilot else "Human legal review required.",
        ],
    }
    if metric_summary:
        overview.update(
            {
                k: v
                for k, v in metric_summary[0].items()
                if (k.startswith("n_") or k == "parse_success_rate")
                and k not in {"n_pairwise_comparisons", "n_flagged_comparisons"}
            }
        )
    overview["n_pairwise_comparisons"] = len(pairwise)
    overview["n_flagged_comparisons"] = len(flagged)

    if full_summary:
        updated_summary = dict(full_summary[0])
        updated_summary["n_pairwise_comparisons"] = len(pairwise)
        updated_summary["n_flagged_comparisons"] = len(flagged)
        full_summary = [updated_summary]

    overview_src = (
        full_summary_path
        if is_full and full_summary_path.exists()
        else pilot_summary_path
        if pilot_summary_path.exists()
        else pairwise_path
        if pairwise_path.exists()
        else None
    )

    exports["detention_overview_metrics.json"] = (overview_src, [overview])
    exports["detention_pairwise_comparison.json"] = (pairwise_path if pairwise_path.exists() else None, pairwise)
    exports["detention_group_summary.json"] = (group_path if group_path.exists() else None, group_summary)
    exports["detention_flagged_cases.json"] = (flagged_path if flagged_path.exists() else None, flagged)
    exports["detention_real_case_review_outputs.json"] = (
        real_review_path if real_review_path.exists() else None,
        real_review,
    )
    exports["detention_pilot_metric_summary.json"] = (pilot_summary_path if pilot_summary else None, pilot_summary)
    exports["detention_full_metric_summary.json"] = (full_summary_path if full_summary else None, full_summary)
    exports["detention_cross_prompt_comparisons.json"] = (
        cross_prompt_path if cross_prompt_path.exists() else None,
        cross_prompt,
    )
    exports["detention_statistical_tests.json"] = (
        statistical_path if statistical_path.exists() else None,
        statistical,
    )
    run_manifest_records: list[dict[str, Any]] = []
    if run_manifest_path.exists():
        run_manifest_records = [json.loads(run_manifest_path.read_text(encoding="utf-8"))]
    exports["detention_pilot_run_manifest.json"] = (
        run_manifest_path if run_manifest_path.exists() and is_pilot else None,
        run_manifest_records if is_pilot else [],
    )
    exports["detention_full_run_manifest.json"] = (
        run_manifest_path if run_manifest_path.exists() and is_full else None,
        run_manifest_records if is_full else [],
    )
    if pilot_report_path.exists() and is_pilot:
        exports["detention_pilot_analysis_report.json"] = (
            pilot_report_path,
            [{"report_name": "detention_pilot_analysis", "title": "Detention Pilot Analysis", "markdown_text": pilot_report_path.read_text(encoding="utf-8")}],
        )
    if full_report_path.exists() and is_full:
        report_text = full_report_path.read_text(encoding="utf-8")
        report_text = _patch_detention_report_counts(
            report_text, pairwise=len(pairwise), flagged=len(flagged)
        )
        exports["detention_full_analysis_report.json"] = (
            full_report_path,
            [{"report_name": "detention_full_analysis", "title": "Detention Full Analysis", "markdown_text": report_text}],
        )
    return exports


def _load_detention_system_exports(
    project_root: Path,
    *,
    use_case: UseCase,
    mock_mode: bool = False,
    gemini_run_dir: Path | None = None,
    data_status: str | None = None,
) -> dict[str, tuple[Path | None, list[dict[str, Any]]]]:
    """Load detention use-case exports (synthetic + approved real-case pilot)."""
    if gemini_run_dir is not None and gemini_run_dir.exists():
        gemini_exports = _load_detention_gemini_run_exports(
            gemini_run_dir, data_status=data_status or "gemini_pilot"
        )
        base = _load_detention_system_exports(
            project_root, use_case=use_case, mock_mode=False, gemini_run_dir=None, data_status=None
        )
        # Keep real-case fulltext from pilot corpus; overlay Gemini analysis metrics
        for key in (
            "detention_real_case_examples_fulltext.json",
            "detention_real_case_quality_report.json",
            "detention_source_manifest.json",
        ):
            if key in base:
                gemini_exports[key] = base[key]
        return gemini_exports

    exports: dict[str, tuple[Path | None, list[dict[str, Any]]]] = {}
    pilot = _load_detention_pilot_exports(project_root)

    fulltext_records = pilot.get("detention_pilot_examples_fulltext.json", (None, []))[1]
    quality_records = pilot.get("detention_pilot_quality_report.json", (None, []))[1]
    manifest_records = pilot.get("detention_pilot_source_manifest.json", (None, []))[1]

    exports["detention_real_case_examples_fulltext.json"] = (
        pilot.get("detention_pilot_examples_fulltext.json", (None, None))[0],
        fulltext_records,
    )
    exports["detention_real_case_quality_report.json"] = (
        pilot.get("detention_pilot_quality_report.json", (None, None))[0],
        quality_records,
    )
    exports["detention_source_manifest.json"] = (
        pilot.get("detention_pilot_source_manifest.json", (None, None))[0],
        manifest_records,
    )

    synthetic_csv = project_root / "data" / "synthetic" / "detention_core_cases.csv"
    if not synthetic_csv.exists():
        synthetic_csv = project_root / "data" / "audit" / "detention" / "detention_counterfactual_cases.csv"
    synthetic_rows: list[dict[str, Any]] = []
    if synthetic_csv.exists():
        synthetic_rows = pd.read_csv(synthetic_csv).to_dict(orient="records")

    pairwise: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    group_summary: list[dict[str, Any]] = []

    mock_analysis_dir = project_root / "results" / "detention_mock_analysis"
    if mock_mode and mock_analysis_dir.exists():
        pp = mock_analysis_dir / "detention_pairwise_comparison.csv"
        fg = mock_analysis_dir / "detention_flagged_cases.csv"
        gs = mock_analysis_dir / "detention_group_summary.csv"
        if pp.exists():
            pairwise = export_csv(pp)
        if fg.exists():
            flagged = export_csv(fg)
        if gs.exists():
            group_summary = export_csv(gs)
    else:
        detention_results = project_root / "results" / "tables"
        pairwise_path = None
        flagged_path = None
        if detention_results.exists():
            pairwise_candidates = sorted(
                detention_results.glob("detention_pairwise_comparison*.csv"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            flagged_candidates = sorted(
                detention_results.glob("detention_flagged_cases*.csv"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if pairwise_candidates:
                pairwise_path = pairwise_candidates[0]
                pairwise = export_csv(pairwise_path)
            if flagged_candidates:
                flagged_path = flagged_candidates[0]
                flagged = export_csv(flagged_path)

    qa_json_path = project_root / "results" / "report" / "detention_synthetic_data_qa.json"
    qa_records: list[dict[str, Any]] = []
    if qa_json_path.exists():
        qa_records = [json.loads(qa_json_path.read_text(encoding="utf-8"))]

    mock_summary_path = project_root / "results" / "report" / "detention_mock_run_summary.json"
    mock_summary: list[dict[str, Any]] = []
    if mock_summary_path.exists():
        mock_summary = [json.loads(mock_summary_path.read_text(encoding="utf-8"))]

    overview: dict[str, Any] = {
        "use_case": use_case,
        "project_name": "BenchAssist-IL Detention Audit",
        "mock_mode": mock_mode,
        "n_synthetic_counterfactual_rows": len(synthetic_rows),
        "n_real_case_pilot_rows": len(fulltext_records),
        "n_pairwise_comparisons": len(pairwise),
        "n_flagged_comparisons": len(flagged),
        "methodology_note": (
            "Screening signals only — not proof of unlawful discrimination. "
            "Not an AI judge. Not legal advice. Human legal review required. "
            "Real-case rows excluded from strict synthetic fairness rates."
        ),
        "disclaimers": [
            "Not legal advice.",
            "Not an AI judge.",
            "Synthetic/toy audit setting.",
            "Metrics are screening signals, not proof of unlawful discrimination.",
            "The tool must not be used to make real detention decisions.",
            "Full-text real legal data is for internal expert review only.",
        ],
    }

    overview["n_pairwise_comparisons"] = len(pairwise)
    overview["n_flagged_comparisons"] = len(flagged)

    exports["detention_overview_metrics.json"] = (None, [overview])
    exports["detention_pairwise_comparison.json"] = (mock_analysis_dir / "detention_pairwise_comparison.csv" if mock_mode else None, pairwise)
    exports["detention_group_summary.json"] = (mock_analysis_dir / "detention_group_summary.csv" if mock_mode else None, group_summary)
    exports["detention_flagged_cases.json"] = (mock_analysis_dir / "detention_flagged_cases.csv" if mock_mode else None, flagged)
    exports["detention_synthetic_data_qa.json"] = (qa_json_path if qa_json_path.exists() else None, qa_records)
    exports["detention_mock_run_summary.json"] = (mock_summary_path if mock_summary_path.exists() else None, mock_summary)
    return exports


def _export_data_access_policy(
    out_dir: Path,
    project_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    """Copy dashboard data access policy; return policy dict and warning messages."""
    warnings: list[str] = []
    policy_src = project_root / "web_dashboard" / "data_access_policy.json"
    policy: dict[str, Any] = {}
    if policy_src.exists():
        policy = json.loads(policy_src.read_text(encoding="utf-8"))
    else:
        policy = {
            "dashboard_data_mode": "unknown",
            "requires_access_control": True,
            "manual_review_required_before_deployment": True,
        }

    detention = _detention_fulltext_indicators(project_root)
    policy["detention_fulltext_indicators"] = detention

    if detention.get("contains_unredacted_public_legal_text") or policy.get(
        "contains_unredacted_public_legal_text"
    ):
        warnings.append(FULL_TEXT_EXPORT_WARNING)

    _write_json(out_dir / "data_access_policy.json", policy)
    return policy, warnings


def export_vercel_data(
    *,
    output_dir: Path | None = None,
    results_dir: Path | None = None,
    use_case: UseCase | None = None,
    mock_mode: bool = False,
    run_dir: Path | None = None,
    data_status: str | None = None,
) -> dict[str, Any]:
    """Export all dashboard JSON files; return manifest summary."""
    effective_use_case = use_case or DEFAULT_USE_CASE
    settings = get_settings()
    root = results_dir or settings.RESULTS_DIR
    project_root = _project_root()
    out_dir = output_dir or default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts = discover_audit_artifacts(root)
    run = select_best_run(artifacts.runs)
    if run is None:
        run = AuditRunBundle(label="empty")

    token = experiment_token_from_run_label(run.label) if run.label != "empty" else "current"
    validity_paths = pick_validity_paths(artifacts, token)
    stereotype_paths = pick_stereotype_paths_for_run(artifacts, run.label)
    mitigation_path = pick_mitigation_for_run(artifacts, run.label)

    stat_effects = _pick_stat_path(artifacts.statistical_group_effects, run.label)
    stat_tests = _pick_stat_path(
        [p for p in artifacts.results_dir.glob("tables/statistical_pairwise_tests*.csv")],
        run.label,
    )
    narrative_summary = _pick_stat_path(artifacts.narrative_robustness_summary, token)
    hallucination_per = _pick_hallucination_per(artifacts, token)
    hallucination_group = _pick_stat_path(artifacts.hallucination_group_summary, token)
    human_review = _pick_by_token(artifacts.human_review_template, token)

    outputs_df = safe_read_csv(run.outputs)
    if outputs_df.empty:
        alt_outputs = _pick_outputs_for_run(root / "outputs", run.label)
        if alt_outputs is not None:
            outputs_df = safe_read_csv(alt_outputs)
            if run.outputs is None:
                source_files_extra = str(alt_outputs)
            else:
                source_files_extra = None
        else:
            source_files_extra = None
    else:
        source_files_extra = None
    parse_rate = compute_parse_error_rate(outputs_df)
    meta = _infer_run_metadata(run, outputs_df)

    pairwise_records = enrich_audit_rows(export_csv(run.pairwise))
    flagged_records = enrich_audit_rows(export_csv(run.flagged))
    if not flagged_records:
        flagged_records = [r for r in pairwise_records if _as_bool(r.get("legal_framing_bias_flag"))]

    cross_prompt_rows, cross_prompt_meta = build_cross_prompt_comparisons(root / "outputs")

    exports: dict[str, tuple[Path | None, list[dict[str, Any]]]] = {
        "group_summary.json": (run.group_summary, export_csv(run.group_summary)),
        "pairwise_comparison.json": (run.pairwise, pairwise_records),
        "flagged_cases.json": (run.flagged, flagged_records),
        "counterfactual_validity.json": (validity_paths.get("per_variant"), export_csv(validity_paths.get("per_variant"))),
        "counterfactual_validity_summary.json": (validity_paths.get("summary"), export_csv(validity_paths.get("summary"))),
        "stereotype_group_summary.json": (stereotype_paths.get("group_summary"), export_csv(stereotype_paths.get("group_summary"))),
        "stereotype_flagged_examples.json": (stereotype_paths.get("flagged_examples"), export_csv(stereotype_paths.get("flagged_examples"))),
        "hallucination_group_summary.json": (hallucination_group, export_csv(hallucination_group)),
        "hallucination_per_output.json": (hallucination_per, export_csv(hallucination_per)),
        "statistical_group_effects.json": (stat_effects, export_csv(stat_effects)),
        "statistical_pairwise_tests.json": (stat_tests, export_csv(stat_tests)),
        "narrative_robustness_summary.json": (narrative_summary, export_csv(narrative_summary)),
        "qualitative_case_studies.json": (run.qualitative, export_csv(run.qualitative)),
        "human_review_template.json": (human_review, export_csv(human_review)),
        "mitigation_comparison.json": (mitigation_path, export_csv(mitigation_path)),
        "cross_prompt_comparisons.json": (root / "outputs", cross_prompt_rows),
    }

    real_case_exports = _load_real_case_layer_exports(root, project_root)
    exports.update(real_case_exports)
    real_case_meta = _real_case_manifest_meta(real_case_exports)

    pilot_exports = _load_detention_pilot_exports(project_root)
    exports.update(pilot_exports)
    if any(records for _, records in pilot_exports.values()):
        real_case_meta["detention_pilot_corpus_available"] = True
        real_case_meta["detention_pilot_row_count"] = len(
            pilot_exports.get("detention_pilot_examples_fulltext.json", (None, []))[1]
        )

    gemini_run: Path | None = None
    if effective_use_case == "detention":
        gemini_run = _resolve_gemini_detention_run_dir(project_root, run_dir, data_status)
        detention_exports = _load_detention_system_exports(
            project_root,
            use_case=effective_use_case,
            mock_mode=mock_mode and gemini_run is None,
            gemini_run_dir=gemini_run,
            data_status=data_status,
        )
        exports.update(detention_exports)
        real_case_meta["use_case"] = "detention"
        overview_list = detention_exports.get("detention_overview_metrics.json", (None, []))[1]
        real_case_meta["detention_synthetic_rows"] = (
            overview_list[0].get("n_synthetic_counterfactual_rows", 0) if overview_list else 0
        )
        if gemini_run is not None:
            from benchassist.detention_case_review_export import export_case_review_records

            synthetic_input = project_root / "data" / "synthetic" / "detention_core_cases.csv"
            if not synthetic_input.exists():
                synthetic_input = project_root / "data" / "audit" / "detention" / "detention_counterfactual_cases.csv"
            review_out = out_dir / "detention_case_review_records.json"
            review_status = data_status or "gemini_full"
            try:
                review_result = export_case_review_records(
                    run_dir=gemini_run,
                    synthetic_input=synthetic_input,
                    output=review_out,
                    data_status=review_status if review_status in {"mock", "gemini_pilot", "gemini_full"} else "gemini_full",
                )
                review_payload = json.loads(review_out.read_text(encoding="utf-8"))
                exports["detention_case_review_records.json"] = (review_out, review_payload)
                index_path = review_out.parent / "detention_case_review_index.json"
                if index_path.exists():
                    exports["detention_case_review_index.json"] = (index_path, json.loads(index_path.read_text(encoding="utf-8")))
                real_case_meta["case_review_records_available"] = review_result["record_count"] > 0
                real_case_meta["case_review_record_count"] = review_result["record_count"]
            except Exception as exc:  # noqa: BLE001 — export should not block dashboard
                real_case_meta["case_review_records_available"] = False
                real_case_meta["case_review_record_count"] = 0
                real_case_meta["case_review_export_error"] = str(exc)

    missing_optional: list[str] = []
    source_files: dict[str, str | None] = {}
    row_counts: dict[str, int] = {}
    detention_pairwise_count: int | None = None
    detention_flagged_count: int | None = None

    for filename, (src, records) in exports.items():
        _write_json(out_dir / filename, records)
        source_files[filename] = str(src) if src else None
        row_counts[filename] = _export_row_count(filename, records)
        if not _export_has_content(records) and (src is None or not Path(src).exists()):
            missing_optional.append(filename)

    if effective_use_case == "detention":
        overview_list = exports.get("detention_overview_metrics.json", (None, []))[1]
        if overview_list:
            detention_pairwise_count = int(overview_list[0].get("n_pairwise_comparisons") or 0)
            detention_flagged_count = int(overview_list[0].get("n_flagged_comparisons") or 0)
        reports = collect_detention_reports(
            project_root,
            gemini_run_dir=gemini_run,
            pairwise_count=detention_pairwise_count,
            flagged_count=detention_flagged_count,
        )
    else:
        reports = collect_reports(root, run.label, project_root)
    _write_json(out_dir / "reports.json", reports)
    source_files["reports.json"] = str(root / "report")
    row_counts["reports.json"] = len(reports)

    overview = compute_overview_metrics(
        group_summary=exports["group_summary.json"][1],
        flagged=exports["flagged_cases.json"][1],
        pairwise=exports["pairwise_comparison.json"][1],
        validity_summary=exports["counterfactual_validity_summary.json"][1],
        stereotype_group=exports["stereotype_group_summary.json"][1],
        hallucination_group=exports["hallucination_group_summary.json"][1],
        outputs_rows=len(outputs_df),
        parse_error_rate=parse_rate,
        base_cases=_count_base_cases(project_root),
        counterfactual_variants=_count_counterfactuals(project_root),
    )
    _write_json(out_dir / "overview_metrics.json", overview)

    if source_files_extra:
        source_files["model_outputs.csv"] = source_files_extra

    primary_files = [
        k for k in ("group_summary.json", "pairwise_comparison.json", "flagged_cases.json", "overview_metrics.json")
        if source_files.get(k)
    ]

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "use_case": effective_use_case,
        "data_status": data_status or ("mock" if mock_mode else None),
        "run_label": run.label,
        "experiment_token": token,
        "run_type": detect_run_type(run.label),
        "selected_source_files": source_files,
        "selected_primary_files": primary_files,
        "missing_optional_files": missing_optional,
        "row_counts": row_counts,
        "provider": meta["provider"],
        "model": meta["model"],
        "prompt_mode": meta["prompt_mode"],
        "prompt_modes": meta["prompt_modes"],
        "schema_versions": meta["schema_versions"],
        "base_cases": overview.get("base_cases"),
        "counterfactual_variants": overview.get("counterfactual_variants"),
        "flagged_cases": overview.get("total_flagged_cases"),
        "parse_error_rate": parse_rate,
        "disclaimer": DISCLAIMER_TEXT,
        "secrets_excluded": True,
        "note": "Export contains no API keys, .env, or live model credentials.",
        "available_sections": [
            name.replace(".json", "")
            for name, count in row_counts.items()
            if count and name != "reports.json"
        ],
        **cross_prompt_meta,
        **real_case_meta,
    }
    if effective_use_case == "detention":
        manifest["export_provenance"] = {
            "git_commit": _git_commit_short(project_root),
            "pairwise_unique_note": (
                "Detention pairwise rows are deduplicated by (case_id, variant_id, prompt_mode) at export."
            ),
            "case_review_split": bool(
                exports.get("detention_case_review_index.json", (None, {}))[1].get("records_split")
                if isinstance(exports.get("detention_case_review_index.json", (None, {}))[1], dict)
                else False
            ),
        }
    _write_json(out_dir / "manifest.json", manifest)

    policy, policy_warnings = _export_data_access_policy(out_dir, project_root)
    manifest["data_access_policy"] = policy
    if policy_warnings:
        manifest["full_text_export_warnings"] = policy_warnings
    _write_json(out_dir / "manifest.json", manifest)

    return manifest


def _pick_stat_path(candidates: list[Path], token: str) -> Path | None:
    for path in candidates:
        if token in path.stem:
            return path
    return candidates[0] if candidates else None


def _pick_hallucination_per(artifacts: Any, token: str) -> Path | None:
    for path in artifacts.hallucination_per_output:
        if token in path.stem or "grounded" in path.stem:
            return path
    return artifacts.hallucination_per_output[0] if artifacts.hallucination_per_output else None


def _pick_by_token(candidates: list[Path], token: str) -> Path | None:
    for path in candidates:
        if token in path.stem:
            return path
    return candidates[0] if candidates else None


def _pick_real_case_tables(results_dir: Path) -> dict[str, Path | None]:
    tables = results_dir / "tables"
    if not tables.exists():
        return {}
    group_files = sorted(tables.glob("real_case_audit_group_summary_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    per_files = sorted(tables.glob("real_case_audit_per_output_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    suffix = group_files[0].stem.replace("real_case_audit_group_summary_", "") if group_files else ""
    per_match = next((p for p in per_files if suffix in p.stem), per_files[0] if per_files else None)
    return {
        "group_summary": group_files[0] if group_files else None,
        "per_output": per_match,
        "suffix": suffix,
    }


def _load_real_case_layer_exports(results_dir: Path, project_root: Path) -> dict[str, tuple[Path | None, list[dict[str, Any]]]]:
    """Load real-case-inspired audit JSON exports (graceful if missing)."""
    picks = _pick_real_case_tables(results_dir)
    data_dir = project_root / "data" / "real_cases"
    domain_csv = data_dir / "real_case_domain_summary.csv"
    examples_csv = data_dir / "real_case_summaries.csv"
    if not examples_csv.exists():
        examples_csv = data_dir / "real_case_bench_inputs.csv"

    return {
        "real_case_audit_summary.json": (picks.get("group_summary"), export_csv(picks.get("group_summary"))),
        "real_case_audit_outputs.json": (picks.get("per_output"), export_csv(picks.get("per_output"))),
        "real_case_domain_summary.json": (domain_csv if domain_csv.exists() else None, export_csv(domain_csv if domain_csv.exists() else None)),
        "real_case_examples.json": (examples_csv if examples_csv.exists() else None, export_csv(examples_csv if examples_csv.exists() else None)),
    }


def _real_case_manifest_meta(
    real_exports: dict[str, tuple[Path | None, list[dict[str, Any]]]],
) -> dict[str, Any]:
    summary = real_exports.get("real_case_audit_summary.json", (None, []))[1]
    examples = real_exports.get("real_case_examples.json", (None, []))[1]
    domains = sorted({str(r.get("normalized_domain", "")) for r in examples if r.get("normalized_domain")})
    has_real = bool(summary or examples)
    modes = ["synthetic_controlled"]
    if has_real:
        modes.append("real_case_inspired")
    if has_real and summary:
        modes.append("hybrid")
    source_dataset = ""
    if examples:
        source_dataset = str(examples[0].get("source_dataset", ""))
    return {
        "dataset_modes_available": modes,
        "real_case_domains_available": domains,
        "real_case_row_count": len(examples),
        "real_case_source_dataset": source_dataset or "BrainboxAI/legal-training-il",
        "real_case_limitations": (
            "Real-case-inspired layer supports realism and domain coverage — not strict counterfactual fairness proof. "
            "Not legal advice. Human legal review required."
        ),
        "real_case_files_selected": {
            k: str(v[0]) if v[0] else None for k, v in real_exports.items()
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export audit data for Vercel dashboard.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: web_dashboard/public/data).",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Export using default paths and latest preferred run.",
    )
    parser.add_argument(
        "--use-case",
        default=None,
        choices=["housing", "detention"],
        help="Audit use case (default: housing — preserves existing behavior).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Include mock/local QA detention analysis exports.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Gemini detention run directory (e.g. results/gemini/detention_pilot).",
    )
    parser.add_argument(
        "--data-status",
        default=None,
        help="Dashboard data status label (e.g. gemini_pilot, mock, final).",
    )
    args = parser.parse_args(argv)

    use_case = normalize_use_case(args.use_case) if args.use_case else DEFAULT_USE_CASE
    manifest = export_vercel_data(
        output_dir=args.output_dir,
        use_case=use_case,
        mock_mode=args.mock,
        run_dir=args.run_dir,
        data_status=args.data_status,
    )
    out = args.output_dir or default_output_dir()
    print(f"Vercel export complete → {out}")
    print(f"  Run: {manifest.get('run_label')}")
    print(f"  Model: {manifest.get('model')} ({manifest.get('provider')})")
    print(f"  Missing optional: {len(manifest.get('missing_optional_files', []))}")
    for warning in manifest.get("full_text_export_warnings", []):
        print(f"  WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
