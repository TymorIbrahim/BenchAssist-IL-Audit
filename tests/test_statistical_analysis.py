"""Tests for statistical uncertainty analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchassist.config import get_settings
from benchassist.dashboard_utils import (
    discover_audit_artifacts,
    list_statistical_suffixes,
    pick_statistical_paths,
    summarize_statistical_signals,
)
from benchassist.final_report import (
    ReportInputs,
    build_final_audit_report,
    summarize_statistical_uncertainty,
)
from benchassist.statistical_analysis import (
    apply_benjamini_hochberg,
    bootstrap_ci,
    build_group_effects_table,
    compute_binary_group_stats,
    compute_numeric_group_stats,
    compute_pairwise_tests,
    paired_test_against_zero,
    run_statistical_analysis,
    sign_test_p_value,
    wilson_interval,
)


def _synthetic_pairwise() -> pd.DataFrame:
    rows = []
    variants = [
        ("broken_hebrew", "broken Hebrew", True, -1.5, 0.5, 0.3, -0.4),
        ("arab_male_name_he", "Ahmed", False, -0.2, 0.1, 0.0, -0.1),
    ]
    for case_id in ("H001", "H002", "H003"):
        for vt, cue, flag, remedy, evid, cred, rights in variants:
            rows.append(
                {
                    "case_id": case_id,
                    "variant_type": vt,
                    "demographic_cue": cue,
                    "legal_framing_bias_flag": flag,
                    "action_type_flip": flag,
                    "remedy_weaker": remedy < 0,
                    "evidence_burden_higher": evid > 0,
                    "credibility_more_skeptical": cred > 0,
                    "rights_orientation_weaker": rights < 0,
                    "remedy_strength_delta": remedy,
                    "evidence_burden_delta": evid,
                    "credibility_skepticism_delta": cred,
                    "rights_orientation_delta": rights,
                    "urgency_delta": -0.1,
                    "procedural_posture_delta": 0.0,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture()
def isolated_results(tmp_path, monkeypatch):
    results_dir = tmp_path / "results"
    for sub in ("tables", "report", "charts"):
        (results_dir / sub).mkdir(parents=True)
    monkeypatch.setenv("RESULTS_DIR", str(results_dir))
    get_settings.cache_clear()
    return results_dir


class TestWilsonInterval:
    def test_bounds_sensible(self) -> None:
        lo, hi = wilson_interval(5, 10)
        assert 0.0 <= lo <= hi <= 1.0
        assert lo < 0.7 < hi

    def test_empty_n_is_nan(self) -> None:
        lo, hi = wilson_interval(0, 0)
        assert pd.isna(lo) and pd.isna(hi)


class TestBootstrapCI:
    def test_fixed_seed_reproducible(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        m1, lo1, hi1, _ = bootstrap_ci(values, n_resamples=500, seed=42)
        m2, lo2, hi2, _ = bootstrap_ci(values, n_resamples=500, seed=42)
        assert m1 == m2 == pytest.approx(3.0)
        assert lo1 == lo2
        assert hi1 == hi2
        assert lo1 < m1 < hi1

    def test_small_n_warning(self) -> None:
        mean, lo, hi, warning = bootstrap_ci([2.0], n_resamples=100, seed=1)
        assert mean == pytest.approx(2.0)
        assert lo == hi == pytest.approx(2.0)
        assert "n<2" in warning


class TestGroupStats:
    def test_binary_group_stats(self) -> None:
        df = _synthetic_pairwise()
        rows = compute_binary_group_stats(df, "legal_framing_bias_flag")
        assert rows
        row = next(r for r in rows if r["variant_type"] == "broken_hebrew")
        assert row["n"] == 3
        assert row["count_true"] == 3
        assert row["rate"] == pytest.approx(1.0)
        assert row["ci_lower"] <= row["rate"] <= row["ci_upper"]

    def test_numeric_group_stats(self) -> None:
        df = _synthetic_pairwise()
        rows = compute_numeric_group_stats(
            df, "remedy_strength_delta", bootstrap_samples=200, seed=7
        )
        row = next(r for r in rows if r["variant_type"] == "broken_hebrew")
        assert row["n"] == 3
        assert row["mean"] == pytest.approx(-1.5)
        assert row["median"] == pytest.approx(-1.5)
        assert not pd.isna(row["ci_lower"])
        assert not pd.isna(row["ci_upper"])


class TestPairedTests:
    def test_sign_test_does_not_crash(self) -> None:
        p = sign_test_p_value(3, 1)
        assert 0.0 <= p <= 1.0

    def test_paired_test_fallback(self) -> None:
        name, p = paired_test_against_zero([0.5, -0.2, 0.3, -0.1])
        assert name in {"wilcoxon", "sign_test", "insufficient_n", "insufficient_nonzero"}
        assert p == p  # not nan for sufficient data with scipy or sign test

    def test_insufficient_n(self) -> None:
        name, p = paired_test_against_zero([1.0])
        assert name == "insufficient_n"
        assert pd.isna(p)

    def test_bh_fdr_columns(self) -> None:
        tests = pd.DataFrame(
            [
                {"p_value": 0.01},
                {"p_value": 0.20},
                {"p_value": 0.04},
            ]
        )
        out = apply_benjamini_hochberg(tests)
        assert "p_value_fdr_bh" in out.columns
        assert "significant_fdr_0_10" in out.columns


class TestSmallSample:
    def test_single_row_pairwise(self) -> None:
        df = _synthetic_pairwise().head(1)
        effects = build_group_effects_table(df, bootstrap_samples=50, seed=1)
        assert not effects.empty
        assert (effects["small_sample_warning"] != "").any() or effects["n"].max() == 1


class TestCLI:
    def test_writes_expected_artefacts(self, isolated_results: Path) -> None:
        pairwise_path = isolated_results / "tables" / "v2_pairwise_test.csv"
        _synthetic_pairwise().to_csv(pairwise_path, index=False)
        result = run_statistical_analysis(
            pairwise_path,
            output_suffix="test_run",
            bootstrap_samples=100,
            seed=42,
            results_dir=isolated_results,
        )
        paths = result["paths"]
        assert paths["group_effects"].exists()
        assert paths["pairwise_tests"].exists()
        assert paths["report"].exists()
        assert paths["chart_effects"].exists()
        assert paths["chart_ci"].exists()
        report = paths["report"].read_text(encoding="utf-8")
        assert "# Statistical Uncertainty Analysis" in report
        assert "Multiple comparisons" in report


class TestDashboardIntegration:
    def test_missing_statistical_files_ok(self, isolated_results: Path) -> None:
        artifacts = discover_audit_artifacts(isolated_results)
        assert list_statistical_suffixes(artifacts) == []
        paths = pick_statistical_paths(artifacts, "none")
        assert paths["group_effects"] is None or not paths["group_effects"].exists()

    def test_discover_statistical_suffixes(self, isolated_results: Path) -> None:
        effects = isolated_results / "tables" / "statistical_group_effects_demo.csv"
        pd.DataFrame([{"variant_type": "x", "metric": "y"}]).to_csv(effects, index=False)
        artifacts = discover_audit_artifacts(isolated_results)
        assert "demo" in list_statistical_suffixes(artifacts)


class TestFinalReportIntegration:
    def test_includes_statistical_section_when_files_exist(
        self, isolated_results: Path
    ) -> None:
        pairwise_path = isolated_results / "tables" / "v2_pairwise_test.csv"
        _synthetic_pairwise().to_csv(pairwise_path, index=False)
        run_statistical_analysis(
            pairwise_path,
            output_suffix="test_run",
            bootstrap_samples=50,
            seed=1,
            results_dir=isolated_results,
        )
        inputs = ReportInputs(
            statistical_report=isolated_results / "report" / "statistical_analysis_test_run.md",
            statistical_group_effects=isolated_results
            / "tables"
            / "statistical_group_effects_test_run.csv",
            statistical_pairwise_tests=isolated_results
            / "tables"
            / "statistical_pairwise_tests_test_run.csv",
            output=isolated_results / "report" / "final_audit_report.md",
        )
        text = build_final_audit_report(inputs)
        assert "## Statistical Uncertainty" in text
        assert "audit screening signals" in text.lower()

    def test_missing_statistical_does_not_fail(self, isolated_results: Path) -> None:
        text = build_final_audit_report(
            ReportInputs(output=isolated_results / "report" / "final_audit_report.md")
        )
        assert "Not available in this run (Statistical uncertainty" in text

    def test_summarize_statistical_uncertainty(self, isolated_results: Path) -> None:
        pairwise_path = isolated_results / "tables" / "v2_pairwise_test.csv"
        _synthetic_pairwise().to_csv(pairwise_path, index=False)
        run_statistical_analysis(
            pairwise_path,
            output_suffix="test_run",
            bootstrap_samples=50,
            seed=1,
            results_dir=isolated_results,
        )
        effects = pd.read_csv(
            isolated_results / "tables" / "statistical_group_effects_test_run.csv"
        )
        tests = pd.read_csv(
            isolated_results / "tables" / "statistical_pairwise_tests_test_run.csv"
        )
        summary = summarize_statistical_uncertainty(effects, tests)
        assert summary["available"] is True
        assert summary["highlights"]

    def test_dashboard_signals_helper(self, isolated_results: Path) -> None:
        pairwise_path = isolated_results / "tables" / "v2_pairwise_test.csv"
        _synthetic_pairwise().to_csv(pairwise_path, index=False)
        run_statistical_analysis(
            pairwise_path,
            output_suffix="test_run",
            bootstrap_samples=50,
            seed=1,
            results_dir=isolated_results,
        )
        effects = pd.read_csv(
            isolated_results / "tables" / "statistical_group_effects_test_run.csv"
        )
        signals = summarize_statistical_signals(effects)
        assert not signals.empty
