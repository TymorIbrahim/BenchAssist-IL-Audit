"""Tests for language-access counterfactual variants."""

from __future__ import annotations

from collections import Counter

import pytest

from benchassist.data_generation import (
    DEMOGRAPHIC_VARIANT_COUNT,
    INTERSECTIONAL_VARIANT_COUNT,
    LANGUAGE_ACCESS_VARIANT_COUNT,
    LANGUAGE_ACCESS_VARIANTS,
    create_base_cases,
    create_counterfactual_cases,
    write_counterfactual_audit_files,
)
from benchassist.language_access_texts import (
    FORMAL_HEBREW_BY_CASE_ID,
    LAWYER_LIKE_HEBREW_BY_CASE_ID,
    SHORT_VAGUE_HEBREW_BY_CASE_ID,
    SIMPLE_HEBREW_BY_CASE_ID,
)


@pytest.fixture()
def base_cases():
    return create_base_cases()


class TestLanguageAccessVariants:
    def test_language_access_variants_generated(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="language_access"
        )
        assert len(variants) == len(base_cases) * LANGUAGE_ACCESS_VARIANT_COUNT
        types = {v.variant_type for v in variants}
        assert types == {spec.variant_type for spec in LANGUAGE_ACCESS_VARIANTS}

    def test_same_count_per_base_case(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="language_access"
        )
        per_case = Counter(v.case_id for v in variants)
        assert all(count == LANGUAGE_ACCESS_VARIANT_COUNT for count in per_case.values())

    def test_arabic_variants_use_ar_language(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="language_access"
        )
        arabic = [v for v in variants if v.variant_type == "arabic"]
        assert len(arabic) == len(base_cases)
        assert all(v.language == "ar" for v in arabic)

    def test_formal_and_lawyer_not_identical(self) -> None:
        assert FORMAL_HEBREW_BY_CASE_ID["H001"] != LAWYER_LIKE_HEBREW_BY_CASE_ID["H001"]

    def test_simple_and_short_vague_not_identical(self) -> None:
        assert SIMPLE_HEBREW_BY_CASE_ID["H001"] != SHORT_VAGUE_HEBREW_BY_CASE_ID["H001"]

    def test_expected_urgency_preserved(self, base_cases) -> None:
        urgency_by_id = {c.case_id: c.expected_urgency for c in base_cases}
        variants = create_counterfactual_cases(
            base_cases, variant_set="language_access"
        )
        for variant in variants:
            assert variant.expected_urgency == urgency_by_id[variant.case_id]

    def test_expected_direction_preserved(self, base_cases) -> None:
        direction_by_id = {c.case_id: c.expected_direction for c in base_cases}
        variants = create_counterfactual_cases(
            base_cases, variant_set="language_access"
        )
        for variant in variants:
            assert variant.expected_direction == direction_by_id[variant.case_id]

    def test_variant_id_unique(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="all")
        ids = [v.variant_id for v in variants]
        assert len(ids) == len(set(ids))

    def test_variant_set_demographic_excludes_language_only(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="demographic")
        types = {v.variant_type for v in variants}
        assert "formal_hebrew" not in types
        assert "arabic" not in types
        assert "jewish_male_name_he" in types

    def test_variant_set_language_access_excludes_demographic_names(
        self, base_cases
    ) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="language_access"
        )
        types = {v.variant_type for v in variants}
        assert "jewish_male_name_he" not in types
        assert "neutral_he" not in types
        assert "formal_hebrew" in types

    def test_variant_set_all_includes_both(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="all")
        types = {v.variant_type for v in variants}
        assert "jewish_male_name_he" in types
        assert "formal_hebrew" in types
        assert "broken_hebrew" in types
        assert "broken_hebrew_v2" in types
        assert "arab_woman_broken_hebrew" in types
        from benchassist.data_generation import NARRATIVE_FRAMING_VARIANT_COUNT

        assert len(variants) == len(base_cases) * (
            DEMOGRAPHIC_VARIANT_COUNT
            + LANGUAGE_ACCESS_VARIANT_COUNT
            + INTERSECTIONAL_VARIANT_COUNT
            + NARRATIVE_FRAMING_VARIANT_COUNT
        )

    def test_write_optional_exports(self, base_cases, tmp_path) -> None:
        write_counterfactual_audit_files(
            base_cases, audit_dir=tmp_path, variant_set="all"
        )
        assert (tmp_path / "counterfactual_cases.csv").exists()
        assert (tmp_path / "demographic_variants.csv").exists()
        assert (tmp_path / "language_access_variants.csv").exists()

    def test_transformation_style_populated(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="language_access"
        )
        assert all(v.transformation_style for v in variants)
