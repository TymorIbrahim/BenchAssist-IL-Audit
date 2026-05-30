"""Dataset mode constants for synthetic vs real-case-inspired audit layers."""

from __future__ import annotations

DATASET_MODE_SYNTHETIC = "synthetic_controlled"
DATASET_MODE_SYNTHETIC_COUNTERFACTUAL = "synthetic_counterfactual"
DATASET_MODE_REAL = "real_case_inspired"
DATASET_MODE_HYBRID = "hybrid"

DATASET_MODES: tuple[str, ...] = (
    DATASET_MODE_SYNTHETIC,
    DATASET_MODE_SYNTHETIC_COUNTERFACTUAL,
    DATASET_MODE_REAL,
    DATASET_MODE_HYBRID,
)

COUNTERFACTUAL_STRENGTH_STRICT = "strict"
COUNTERFACTUAL_STRENGTH_APPROXIMATE = "approximate"
COUNTERFACTUAL_STRENGTH_STRESS = "stress_test"
COUNTERFACTUAL_STRENGTH_NONE = "not_counterfactual"

COUNTERFACTUAL_STRENGTHS: tuple[str, ...] = (
    COUNTERFACTUAL_STRENGTH_STRICT,
    COUNTERFACTUAL_STRENGTH_APPROXIMATE,
    COUNTERFACTUAL_STRENGTH_STRESS,
    COUNTERFACTUAL_STRENGTH_NONE,
)

REAL_CASE_SOURCE_DATASET = "BrainboxAI/legal-training-il"
REAL_CASE_LICENSE_NOTE = (
    "Public/licensed training-evaluation material (Legal-Training-IL). "
    "Not authoritative legal advice. Preserve attribution; human legal review required."
)
REAL_CASE_ATTRIBUTION = "Derived from Legal-Training-IL (BrainboxAI) where applicable."

DEFAULT_REAL_CASE_LIMITATIONS = (
    "Real-case-inspired summaries are source-derived and may be imperfect. "
    "They support realism and domain coverage testing, not strict counterfactual fairness proof. "
    "Not legal advice. Not proof of discrimination."
)

# Variants excluded from strict synthetic demographic fairness rates
NARRATIVE_PROXY_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "low_income_neighborhood_proxy",
        "intersectional_arab_young_male_broken_hebrew",
        "skeptical_police_framing",
        "defense_framing",
        "skeptical_procedural_framing",
        "emotional_layperson",
        "single_mother_low_income",
        "intersectional_arab_woman_broken_hebrew",
    }
)


def parse_bool(value: object, default: bool = False) -> bool:
    """Parse booleans from CSV/JSON mixed types."""
    if value is None or (isinstance(value, float) and str(value) == "nan"):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    return default


def is_real_case_row(row: dict[str, object]) -> bool:
    """Return True if row belongs to the real-case-inspired layer."""
    mode = str(row.get("dataset_mode", DATASET_MODE_SYNTHETIC) or DATASET_MODE_SYNTHETIC)
    if mode == DATASET_MODE_REAL:
        return True
    if parse_bool(row.get("is_real_case_inspired")):
        return True
    return False


def _clean_str(value: object) -> str:
    """Normalize optional string fields; treat pandas NaN as empty."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>"}:
        return ""
    return text


def exclude_from_strict_bias(row: dict[str, object]) -> bool:
    """Whether a row should be excluded from strict synthetic bias rates."""
    if is_real_case_row(row):
        return True
    if not parse_bool(row.get("use_for_strict_bias_rates"), default=True):
        return True
    if parse_bool(row.get("exclude_from_strict_bias_rates")):
        return True

    variant = _clean_str(row.get("variant_type"))
    if variant in NARRATIVE_PROXY_VARIANT_TYPES:
        return True
    if "strict_counterfactual_candidate" in row and not parse_bool(
        row.get("strict_counterfactual_candidate"), default=True
    ):
        return True

    strength = _clean_str(row.get("counterfactual_strength"))
    if strength == COUNTERFACTUAL_STRENGTH_NONE:
        return True
    if strength in {COUNTERFACTUAL_STRENGTH_APPROXIMATE, COUNTERFACTUAL_STRENGTH_STRESS}:
        return True

    mode = _clean_str(row.get("dataset_mode")) or DATASET_MODE_SYNTHETIC
    if mode == DATASET_MODE_REAL:
        return True
    if mode == DATASET_MODE_SYNTHETIC_COUNTERFACTUAL:
        if strength and strength != COUNTERFACTUAL_STRENGTH_STRICT:
            return True

    if variant in {"real_case_original", "real_original"}:
        return True
    return False
