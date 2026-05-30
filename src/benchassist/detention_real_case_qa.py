"""QA checks for approved real-case detention pilot corpus integration."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.dataset_modes import exclude_from_strict_bias, parse_bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_pilot_rows(input_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fulltext = input_dir / "detention_pilot_fulltext.jsonl"
    summaries = input_dir / "detention_pilot_summaries.csv"
    sensitive = input_dir / "detention_pilot_sensitive_review.csv"
    quality = input_dir / "detention_pilot_quality_report.json"

    rows: list[dict[str, Any]] = []
    if fulltext.exists():
        for line in fulltext.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    meta: dict[str, Any] = {
        "fulltext_path": str(fulltext) if fulltext.exists() else None,
        "summaries_path": str(summaries) if summaries.exists() else None,
        "sensitive_path": str(sensitive) if sensitive.exists() else None,
        "quality_path": str(quality) if quality.exists() else None,
        "n_fulltext_rows": len(rows),
    }
    if quality.exists():
        meta["quality_report"] = json.loads(quality.read_text(encoding="utf-8"))
    return rows, meta


def run_real_case_qa(input_dir: Path, output: Path) -> dict[str, Any]:
    """Run real-case integration QA and write markdown report."""
    rows, meta = _load_pilot_rows(input_dir)
    project_root = Path(__file__).resolve().parent.parent.parent
    policy_path = project_root / "web_dashboard" / "data_access_policy.json"

    checks: list[dict[str, Any]] = []
    warnings: list[str] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})
        if not passed:
            warnings.append(f"{name}: {detail}")

    check("pilot_rows_present", len(rows) > 0, f"n={len(rows)}")
    check("data_access_policy_exists", policy_path.exists(), str(policy_path))

    if rows:
        sample = rows[0]
        check("full_text_preserved", bool(sample.get("full_text") or sample.get("text")), "full text field present")
        check(
            "source_attribution",
            bool(sample.get("source_dataset") and sample.get("source_id")),
            "source_dataset/source_id",
        )
        check("expert_review_status_field", "expert_review_status" in sample, "")
        check("manual_review_required", parse_bool(sample.get("manual_review_required"), default=False), "")
        check("use_for_strict_bias_rates_false", not parse_bool(sample.get("use_for_strict_bias_rates"), default=False), "")
        check("exclude_from_strict_bias_rates_true", parse_bool(sample.get("exclude_from_strict_bias_rates")), "")
        check(
            "data_visibility_internal",
            str(sample.get("data_visibility", "")) == "internal_full_text",
            str(sample.get("data_visibility")),
        )
        check("dataset_mode_real", str(sample.get("dataset_mode")) == "real_case_inspired", "")
        check("strict_filter_excludes_all", all(exclude_from_strict_bias(r) for r in rows), "all pilot rows excluded")

        sensitive_csv = input_dir / "detention_pilot_sensitive_review.csv"
        if sensitive_csv.exists():
            sens_df = pd.read_csv(sensitive_csv)
            check("sensitive_review_file_present", len(sens_df) > 0, f"n={len(sens_df)}")
            if "include_in_model_inputs" in sens_df.columns:
                default_blocked = (sens_df["include_in_model_inputs"] == False).all()  # noqa: E712
                check("sensitive_default_not_model_inputs", default_blocked, "sensitive rows blocked by default")

    passed = sum(1 for c in checks if c["passed"])
    result = {
        "generated_at": _utc_now(),
        "input_dir": str(input_dir),
        "n_rows": len(rows),
        "checks": checks,
        "n_passed": passed,
        "n_total": len(checks),
        "all_passed": passed == len(checks),
        "warnings": warnings,
        "meta": meta,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Detention Real-Case Integration QA",
        "",
        f"Generated: {result['generated_at']}",
        "",
        f"Pilot directory: `{input_dir}`",
        "",
        f"**Status:** {'PASS' if result['all_passed'] else 'ISSUES FOUND'} ({passed}/{len(checks)} checks)",
        "",
        "## Checks",
        "",
    ]
    for c in checks:
        mark = "✓" if c["passed"] else "✗"
        lines.append(f"- {mark} **{c['check']}** — {c['detail']}")
    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "- Real-case-inspired rows support realism and legal-expert review only.",
            "- They must **not** be used for strict demographic fairness-rate claims.",
            "- Full text is preserved for internal expert review (access control required).",
            "- Human legal review is required before any operational use.",
            "",
        ]
    )
    if warnings:
        lines.extend(["## Warnings", ""] + [f"- {w}" for w in warnings])
    output.write_text("\n".join(lines), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA for detention real-case pilot integration.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    result = run_real_case_qa(args.input_dir, args.output)
    status = "PASS" if result["all_passed"] else "FAIL"
    print(f"Real-case integration QA: {status} ({result['n_passed']}/{result['n_total']}) → {args.output}")
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
