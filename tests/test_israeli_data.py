"""Tests for optional Israeli legal dataset helpers (no network)."""

from __future__ import annotations

import pandas as pd

from benchassist.israeli_data import (
    HOUSING_KEYWORDS,
    build_base_cases_from_legal_training_il,
    convert_record_to_base_case,
    export_sample_to_csv,
    filter_housing_like_examples,
    filter_records_by_legal_areas,
    infer_legal_area,
    load_legal_training_il_sample,
    parse_legal_areas_arg,
    record_text,
)


class TestRecordTextAndFilter:
    def test_record_text_joins_string_fields(self) -> None:
        record = {"instruction": "שאלה", "output": "תשובה על שכירות"}
        assert "שכירות" in record_text(record)

    def test_filter_housing_like_examples(self) -> None:
        records = [
            {"text": "עניין פלילי כללי"},
            {"text": "סכסוך שכירות בדירה בחיפה"},
            {"text": "חוזה מסחרי"},
        ]
        filtered = filter_housing_like_examples(records)
        assert len(filtered) == 1
        assert "שכירות" in record_text(filtered[0])

    def test_filter_empty_list(self) -> None:
        assert filter_housing_like_examples([]) == []

    def test_housing_keywords_are_hebrew(self) -> None:
        assert "שכירות" in HOUSING_KEYWORDS
        assert "דיור" in HOUSING_KEYWORDS

    def test_infer_legal_area(self) -> None:
        assert infer_legal_area("סכסוך שכירות בדירה") == "housing"
        assert infer_legal_area("תביעת פיטורים ושכר עובד") == "labor"
        assert infer_legal_area("עניין כללי ללא מילות מפתח") == "general"

    def test_filter_records_by_legal_areas(self) -> None:
        records = [
            {"text": "פיטורים ושכר עובד"},
            {"text": "שכירות דירה"},
        ]
        labor = filter_records_by_legal_areas(records, ("labor",))
        assert len(labor) == 1

    def test_parse_legal_areas_arg(self) -> None:
        assert parse_legal_areas_arg("housing, labor") == ("housing", "labor")
        assert parse_legal_areas_arg(None) is None


class TestExportSample:
    def test_export_sample_to_csv(self, tmp_path) -> None:
        records = [
            {"instruction": "שאלה", "output": "תשובה"},
            {"instruction": "עוד", "output": "דירה ופינוי"},
        ]
        path = export_sample_to_csv(records, path=tmp_path / "sample.csv")
        assert path.exists()
        df = pd.read_csv(path)
        assert len(df) == 2

    def test_export_empty_writes_csv(self, tmp_path) -> None:
        path = export_sample_to_csv([], path=tmp_path / "empty.csv")
        assert path.exists()


class TestConvertToBaseCase:
    def test_convert_record_to_base_case(self) -> None:
        record = {
            "instruction": "מהן הסוגיות המשפטיות?",
            "input": "הדייר מתגורר בדירה שכורה בחיפה. " * 20,
            "output": "ניתוח קצר",
        }
        case = convert_record_to_base_case(record, 1)
        assert case.case_id == "IL-HF-0001"
        assert case.legal_area == "housing"
        assert len(case.base_facts_he) >= 150

    def test_extract_facts_from_instruction_when_input_empty(self) -> None:
        record = {
            "instruction": (
                "מהם הסוגיות המשפטיות העיקריות בפסק דין זה? "
                + "הדייר מתגורר בדירה שכורה בחיפה. " * 30
            ),
            "input": "",
            "output": "קצר",
        }
        case = convert_record_to_base_case(record, 2)
        assert "דירה שכורה" in case.base_facts_he

    def test_build_base_cases_from_mocked_pool(self, monkeypatch) -> None:
        pool = [
            {
                "instruction": f"שאלה {i}",
                "input": f"סכסוך שכירות בדירה בירושלים מקרה {i}. " * 25,
                "output": "",
            }
            for i in range(5)
        ]

        def fake_load(limit: int):
            return pool[:limit]

        monkeypatch.setattr(
            "benchassist.israeli_data.load_legal_training_il_sample",
            fake_load,
        )
        cases = build_base_cases_from_legal_training_il(
            target_count=3, fetch_limit=5, housing_only=True
        )
        assert len(cases) == 3
        assert all(c.case_id.startswith("IL-HF-") for c in cases)

    def test_build_multi_area_pool(self, monkeypatch) -> None:
        pool = [
            {
                "instruction": "שאלה",
                "input": f"פיטורים ושכר עובד במפעל מקרה {i}. " * 25,
                "output": "",
            }
            for i in range(3)
        ] + [
            {
                "instruction": "שאלה",
                "input": f"שכירות דירה בירושלים מקרה {i}. " * 25,
                "output": "",
            }
            for i in range(3)
        ]

        monkeypatch.setattr(
            "benchassist.israeli_data.load_legal_training_il_sample",
            lambda limit: pool[:limit],
        )
        cases = build_base_cases_from_legal_training_il(
            target_count=4,
            fetch_limit=10,
            housing_only=False,
            legal_areas=("housing", "labor"),
            stratify_by_area=True,
        )
        areas = {c.legal_area for c in cases}
        assert "housing" in areas
        assert "labor" in areas


class TestLoadWithoutDatasetsPackage:
    def test_load_raises_import_error_without_datasets(self, monkeypatch) -> None:
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "datasets":
                raise ImportError("no datasets")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        try:
            load_legal_training_il_sample(limit=5)
            raised = False
        except ImportError as exc:
            raised = True
            assert "datasets" in str(exc).lower()
        assert raised
