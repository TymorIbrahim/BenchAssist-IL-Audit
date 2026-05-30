"""Generate consolidated mock pipeline QA report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_mock_pipeline_qa_report(project_root: Path | None = None) -> Path:
    root = project_root or Path(__file__).resolve().parent.parent.parent
    report_dir = root / "results" / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / "detention_mock_pipeline_qa_report.md"

    def _read_json(path: Path) -> dict | None:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    synthetic_qa = _read_json(report_dir / "detention_synthetic_data_qa.json")
    mock_summary = _read_json(report_dir / "detention_mock_run_summary.json")
    metric = _read_json(root / "results" / "detention_mock_analysis" / "detention_metric_summary.json")
    real_qa_exists = (report_dir / "detention_real_case_integration_qa.md").exists()
    validation_passed = mock_summary.get("schema_validation_passed") if mock_summary else None

    lines = [
        "# Detention Mock Pipeline QA Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Status summary",
        "",
        "| Step | Status |",
        "|------|--------|",
        f"| Synthetic data generation | {'OK' if synthetic_qa else 'MISSING'} |",
        f"| Schema validation | {'PASS' if validation_passed else 'UNKNOWN/FAIL'} |",
        f"| Mock runs (3 prompt modes) | {'OK' if mock_summary else 'MISSING'} |",
        f"| Detention analysis | {'OK' if metric else 'MISSING'} |",
        f"| Real-case integration QA | {'OK' if real_qa_exists else 'MISSING'} |",
        f"| Vercel export (mock) | see manifest |",
        "",
        "## Important disclaimers",
        "",
        "- **Mock outputs are not research findings.**",
        "- Mock outputs are used only to test the pipeline before any Gemini run.",
        "- Real cases must **not** be used for strict fairness-rate claims.",
        "- Human legal review is required before operational use or deployment.",
        "- **Gemini should only be run after this QA passes.**",
        "",
        "## Synthetic data",
        "",
    ]
    if synthetic_qa:
        lines.extend(
            [
                f"- Base cases: {synthetic_qa.get('n_base_cases')}",
                f"- Total variants: {synthetic_qa.get('n_total_variants')}",
                f"- Strict included: {synthetic_qa.get('strict_fairness_included')}",
                f"- Strict excluded: {synthetic_qa.get('strict_fairness_excluded')}",
            ]
        )
    if mock_summary:
        lines.extend(["", "## Mock runs", ""])
        for mode, info in mock_summary.get("runs", {}).items():
            lines.append(f"- {mode}: {info.get('n_outputs')} outputs")
    if metric:
        lines.extend(
            [
                "",
                "## Analysis metrics",
                "",
                f"- Pairwise comparisons: {metric.get('n_pairwise_comparisons')}",
                f"- Flagged comparisons: {metric.get('n_flagged_comparisons')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Next step",
            "",
            "If all checks pass, proceed to Gemini dry-run/pilot with detention prompts and schema.",
            "Do not deploy to Vercel without access control for full-text real-case data.",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    path = build_mock_pipeline_qa_report()
    print(f"Pipeline QA report → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
