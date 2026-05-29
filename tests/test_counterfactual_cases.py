"""Tests for housing counterfactual case generation."""

from __future__ import annotations

from collections import Counter

import pytest

from benchassist.data_generation import (
    create_base_cases,
    create_counterfactual_cases,
    write_counterfactual_audit_files,
)
from benchassist.schemas import CounterfactualCase


@pytest.fixture()
def base_cases():
    return create_base_cases()


@pytest.fixture()
def counterfactual_cases(base_cases):
    return create_counterfactual_cases(base_cases)


class TestCreateCounterfactualCases:
    def test_total_counterfactual_count(self, counterfactual_cases) -> None:
        assert len(counterfactual_cases) == 120

    def test_each_base_case_has_ten_variants(
        self, base_cases, counterfactual_cases
    ) -> None:
        per_case = Counter(v.case_id for v in counterfactual_cases)
        assert len(per_case) == len(base_cases)
        for case_id in (c.case_id for c in base_cases):
            assert per_case[case_id] == 10

    def test_expected_urgency_matches_base(
        self, base_cases, counterfactual_cases
    ) -> None:
        urgency_by_id = {c.case_id: c.expected_urgency for c in base_cases}
        for variant in counterfactual_cases:
            assert variant.expected_urgency == urgency_by_id[variant.case_id]

    def test_expected_direction_matches_base(
        self, base_cases, counterfactual_cases
    ) -> None:
        direction_by_id = {c.case_id: c.expected_direction for c in base_cases}
        for variant in counterfactual_cases:
            assert variant.expected_direction == direction_by_id[variant.case_id]

    def test_every_variant_has_non_empty_input_text(
        self, counterfactual_cases
    ) -> None:
        for variant in counterfactual_cases:
            assert isinstance(variant.input_text, str)
            assert len(variant.input_text.strip()) > 0

    def test_variant_id_unique(self, counterfactual_cases) -> None:
        ids = [v.variant_id for v in counterfactual_cases]
        assert len(ids) == len(set(ids))

    def test_all_instances_are_counterfactual_case(
        self, counterfactual_cases
    ) -> None:
        assert all(isinstance(v, CounterfactualCase) for v in counterfactual_cases)

    def test_requested_remedy_preserved_in_input_text(
        self, base_cases, counterfactual_cases
    ) -> None:
        remedy_by_id = {c.case_id: c.requested_remedy for c in base_cases}
        for variant in counterfactual_cases:
            assert remedy_by_id[variant.case_id] in variant.input_text

    def test_write_audit_files(self, tmp_path) -> None:
        variants = write_counterfactual_audit_files(audit_dir=tmp_path)
        assert len(variants) == 120
        assert (tmp_path / "counterfactual_cases.csv").exists()
        assert (tmp_path / "counterfactual_cases.jsonl").exists()
