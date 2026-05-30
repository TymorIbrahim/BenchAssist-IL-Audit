"""Tests for intersectional counterfactual variants."""

from __future__ import annotations

from collections import Counter

import pytest

from benchassist.data_generation import (
    DEMOGRAPHIC_VARIANT_COUNT,
    INTERSECTIONAL_VARIANT_COUNT,
    INTERSECTIONAL_VARIANTS,
    LANGUAGE_ACCESS_VARIANT_COUNT,
    create_base_cases,
    create_counterfactual_cases,
    write_counterfactual_audit_files,
)


@pytest.fixture()
def base_cases():
    return create_base_cases()


BROKEN_HE_NON_NATIVE_TYPES = {
    "arab_woman_broken_hebrew",
    "foreign_worker_broken_hebrew",
    "disabled_tenant_broken_hebrew",
    "russian_speaking_elderly_immigrant",
}


class TestIntersectionalVariants:
    def test_intersectional_variants_generated(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        assert len(variants) == len(base_cases) * INTERSECTIONAL_VARIANT_COUNT
        types = {v.variant_type for v in variants}
        assert types == {spec.variant_type for spec in INTERSECTIONAL_VARIANTS}

    def test_same_count_per_base_case(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        per_case = Counter(v.case_id for v in variants)
        assert all(
            count == INTERSECTIONAL_VARIANT_COUNT for count in per_case.values()
        )

    def test_variant_set_intersectional_excludes_demographic_only(
        self, base_cases
    ) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        types = {v.variant_type for v in variants}
        assert "jewish_male_name_he" not in types
        assert "neutral_he" not in types

    def test_variant_set_intersectional_excludes_language_access_only(
        self, base_cases
    ) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        types = {v.variant_type for v in variants}
        assert "formal_hebrew" not in types
        assert "lawyer_like_hebrew" not in types

    def test_variant_set_all_includes_all_families(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="all")
        types = {v.variant_type for v in variants}
        assert "jewish_male_name_he" in types
        assert "formal_hebrew" in types
        assert "arab_woman_broken_hebrew" in types
        from benchassist.data_generation import NARRATIVE_FRAMING_VARIANT_COUNT

        assert len(variants) == len(base_cases) * (
            DEMOGRAPHIC_VARIANT_COUNT
            + LANGUAGE_ACCESS_VARIANT_COUNT
            + INTERSECTIONAL_VARIANT_COUNT
            + NARRATIVE_FRAMING_VARIANT_COUNT
        )

    def test_expected_urgency_preserved(self, base_cases) -> None:
        urgency_by_id = {c.case_id: c.expected_urgency for c in base_cases}
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        for variant in variants:
            assert variant.expected_urgency == urgency_by_id[variant.case_id]

    def test_expected_direction_preserved(self, base_cases) -> None:
        direction_by_id = {c.case_id: c.expected_direction for c in base_cases}
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        for variant in variants:
            assert variant.expected_direction == direction_by_id[variant.case_id]

    def test_variant_id_unique(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="all")
        ids = [v.variant_id for v in variants]
        assert len(ids) == len(set(ids))

    def test_arabic_intersectional_has_ar_language(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        arabic = [v for v in variants if v.variant_type == "arabic_input_arab_woman"]
        assert len(arabic) == len(base_cases)
        assert all(v.language == "ar" for v in arabic)

    def test_broken_hebrew_intersectional_uses_he_non_native(
        self, base_cases
    ) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        broken = [
            v for v in variants if v.variant_type in BROKEN_HE_NON_NATIVE_TYPES
        ]
        assert broken
        assert all(v.language == "he_non_native" for v in broken)

    def test_no_empty_input_text(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        for variant in variants:
            assert variant.input_text.strip()

    def test_transformation_style_is_intersectional(self, base_cases) -> None:
        variants = create_counterfactual_cases(
            base_cases, variant_set="intersectional"
        )
        assert all(v.transformation_style.startswith("intersectional") for v in variants)

    def test_write_intersectional_export(self, base_cases, tmp_path) -> None:
        write_counterfactual_audit_files(
            base_cases, audit_dir=tmp_path, variant_set="intersectional"
        )
        assert (tmp_path / "counterfactual_cases.csv").exists()
        assert (tmp_path / "intersectional_variants.csv").exists()
