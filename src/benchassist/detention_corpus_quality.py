"""Corpus quality checks: Hebrew drift heuristics, address registry validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.address_variants import (
    DEFAULT_REGISTRY_PATH,
    load_address_variants,
    validate_address_variant_record,
)

# Legal-fact field labels we expect stable between neutral and strict variants.
STRUCTURED_FIELD_MARKERS = (
    "סוג הליך",
    "עבירה חשודה",
    "חוזק ראיות",
    "עבר פלילי",
    "נשק",
    "בקשת המשטרה",
)


def check_hebrew_structured_field_drift(
    csv_path: Path,
    *,
    sample_bases: int = 10,
) -> dict[str, Any]:
    """Flag bases where structured Hebrew labels disappear between neutral and a strict variant."""
    df = pd.read_csv(csv_path)
    checks: list[dict[str, Any]] = []
    bases = sorted(df["base_case_id"].dropna().unique())[:sample_bases]
    for base in bases:
        sub = df[df["base_case_id"] == base]
        neutral = sub[sub["variant_type"] == "neutral_he"]
        if neutral.empty:
            checks.append({"base_case_id": base, "ok": False, "detail": "missing neutral_he"})
            continue
        n_text = str(neutral.iloc[0].get("prompt_input") or "")
        n_markers = sum(1 for m in STRUCTURED_FIELD_MARKERS if m in n_text)
        worst = n_markers
        for _, row in sub.iterrows():
            if str(row.get("variant_type")) == "neutral_he":
                continue
            if str(row.get("exclude_from_strict_bias_rates")).lower() in {"true", "1"}:
                continue
            v_text = str(row.get("prompt_input") or "")
            v_markers = sum(1 for m in STRUCTURED_FIELD_MARKERS if m in v_text)
            worst = min(worst, v_markers)
        ok = worst >= max(1, n_markers - 1)
        checks.append(
            {
                "base_case_id": base,
                "ok": ok,
                "detail": f"neutral_markers={n_markers}, min_strict_variant_markers={worst}",
            }
        )
    failed = [c for c in checks if not c["ok"]]
    return {"passed": not failed, "checks": checks, "failed_count": len(failed)}


def validate_address_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or DEFAULT_REGISTRY_PATH
    variants = load_address_variants(registry_path, variant_set="all")
    issues: list[dict[str, str]] = []
    email_phone = re.compile(r"[\w.+-]+@[\w-]+\.\w+|0\d{1,2}[- ]?\d{7}")
    for rec in variants:
        vid = str(rec.get("address_variant_id"))
        for w in validate_address_variant_record(rec):
            issues.append({"address_variant_id": vid, "issue": w})
        addr = str(rec.get("address_text_he") or "")
        if email_phone.search(addr):
            issues.append({"address_variant_id": vid, "issue": "possible PII pattern in address text"})
    return {
        "passed": not issues,
        "registry_path": str(registry_path),
        "variant_count": len(variants),
        "issues": issues[:50],
    }
