"""Load and validate Israeli address proxy-cautious audit variants."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from benchassist.dataset_modes import COUNTERFACTUAL_STRENGTH_PROXY_CAUTIOUS_ADDRESS

DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "address_variants" / "israeli_address_variants.json"
)

APARTMENT_PATTERN = re.compile(
    r"(?:דירה|apt\.?|apartment|#\s*\d|\b\d{1,4}\s*/\s*\d{1,4}\b|\b\d{1,3}\s*,\s*\d{1,3}\b)",
    re.IGNORECASE,
)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


SLIM_ADDRESS_VARIANT_IDS: tuple[str, ...] = (
    "affluent_center_jewish_majority",
    "lower_ses_jewish_periphery",
    "arab_locality_north",
    "mixed_city_arab_neighborhood",
    "neutral_large_city_center",
    "development_town_periphery",
)


def load_address_variants(
    path: Path | None = None,
    *,
    variant_set: str = "balanced",
) -> list[dict[str, Any]]:
    """Load address variant records from registry JSON."""
    registry_path = path or DEFAULT_REGISTRY_PATH
    if not registry_path.exists():
        raise FileNotFoundError(f"Address variant registry not found: {registry_path}")

    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    variants = list(raw.get("variants") or [])
    if variant_set == "slim":
        allowed = set(SLIM_ADDRESS_VARIANT_IDS)
        return [v for v in variants if str(v.get("address_variant_id")) in allowed]
    if variant_set == "balanced":
        return variants
    if variant_set == "all":
        return variants
    allowed = {v.strip() for v in variant_set.split(",") if v.strip()}
    return [v for v in variants if str(v.get("address_variant_id")) in allowed]


def validate_address_variant_record(record: dict[str, Any]) -> list[str]:
    """Return validation warnings for a single address variant."""
    warnings: list[str] = []
    addr = str(record.get("address_text_he") or "")
    if not addr.strip():
        warnings.append("address_text_he is empty")
    if APARTMENT_PATTERN.search(addr):
        warnings.append("address_text_he may contain apartment-like detail")
    if record.get("counterfactual_strength") != COUNTERFACTUAL_STRENGTH_PROXY_CAUTIOUS_ADDRESS:
        warnings.append("counterfactual_strength should be proxy_cautious_address")
    if record.get("use_for_strict_bias_rates") is not False:
        warnings.append("use_for_strict_bias_rates should be false for address proxy variants")
    return warnings


def _clean_optional(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>"}:
        return ""
    return text


def is_address_proxy_row(row: dict[str, Any]) -> bool:
    """Return True if row is an address proxy-cautious variant."""
    if _clean_optional(row.get("protected_attribute_tested")) == "address_proxy":
        return True
    variant_type = _clean_optional(row.get("variant_type"))
    if variant_type.startswith("address_"):
        return True
    if _clean_optional(row.get("address_variant_id")):
        return True
    return _clean_optional(row.get("counterfactual_strength")) == COUNTERFACTUAL_STRENGTH_PROXY_CAUTIOUS_ADDRESS


def is_combined_variant_row(row: dict[str, Any]) -> bool:
    """Return True if row is a combined (demographic+address) intersectional variant."""
    if _clean_optional(row.get("variant_tier")) == "combined":
        return True
    if _clean_optional(row.get("variant_category")) == "intersectional":
        variant_type = _clean_optional(row.get("variant_type"))
        # Combined variants contain city names (not starting with address_)
        if variant_type and not variant_type.startswith("address_") and not is_address_proxy_row(row):
            return True
    return False

