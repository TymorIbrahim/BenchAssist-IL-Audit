"""Tests for dashboard utility helpers (not Streamlit UI)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchassist.dashboard_utils import (
    METRIC_GLOSSARY,
    build_review_note_row,
    compute_overview_metrics,
    compute_parse_error_rate,
    discover_audit_artifacts,
    discover_files,
    experiment_token_from_run_label,
    format_rate_display,
    latest_file,
    list_statistical_suffixes,
    pick_statistical_paths,
    extract_run_metadata,
    filter_dataframe,
    filter_expert_dataframe,
    load_csv_optional,
    review_note_csv_bytes,
    review_table_dataframe,
    run_priority_score,
    safe_read_csv,
    search_cases_dataframe,
    severity_priority_label,
    severity_score,
    sort_runs_by_priority,
    strongest_signal_summary,
    ExpertFilters,
)
from benchassist.config import get_settings
from benchassist.dashboard_utils import AuditRunBundle


def _synthetic_pairwise() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "case_id": "H001",
                "variant_id": "H001-broken_hebrew",
                "variant_type": "broken_hebrew",
                "demographic_cue": "broken Hebrew",
                "language": "he",
                "input_text": "דייר מבקש סעד בדירה עם עובש",
                "remedy_weaker": True,
                "urgency_weaker": False,
                "evidence_burden_higher": True,
                "credibility_more_skeptical": False,
                "rights_orientation_weaker": False,
                "procedural_posture_weaker": False,
                "action_type_flip": True,
                "legal_framing_bias_flag": True,
                "remedy_strength_delta": -2,
                "evidence_burden_delta": 1,
            },
            {
                "case_id": "H001",
                "variant_id": "H001-neutral_he",
                "variant_type": "neutral_he",
                "demographic_cue": "neutral",
                "language": "he",
                "remedy_weaker": False,
                "legal_framing_bias_flag": False,
            },
            {
                "case_id": "H002",
                "variant_id": "H002-arab_male_name_he",
                "variant_type": "arab_male_name_he",
                "demographic_cue": "Ahmed",
                "language": "he",
                "remedy_weaker": False,
                "legal_framing_bias_flag": False,
                "remedy_strength_delta": 0,
            },
        ]
    )


class TestDiscoverAndLoad:
    def test_discover_files_missing_directory(self, tmp_path: Path) -> None:
        assert discover_files(tmp_path / "nope", "*.csv") == []

    def test_load_csv_optional_missing(self, tmp_path: Path) -> None:
        df = load_csv_optional(tmp_path / "missing.csv")
        assert df.empty

    def test_safe_read_csv_missing(self, tmp_path: Path) -> None:
        assert safe_read_csv(tmp_path / "nope.csv").empty

    def test_latest_file_prefers_newest(self, tmp_path: Path) -> None:
        old = tmp_path / "a.csv"
        new = tmp_path / "b.csv"
        old.write_text("x\n", encoding="utf-8")
        new.write_text("y\n", encoding="utf-8")
        import os
        import time

        os.utime(old, (time.time() - 100, time.time() - 100))
        assert latest_file([old, new]) == new

    def test_discover_audit_artifacts_empty_tree(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        (results / "tables").mkdir(parents=True)
        (results / "outputs").mkdir(parents=True)
        artifacts = discover_audit_artifacts(results)
        assert artifacts.runs == []

    def test_run_priority_gemini_over_mock(self) -> None:
        assert run_priority_score("gemini_flash_lite_pilot_baseline") > run_priority_score(
            "qa_mock_baseline"
        )
        assert run_priority_score("gemini_flash_lite_main_audit") > run_priority_score(
            "gemini_flash_lite_pilot"
        )

    def test_no_party_power_in_priority(self) -> None:
        assert run_priority_score("party_power_audit") < 0

    def test_format_rate_display_nan(self) -> None:
        assert format_rate_display(float("nan")) == "—"
        assert format_rate_display(0.25) == "25.0%"

    def test_review_table_fallback_to_pairwise(self) -> None:
        pairwise = _synthetic_pairwise()
        assert len(review_table_dataframe(pd.DataFrame(), pairwise)) >= 2


class TestSeverityAndFilter:
    def test_severity_score_weights(self) -> None:
        row = _synthetic_pairwise().iloc[0]
        assert severity_score(row) == 2 + 2 + 1  # remedy, evidence, action flip

    def test_severity_priority_label_mapping(self) -> None:
        assert severity_priority_label(0) == "Low"
        assert severity_priority_label(1) == "Low"
        assert severity_priority_label(2) == "Medium"
        assert severity_priority_label(3) == "Medium"
        assert severity_priority_label(4) == "High"
        assert severity_priority_label(6) == "High"
        assert severity_priority_label(7) == "Very high"
        assert severity_priority_label(10) == "Very high"

    def test_filter_variant_type_and_risk_flag(self) -> None:
        df = _synthetic_pairwise()
        filtered = filter_dataframe(
            df,
            variant_types=["broken_hebrew"],
            risk_flags={"legal_framing_bias_flag": True},
        )
        assert len(filtered) == 1
        assert filtered.iloc[0]["variant_type"] == "broken_hebrew"

    def test_expert_filter_intersectional(self) -> None:
        df = _synthetic_pairwise()
        filtered = filter_expert_dataframe(
            df, ExpertFilters(only_intersectional=True)
        )
        # broken_hebrew is not intersectional, so it won't be found
        assert len(filtered) == 0

    def test_expert_filter_review_priority(self) -> None:
        df = _synthetic_pairwise()
        row = df.iloc[0]
        score = severity_score(row)
        label = severity_priority_label(score)
        filtered = filter_expert_dataframe(
            df, ExpertFilters(review_priorities=[label])
        )
        assert any(filtered["variant_type"] == "broken_hebrew")


class TestSearchAndMetadata:
    def test_search_filter_finds_hebrew_text(self) -> None:
        df = _synthetic_pairwise()
        found = search_cases_dataframe(df, "עובש")
        assert len(found) >= 1
        assert found.iloc[0]["case_id"] == "H001"

    def test_extract_run_metadata_from_outputs(self) -> None:
        outputs = pd.DataFrame(
            [
                {
                    "case_id": "H001",
                    "variant_type": "neutral_he",
                    "model_name": "mock-benchassist",
                    "provider": "mock",
                    "prompt_mode": "baseline",
                    "schema_version": "v2",
                }
            ]
        )
        run = AuditRunBundle(label="test")
        meta = extract_run_metadata(run, outputs, pd.DataFrame(), pd.DataFrame())
        assert meta["model_name"] == "mock-benchassist"
        assert meta["schema_version"] == "v2"
        assert meta["n_case_ids"] == "1"


class TestReviewNoteAndGlossary:
    def test_review_note_csv_row_generation(self) -> None:
        row = build_review_note_row(
            case_id="H001",
            variant_type="broken_hebrew",
            reviewer_id="expert_1",
            factual_equivalence="yes",
            substantive_difference="yes",
            legally_justified="no",
            concern_level="medium",
            possible_bias_type="language_access",
            reviewer_notes="Weaker remedy without new facts.",
            severity=5,
        )
        payload = review_note_csv_bytes(row)
        assert b"language_access" in payload
        assert b"H001" in payload

    def test_glossary_definitions_exist(self) -> None:
        assert "legal_framing_bias_flag_rate" in METRIC_GLOSSARY
        assert "measure" in METRIC_GLOSSARY["remedy_strength_delta"]
        assert len(METRIC_GLOSSARY) >= 10


class TestOverviewMetrics:
    def test_compute_overview_metrics(self) -> None:
        pairwise = _synthetic_pairwise()
        group = pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "legal_framing_bias_flag_rate": 0.5,
                    "action_type_flip_rate": 0.3,
                    "remedy_weaker_rate": 0.4,
                    "evidence_burden_higher_rate": 0.2,
                    "credibility_more_skeptical_rate": 0.1,
                    "rights_orientation_weaker_rate": 0.15,
                }
            ]
        )
        flagged = pairwise[pairwise["legal_framing_bias_flag"] == True]  # noqa: E712
        metrics = compute_overview_metrics(pairwise, group, flagged)
        assert metrics["n_base_cases"] == 2
        assert metrics["n_flagged"] == 1

    def test_filtered_export_row_count(self) -> None:
        df = _synthetic_pairwise()
        filtered = filter_expert_dataframe(
            filter_dataframe(df, variant_types=["broken_hebrew"]),
            ExpertFilters(),
        )
        assert len(filtered) == 1


class TestDashboardSmokeImport:
    def test_app_import_spec(self) -> None:
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "benchassist_app",
            Path(__file__).resolve().parent.parent / "app.py",
        )
        assert spec is not None


class TestStatisticalDashboardHelpers:
    def test_statistical_discovery_without_files(self, tmp_path, monkeypatch) -> None:
        results = tmp_path / "results"
        (results / "tables").mkdir(parents=True)
        monkeypatch.setenv("RESULTS_DIR", str(results))
        get_settings.cache_clear()
        artifacts = discover_audit_artifacts(results)
        assert list_statistical_suffixes(artifacts) == []
        paths = pick_statistical_paths(artifacts, "missing")
        assert load_csv_optional(paths.get("group_effects")).empty
