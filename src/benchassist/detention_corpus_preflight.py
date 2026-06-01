"""Validate synthetic detention corpus before a Gemini run (no API calls)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from benchassist.address_variants import is_address_proxy_row
from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.detention_corpus_quality import check_hebrew_structured_field_drift, validate_address_registry
from benchassist.detention_schema import SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2, is_minimal_dangerousness_schema


def _load_dataset_hints(config_path: Path | None) -> dict[str, Any]:
    if not config_path or not config_path.exists():
        return {}
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    dataset = raw.get("dataset") or {}
    return {
        "variant_set": dataset.get("variant_set"),
        "max_base_cases": raw.get("max_synthetic_base_cases") or dataset.get("max_base_cases"),
        "schema_version": raw.get("schema_version"),
    }


def validate_synthetic_corpus(
    csv_path: Path,
    *,
    config_path: Path | None = None,
    require_address_proxy: bool = False,
) -> dict[str, Any]:
    """Return {passed, checks, counts} for synthetic CSV readiness."""
    checks: list[dict[str, Any]] = []
    all_ok = True
    hints = _load_dataset_hints(config_path)

    def add(name: str, ok: bool, detail: str, **extra: Any) -> None:
        nonlocal all_ok
        if not ok:
            all_ok = False
        checks.append({"name": name, "ok": ok, "detail": detail, **extra})

    add("file_exists", csv_path.exists() and csv_path.stat().st_size > 0, str(csv_path))
    if not csv_path.exists():
        return {"passed": False, "checks": checks, "counts": {}}

    df = pd.read_csv(csv_path)
    rows = df.to_dict(orient="records")
    bases = sorted({str(r.get("base_case_id")) for r in rows if r.get("base_case_id")})

    add("has_rows", len(rows) > 0, f"{len(rows)} rows")
    add("has_base_case_id", "base_case_id" in df.columns, "base_case_id column present")
    add("has_variant_id", "variant_id" in df.columns, "variant_id column present")
    add("has_prompt_input", "prompt_input" in df.columns, "prompt_input column present")

    neutral_missing: list[str] = []
    for base in bases:
        sub = [r for r in rows if str(r.get("base_case_id")) == base]
        if not any(str(r.get("variant_type")) == "neutral_he" for r in sub):
            neutral_missing.append(base)
    add(
        "neutral_per_base",
        not neutral_missing,
        f"missing neutral_he for {len(neutral_missing)} bases" if neutral_missing else "neutral_he present for all bases",
        missing_bases=neutral_missing[:5],
    )

    address_rows = [r for r in rows if is_address_proxy_row(r)]
    add(
        "address_proxy_rows",
        len(address_rows) > 0 if require_address_proxy else True,
        f"{len(address_rows)} address-proxy rows",
    )
    add(
        "address_proxy_strict_excluded",
        all(exclude_from_strict_bias(r) for r in address_rows) if address_rows else True,
        "address-proxy rows excluded from strict rates",
    )

    strict_eligible = [r for r in rows if not exclude_from_strict_bias(r)]
    add("strict_eligible_rows", len(strict_eligible) > 0, f"{len(strict_eligible)} strict-eligible rows")

    max_bases = hints.get("max_base_cases")
    if max_bases is not None:
        try:
            max_bases = int(max_bases)
            add(
                "max_base_cases_hint",
                len(bases) <= max_bases,
                f"{len(bases)} base cases in file (config max_base_cases={max_bases})",
            )
        except (TypeError, ValueError):
            pass

    schema_hint = hints.get("schema_version")
    if schema_hint:
        add(
            "config_schema_minimal",
            is_minimal_dangerousness_schema(str(schema_hint)),
            f"config schema_version={schema_hint} (expected {SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2} for slim minimal runs)",
        )

    hebrew_drift = check_hebrew_structured_field_drift(csv_path)
    add(
        "hebrew_structured_field_drift",
        hebrew_drift["passed"],
        f"{hebrew_drift.get('failed_count', 0)} bases with marker drift (sampled)",
    )

    address_registry = validate_address_registry()
    add(
        "address_variant_registry",
        address_registry["passed"],
        f"{address_registry['variant_count']} variants · {len(address_registry.get('issues') or [])} issues",
        issues=(address_registry.get("issues") or [])[:3],
    )

    counts = {
        "row_count": len(rows),
        "base_case_count": len(bases),
        "variant_count": df["variant_id"].nunique() if "variant_id" in df.columns else 0,
        "strict_eligible_count": len(strict_eligible),
        "strict_excluded_count": len(rows) - len(strict_eligible),
        "address_proxy_count": len(address_rows),
    }
    return {"passed": all_ok, "checks": checks, "counts": counts, "csv_path": str(csv_path)}
