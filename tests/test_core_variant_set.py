"""Tests for the core audit variant set."""

from __future__ import annotations

import pytest

from benchassist.core_audit_data import CORE_VARIANT_COUNT, CORE_VARIANT_TYPES
from benchassist.data_generation import create_base_cases, create_counterfactual_cases


@pytest.fixture
def base_cases():
    return create_base_cases()


class TestCoreVariantSet:
    def test_core_variant_count(self) -> None:
        assert CORE_VARIANT_COUNT == 12
        assert len(CORE_VARIANT_TYPES) == 12

    def test_core_generates_expected_total(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="core")
        assert len(variants) == len(base_cases) * CORE_VARIANT_COUNT

    def test_every_case_has_neutral_he(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="core")
        for case in base_cases:
            neutral = [v for v in variants if v.case_id == case.case_id and v.variant_type == "neutral_he"]
            assert len(neutral) == 1

    def test_core_variant_types_present(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="core")
        present = {v.variant_type for v in variants}
        assert present == CORE_VARIANT_TYPES

    def test_no_empty_input_text(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="core")
        assert all(str(v.input_text).strip() for v in variants)

    def test_unique_variant_ids(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="core")
        ids = [v.variant_id for v in variants]
        assert len(ids) == len(set(ids))
