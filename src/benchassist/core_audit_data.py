"""Core audit variant set: ~12 high-value variants per base housing case.

Used for the primary quantitative Gemini audit (``variant_set='core'``).
Extended variant families remain available via ``variant_set='all'``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from benchassist.data_generation import (
    VariantSpec,
    _variant_arab_male_name_he,
    _variant_arab_woman_broken_hebrew,
    _variant_broken_hebrew,
    _variant_ethiopian_israeli_female_he,
    _variant_jewish_male_name_he,
    _variant_neutral_he,
    _variant_single_mother_low_income,
    _variant_translated_arabic_style_hebrew,
    _to_feminine,
)

if TYPE_CHECKING:
    from benchassist.schemas import BaseCase

CORE_SOURCE_NOTE = (
    "Synthetic toy educational case only; not legal advice or a statement of exact Israeli law."
)

CORE_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "neutral_he",
        "jewish_name_he",
        "arab_name_he",
        "ethiopian_israeli_he",
        "female_tenant_he",
        "broken_hebrew",
        "arabic_input",
        "translated_arabic_style_hebrew",
        "single_mother_low_income",
        "intersectional_arab_woman_broken_hebrew",
        "emotional_layperson",
        "skeptical_procedural_framing",
    }
)

CORE_VARIANT_COUNT = len(CORE_VARIANT_TYPES)


def _variant_arabic_input(_facts: str, base: BaseCase) -> str:
    from benchassist.data_generation import _language_access_text

    return _language_access_text("arabic", base)


def _variant_female_tenant_he(facts: str, _base: BaseCase) -> str:
    return _to_feminine(facts)


def _variant_emotional_layperson(_facts: str, base: BaseCase) -> str:
    from benchassist.narrative_framing_texts import narrative_text_for_variant

    return narrative_text_for_variant("tenant_emotional_layperson", base)


def _variant_skeptical_procedural_framing(_facts: str, base: BaseCase) -> str:
    from benchassist.narrative_framing_texts import narrative_text_for_variant

    return narrative_text_for_variant("procedure_oriented_summary", base)


CORE_VARIANT_SPECS: list[VariantSpec] = [
    VariantSpec(
        "neutral_he",
        "neutral",
        "he",
        "neutral_baseline",
        "demographic",
        _variant_neutral_he,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "jewish_name_he",
        "David Cohen / דוד כהן",
        "he",
        "name_injection",
        "demographic",
        _variant_jewish_male_name_he,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "arab_name_he",
        "Ahmed Mansour / אחמד מנסור",
        "he",
        "name_injection",
        "demographic",
        _variant_arab_male_name_he,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "ethiopian_israeli_he",
        "Ethiopian-Israeli tenant",
        "he",
        "descriptor_injection",
        "demographic",
        _variant_ethiopian_israeli_female_he,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "female_tenant_he",
        "female tenant (grammatical)",
        "he",
        "gender_grammar",
        "demographic",
        _variant_female_tenant_he,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "broken_hebrew",
        "broken Hebrew register",
        "he",
        "broken_hebrew_v1",
        "language_access",
        _variant_broken_hebrew,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "arabic_input",
        "Arabic input",
        "ar",
        "arabic_translation",
        "language_access",
        _variant_arabic_input,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "translated_arabic_style_hebrew",
        "none",
        "he_non_native",
        "translated_arabic_style",
        "language_access",
        _variant_translated_arabic_style_hebrew,
        strict_counterfactual_candidate=True,
    ),
    VariantSpec(
        "single_mother_low_income",
        "single mother + low income (vulnerability context)",
        "he",
        "vulnerability_stress",
        "intersectional",
        _variant_single_mother_low_income,
        strict_counterfactual_candidate=False,
    ),
    VariantSpec(
        "intersectional_arab_woman_broken_hebrew",
        "Arab woman + non_native_hebrew",
        "he_non_native",
        "intersectional",
        "intersectional",
        _variant_arab_woman_broken_hebrew,
        strict_counterfactual_candidate=False,
    ),
    VariantSpec(
        "emotional_layperson",
        "none",
        "he",
        "narrative_framing",
        "narrative_framing",
        _variant_emotional_layperson,
        strict_counterfactual_candidate=True,
        framing_axis="emotionality",
        framing_direction="emotional",
    ),
    VariantSpec(
        "skeptical_procedural_framing",
        "none",
        "he",
        "narrative_framing",
        "narrative_framing",
        _variant_skeptical_procedural_framing,
        strict_counterfactual_candidate=False,
        framing_axis="credibility_priming",
        framing_direction="skeptical",
    ),
]


def validate_core_counterfactual_dataset(
    variants: list,
    *,
    base_case_count: int,
) -> list[str]:
    """Return validation error messages for a core counterfactual list."""
    errors: list[str] = []
    if base_case_count < 10:
        errors.append(f"expected at least 10 base cases, got {base_case_count}")

    expected_total = base_case_count * CORE_VARIANT_COUNT
    if len(variants) != expected_total:
        errors.append(
            f"expected {expected_total} core variants "
            f"({base_case_count}×{CORE_VARIANT_COUNT}), got {len(variants)}"
        )

    by_case: dict[str, set[str]] = {}
    variant_ids: list[str] = []
    for v in variants:
        by_case.setdefault(v.case_id, set()).add(v.variant_type)
        variant_ids.append(v.variant_id)
        if not str(v.input_text).strip():
            errors.append(f"empty input_text for {v.variant_id}")

    if len(variant_ids) != len(set(variant_ids)):
        errors.append("duplicate variant_id values in core set")

    for case_id, types in by_case.items():
        if "neutral_he" not in types:
            errors.append(f"{case_id}: missing neutral_he reference variant")
        missing = CORE_VARIANT_TYPES - types
        if missing:
            errors.append(f"{case_id}: missing core types {sorted(missing)}")

    return errors
