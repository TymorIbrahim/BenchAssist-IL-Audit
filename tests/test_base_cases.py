"""Tests for the housing base-case dataset (create_base_cases)."""

from __future__ import annotations

from benchassist.data_generation import create_base_cases
from benchassist.schemas import BaseCase


class TestCreateBaseCases:
    """Validate the 12 housing base cases."""

    def test_exactly_12_base_cases(self) -> None:
        """create_base_cases() must return exactly 12 BaseCase objects."""
        cases = create_base_cases()
        assert len(cases) == 12
        assert all(isinstance(c, BaseCase) for c in cases)

    def test_all_case_ids_unique(self) -> None:
        """Every case_id must be unique."""
        cases = create_base_cases()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids)), f"Duplicate case IDs: {ids}"

    def test_all_urgency_values_valid(self) -> None:
        """expected_urgency must be one of 'low', 'medium', 'high'."""
        valid = {"low", "medium", "high"}
        cases = create_base_cases()
        for case in cases:
            assert case.expected_urgency in valid, (
                f"{case.case_id}: invalid urgency {case.expected_urgency!r}"
            )

    def test_every_hebrew_summary_non_empty(self) -> None:
        """base_facts_he must be a non-empty string for every case."""
        cases = create_base_cases()
        for case in cases:
            assert isinstance(case.base_facts_he, str), (
                f"{case.case_id}: base_facts_he is not a string"
            )
            assert len(case.base_facts_he.strip()) > 0, (
                f"{case.case_id}: base_facts_he is empty"
            )

    def test_all_legal_area_is_housing(self) -> None:
        """All base cases should have legal_area == 'housing'."""
        cases = create_base_cases()
        for case in cases:
            assert case.legal_area == "housing", (
                f"{case.case_id}: expected housing, got {case.legal_area!r}"
            )

    def test_source_note_present(self) -> None:
        """All cases must have a non-empty source_note."""
        cases = create_base_cases()
        for case in cases:
            assert len(case.source_note.strip()) > 0
