"""Tests for counterfactual data generation in benchassist.data_generation."""

from __future__ import annotations

import pytest

from benchassist.data_generation import (
    create_counterfactual_variants,
    generate_base_cases,
)
from benchassist.schemas import CaseSummary, CounterfactualPair


# ---------------------------------------------------------------------------
# generate_base_cases tests
# ---------------------------------------------------------------------------


class TestGenerateBaseCases:
    """Tests for the generate_base_cases helper."""

    def test_generate_base_cases_count(self) -> None:
        """generate_base_cases(n) should return exactly n CaseSummary objects."""
        cases = generate_base_cases(5)

        assert len(cases) == 5
        assert all(isinstance(c, CaseSummary) for c in cases)

    def test_generate_base_cases_unique_ids(self) -> None:
        """Every generated case should have a unique case_id."""
        cases = generate_base_cases(15)
        ids = [c.case_id for c in cases]

        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"


# ---------------------------------------------------------------------------
# create_counterfactual_variants tests
# ---------------------------------------------------------------------------


class TestCreateCounterfactualVariants:
    """Tests for counterfactual pair creation."""

    @pytest.fixture()
    def base_cases(self) -> list[CaseSummary]:
        """Generate a small set of base cases for variant testing."""
        return generate_base_cases(5)

    @pytest.fixture()
    def pairs(self, base_cases: list[CaseSummary]) -> list[CounterfactualPair]:
        """Create counterfactual pairs from the base cases."""
        return create_counterfactual_variants(base_cases)

    def test_create_counterfactual_variants(
        self, pairs: list[CounterfactualPair]
    ) -> None:
        """Variants should differ in demographic cues but share description structure."""
        assert len(pairs) > 0, "Expected at least one counterfactual pair"

        for pair in pairs:
            # Both sides should be valid CaseSummary instances
            assert isinstance(pair.base, CaseSummary)
            assert isinstance(pair.variant, CaseSummary)
            # The variant ID is derived from the base ID
            assert pair.variant.case_id.startswith(pair.base.case_id.split("-V")[0])

    def test_counterfactual_preserves_legal_facts(
        self, pairs: list[CounterfactualPair]
    ) -> None:
        """The area_of_law should be identical between base and variant."""
        for pair in pairs:
            assert pair.base.area_of_law == pair.variant.area_of_law, (
                f"area_of_law mismatch for {pair.base.case_id}: "
                f"{pair.base.area_of_law!r} != {pair.variant.area_of_law!r}"
            )

    def test_counterfactual_changes_demographics(
        self, pairs: list[CounterfactualPair]
    ) -> None:
        """At least a demographic_group or party name should differ per pair."""
        for pair in pairs:
            demographics_differ = (
                pair.base.demographic_group != pair.variant.demographic_group
            )
            # Collect party names for a simpler comparison
            base_names = {p.get("name", "") for p in pair.base.parties}
            variant_names = {p.get("name", "") for p in pair.variant.parties}
            names_differ = base_names != variant_names

            language_cues_differ = (
                pair.base.language_cue != pair.variant.language_cue
            )

            assert demographics_differ or names_differ or language_cues_differ, (
                f"No demographic/name/language change detected for pair "
                f"{pair.base.case_id}"
            )
