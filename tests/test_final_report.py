"""Tests for the final Responsible AI audit report generator."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchassist.config import get_settings
from benchassist.final_report import (
    build_final_audit_report,
    discover_report_inputs,
    markdown_table_top,
    read_csv_optional,
    summarize_group_summary,
    write_final_audit_report,
    ReportInputs,
)


def _synthetic_v2_group_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "variant_type": "broken_hebrew",
                "demographic_cue": "broken Hebrew",
                "n_pairs": 12,
                "action_type_flip_rate": 0.25,
                "legal_framing_bias_flag_rate": 0.42,
                "remedy_weaker_rate": 0.33,
                "evidence_burden_higher_rate": 0.30,
                "credibility_more_skeptical_rate": 0.28,
                "rights_orientation_weaker_rate": 0.20,
            },
            {
                "variant_type": "arab_male_name_he",
                "demographic_cue": "Ahmed",
                "n_pairs": 12,
                "action_type_flip_rate": 0.20,
                "legal_framing_bias_flag_rate": 0.35,
                "remedy_weaker_rate": 0.25,
                "evidence_burden_higher_rate": 0.22,
                "credibility_more_skeptical_rate": 0.18,
                "rights_orientation_weaker_rate": 0.15,
            },
        ]
    )


@pytest.fixture()
def isolated_results(tmp_path, monkeypatch):
    results_dir = tmp_path / "results"
    (results_dir / "tables").mkdir(parents=True)
    (results_dir / "report").mkdir(parents=True)
    (results_dir / "charts").mkdir(parents=True)
    monkeypatch.setenv("RESULTS_DIR", str(results_dir))
    get_settings.cache_clear()
    return results_dir


class TestFinalReportHelpers:
    def test_summarize_group_summary(self) -> None:
        summary = summarize_group_summary(_synthetic_v2_group_summary())
        assert summary["available"] is True
        assert summary["top_variants"][0] == "broken_hebrew"
        assert summary["highest_rate"] == pytest.approx(0.42)

    def test_markdown_table_top(self) -> None:
        table = markdown_table_top(
            _synthetic_v2_group_summary(),
            ["variant_type", "legal_framing_bias_flag_rate"],
            sort_by="legal_framing_bias_flag_rate",
            top_n=1,
        )
        assert "broken_hebrew" in table
        assert "0.420" in table or "0.42" in table


class TestFinalReportGeneration:
    def test_runs_with_no_optional_inputs(self, isolated_results: Path) -> None:
        output = isolated_results / "report" / "final_audit_report.md"
        inputs = ReportInputs(output=output, availability={"all": "not provided"})
        path = write_final_audit_report(inputs)
        text = path.read_text(encoding="utf-8")
        assert path.exists()
        assert "# Final Audit Report: BenchAssist-IL" in text
        assert "Not available in this run" in text

    def test_includes_goodman_trehu_sections(self, isolated_results: Path) -> None:
        inputs = ReportInputs(
            output=isolated_results / "report" / "final_audit_report.md"
        )
        text = build_final_audit_report(inputs)
        assert "## 4. Audit Framework" in text
        assert "### Why" in text
        assert "### Who" in text
        assert "### What and When" in text
        assert "### How" in text
        assert "Goodman" in text

    def test_includes_audit_washing_section(self, isolated_results: Path) -> None:
        text = build_final_audit_report(
            ReportInputs(output=isolated_results / "report" / "final_audit_report.md")
        )
        assert "## 13. Audit-Washing Risks" in text
        assert "audit-washing" in text.lower()
        assert "V2 schema" in text

    def test_includes_limitations_section(self, isolated_results: Path) -> None:
        text = build_final_audit_report(
            ReportInputs(output=isolated_results / "report" / "final_audit_report.md")
        )
        assert "## 14. Limitations" in text
        assert "synthetic" in text.lower()

    def test_summarizes_synthetic_group_summary(self, isolated_results: Path) -> None:
        group_path = isolated_results / "tables" / "v2_group_summary_test.csv"
        _synthetic_v2_group_summary().to_csv(group_path, index=False)
        inputs = ReportInputs(
            group_summary=group_path,
            output=isolated_results / "report" / "final_audit_report.md",
            availability={"group_summary": str(group_path)},
        )
        text = build_final_audit_report(inputs)
        assert "## 7. Quantitative Results" in text
        assert "broken_hebrew" in text
        assert "legal_framing_bias_flag_rate" in text

    def test_handles_missing_optional_files(self, isolated_results: Path) -> None:
        inputs = ReportInputs(
            group_summary=isolated_results / "tables" / "missing.csv",
            qualitative=isolated_results / "report" / "missing.md",
            output=isolated_results / "report" / "final_audit_report.md",
        )
        text = build_final_audit_report(inputs)
        assert "Not available in this run" in text
        assert read_csv_optional(inputs.group_summary) is None

    def test_auto_mode_does_not_crash(self, isolated_results: Path) -> None:
        group_path = isolated_results / "tables" / "v2_group_summary_baseline.csv"
        _synthetic_v2_group_summary().to_csv(group_path, index=False)
        inputs = discover_report_inputs(isolated_results)
        path = write_final_audit_report(inputs)
        assert path.exists()

    def test_includes_statistical_section_when_artefacts_exist(
        self, isolated_results: Path
    ) -> None:
        from benchassist.statistical_analysis import run_statistical_analysis

        pairwise_path = isolated_results / "tables" / "v2_pairwise_test.csv"
        pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "x",
                    "legal_framing_bias_flag": True,
                    "remedy_strength_delta": -1.0,
                    "evidence_burden_delta": 0.5,
                    "credibility_skepticism_delta": 0.2,
                    "rights_orientation_delta": -0.3,
                    "urgency_delta": 0.0,
                    "procedural_posture_delta": 0.0,
                }
            ]
        ).to_csv(pairwise_path, index=False)
        run_statistical_analysis(
            pairwise_path,
            output_suffix="test_run",
            bootstrap_samples=50,
            seed=1,
            results_dir=isolated_results,
        )
        inputs = ReportInputs(
            statistical_group_effects=isolated_results
            / "tables"
            / "statistical_group_effects_test_run.csv",
            statistical_pairwise_tests=isolated_results
            / "tables"
            / "statistical_pairwise_tests_test_run.csv",
            statistical_report=isolated_results / "report" / "statistical_analysis_test_run.md",
            output=isolated_results / "report" / "final_audit_report.md",
        )
        text = build_final_audit_report(inputs)
        assert "## Statistical Uncertainty" in text

    def test_includes_chart_links_when_charts_exist(self, isolated_results: Path) -> None:
        chart = isolated_results / "charts" / "v2_legal_framing_bias_flag_rate_by_variant.png"
        chart.write_bytes(b"png")
        inputs = ReportInputs(
            charts_dir=isolated_results / "charts",
            output=isolated_results / "report" / "final_audit_report.md",
        )
        text = build_final_audit_report(inputs)
        assert "## Available Charts" in text
        assert "v2_legal_framing_bias_flag_rate_by_variant.png" in text
