"""Dashboard export manifest helpers: completeness, lineage, missing-file impact."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# Which optional export keys affect which dashboard tabs (empty state vs silent gap).
MISSING_OPTIONAL_FILE_IMPACT: dict[str, dict[str, str]] = {
    "detention_cross_prompt_comparisons.json": {
        "tabs": "Mitigation, Case Review (cross-prompt panel)",
        "effect": "Cross-prompt heatmap and instability strip show empty state.",
    },
    "detention_statistical_tests.json": {
        "tabs": "Audit Results",
        "effect": "Wilson/FDR table hidden; headline rates still available.",
    },
    "detention_statistical_tests_baseline.json": {
        "tabs": "Audit Results",
        "effect": "Baseline-only statistical table omitted.",
    },
    "detention_real_case_examples_fulltext.json": {
        "tabs": "(none in slim 7-tab product)",
        "effect": "No impact on current detention dashboard.",
    },
    "detention_stereotype_flagged_examples.json": {
        "tabs": "(none in slim product)",
        "effect": "Legacy housing-era export; safe to omit.",
    },
    "detention_hallucination_per_output.json": {
        "tabs": "(none in slim product)",
        "effect": "Not used in minimal-schema dashboard.",
    },
}

CRITICAL_DETENTION_EXPORTS: tuple[str, ...] = (
    "manifest.json",
    "overview_metrics.json",
    "detention_overview_metrics.json",
    "detention_pairwise_comparison.json",
    "detention_flagged_cases.json",
    "detention_case_review_index.json",
)


def git_commit_short(project_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return out.stdout.strip() or None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def read_parent_run_id(run_dir: Path | None) -> str | None:
    if not run_dir:
        return None
    manifest = run_dir / "run_manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return str(data.get("parent_run_id") or data.get("resume_from_run_id") or "") or None
    except (json.JSONDecodeError, OSError):
        return None


def export_completeness_score(
    row_counts: dict[str, int],
    *,
    missing_optional: list[str],
    critical_present: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """0–100 score: critical files must be present; optional files add weight."""
    checks = {
        "detention_overview_metrics.json": row_counts.get("detention_overview_metrics.json", 0) > 0,
        "detention_pairwise_comparison.json": row_counts.get("detention_pairwise_comparison.json", 0) > 0,
        "detention_flagged_cases.json": row_counts.get("detention_flagged_cases.json", 0) > 0,
        "detention_case_review_index.json": row_counts.get("detention_case_review_index.json", 0) > 0,
    }
    critical_ok = all(checks.values())
    optional_total = 12
    optional_present = sum(1 for k, n in row_counts.items() if n > 0 and k.endswith(".json"))
    optional_score = min(optional_present / max(optional_total, 1), 1.0) * 40
    critical_score = 60 if critical_ok else int(60 * sum(checks.values()) / max(len(checks), 1))
    score = int(min(100, critical_score + optional_score))
    return {
        "export_completeness_score": score,
        "critical_exports_ok": critical_ok,
        "critical_export_checks": checks,
        "optional_files_missing": missing_optional,
        "deploy_blocked": not critical_ok,
    }


def missing_optional_files_detail(missing: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for name in missing:
        impact = MISSING_OPTIONAL_FILE_IMPACT.get(name, {})
        out.append(
            {
                "file": name,
                "tabs_affected": impact.get("tabs", "Unknown"),
                "effect": impact.get("effect", "May show empty state where data is referenced."),
            }
        )
    return out


def build_cross_prompt_mode_summary(cross_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per prompt-mode material vs wording-only counts for Mitigation export."""
    by_mode: dict[str, dict[str, int]] = {}
    for row in cross_rows:
        mode = str(row.get("comparison_mode") or row.get("prompt_mode") or "unknown")
        bucket = by_mode.setdefault(mode, {"material_instability": 0, "wording_only": 0, "total": 0})
        bucket["total"] += 1
        if row.get("cross_prompt_instability_flag") in (True, "True", "true", 1):
            bucket["material_instability"] += 1
        elif row.get("reasoning_only_change") in (True, "True", "true", 1):
            bucket["wording_only"] += 1
        else:
            bucket["wording_only"] += 1
    return {
        "by_comparison_mode": by_mode,
        "note": "Exploratory screening only — not merged into strict dangerousness flagged rates.",
    }
