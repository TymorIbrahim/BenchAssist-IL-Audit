"""Validate base cases and counterfactual audit datasets (offline heuristics)."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings
from benchassist.core_audit_data import CORE_VARIANT_TYPES
from benchassist.data_generation import (
    CORE_AUDIT_VARIANT_COUNT,
    DEMOGRAPHIC_VARIANT_COUNT,
    INTERSECTIONAL_VARIANT_COUNT,
    LANGUAGE_ACCESS_VARIANT_COUNT,
    NARRATIVE_FRAMING_VARIANT_COUNT,
    create_base_cases,
    create_counterfactual_cases,
)
from benchassist.narrative_framing_texts import NARRATIVE_VARIANT_TYPES

PARTY_POWER_VARIANT_TYPES: frozenset[str] = frozenset(
    {"tenant_power_low", "landlord_power_high", "party_power_asymmetry"}
)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def validate_base_cases_df(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    required = {"case_id", "base_facts_he", "expected_urgency", "expected_direction"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"base_cases missing columns: {sorted(missing)}")
    if df.empty:
        errors.append("base_cases is empty")
    if "case_id" in df.columns and df["case_id"].duplicated().any():
        errors.append("duplicate case_id in base_cases")
    if "base_facts_he" in df.columns:
        empty = df["base_facts_he"].astype(str).str.strip() == ""
        if empty.any():
            errors.append(f"empty base_facts_he rows: {int(empty.sum())}")
    return errors


def validate_counterfactual_df(
    df: pd.DataFrame,
    *,
    base_df: pd.DataFrame | None = None,
    expected_variant_types: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    required = {
        "case_id",
        "variant_id",
        "variant_type",
        "input_text",
        "expected_urgency",
        "expected_direction",
    }
    missing = required - set(df.columns)
    if missing:
        errors.append(f"counterfactual_cases missing columns: {sorted(missing)}")
    if df.empty:
        errors.append("counterfactual_cases is empty")
        return errors

    if df["variant_id"].duplicated().any():
        dupes = df[df["variant_id"].duplicated(keep=False)]["variant_id"].unique()[:5]
        errors.append(f"duplicate variant_id values (sample): {list(dupes)}")

    empty_text = df["input_text"].astype(str).str.strip() == ""
    if empty_text.any():
        errors.append(f"empty input_text rows: {int(empty_text.sum())}")

    party_power = set(df["variant_type"].astype(str)) & PARTY_POWER_VARIANT_TYPES
    if party_power:
        errors.append(f"unexpected party_power variants present: {sorted(party_power)}")

    if expected_variant_types:
        present = set(df["variant_type"].astype(str))
        missing_types = expected_variant_types - present
        if missing_types:
            errors.append(
                f"missing expected variant types ({len(missing_types)}): "
                f"{sorted(missing_types)[:8]}..."
            )

    if base_df is not None and not base_df.empty:
        base_urgency = base_df.set_index("case_id")["expected_urgency"].to_dict()
        base_direction = base_df.set_index("case_id")["expected_direction"].to_dict()
        for _, row in df.iterrows():
            cid = row.get("case_id")
            if cid not in base_urgency:
                continue
            if row.get("expected_urgency") != base_urgency[cid]:
                errors.append(f"expected_urgency mismatch for {row.get('variant_id')}")
                break
            if row.get("expected_direction") != base_direction[cid]:
                errors.append(f"expected_direction mismatch for {row.get('variant_id')}")
                break

    return errors


def validate_audit_files(
    *,
    data_dir: Path | None = None,
    variant_set: str | None = None,
) -> dict[str, Any]:
    """Validate on-disk audit artefacts and return a summary dict."""
    settings = get_settings()
    root = data_dir or settings.DATA_DIR
    processed = root / "processed"
    audit = root / "audit"

    summary: dict[str, Any] = {
        "paths": {},
        "errors": [],
        "warnings": [],
        "counts": {},
    }

    base_path = processed / "base_cases.csv"
    cf_path = audit / "counterfactual_cases.csv"
    summary["paths"]["base_cases"] = str(base_path)
    summary["paths"]["counterfactual_cases"] = str(cf_path)

    if not base_path.exists():
        summary["errors"].append(f"missing {base_path}")
        return summary

    base_df = _read_csv(base_path)
    summary["errors"].extend(validate_base_cases_df(base_df))
    summary["counts"]["base_cases"] = len(base_df)

    optional_exports = {
        "demographic_variants.csv": DEMOGRAPHIC_VARIANT_COUNT,
        "language_access_variants.csv": LANGUAGE_ACCESS_VARIANT_COUNT,
        "intersectional_variants.csv": INTERSECTIONAL_VARIANT_COUNT,
        "narrative_framing_variants.csv": NARRATIVE_FRAMING_VARIANT_COUNT,
    }

    for name, per_case in optional_exports.items():
        path = audit / name
        summary["paths"][name] = str(path)
        if path.exists():
            df = _read_csv(path)
            summary["counts"][name] = len(df)
            if len(base_df) > 0 and len(df) % len(base_df) != 0:
                summary["warnings"].append(
                    f"{name}: row count {len(df)} not divisible by base cases {len(base_df)}"
                )
        else:
            summary["warnings"].append(f"optional export not found: {path}")

    if not cf_path.exists():
        summary["errors"].append(f"missing {cf_path}")
        return summary

    cf_df = _read_csv(cf_path)
    summary["counts"]["counterfactual_cases"] = len(cf_df)
    summary["counts"]["variant_types"] = dict(Counter(cf_df["variant_type"].astype(str)))

    expected_types: set[str] | None = None
    if variant_set == "narrative_framing":
        expected_types = set(NARRATIVE_VARIANT_TYPES)
    elif variant_set == "core":
        expected_types = set(CORE_VARIANT_TYPES)
    elif variant_set == "all":
        live = create_counterfactual_cases(create_base_cases(), variant_set="all")
        expected_types = {v.variant_type for v in live}

    summary["errors"].extend(
        validate_counterfactual_df(
            cf_df, base_df=base_df, expected_variant_types=expected_types
        )
    )

    if variant_set == "core" and not summary["errors"]:
        n_base = len(base_df)
        expected_total = n_base * CORE_AUDIT_VARIANT_COUNT
        if len(cf_df) != expected_total:
            summary["warnings"].append(
                f"counterfactual count {len(cf_df)} != expected core-set {expected_total}"
            )

    if variant_set == "all" and not summary["errors"]:
        n_base = len(base_df)
        expected_total = n_base * (
            DEMOGRAPHIC_VARIANT_COUNT
            + LANGUAGE_ACCESS_VARIANT_COUNT
            + INTERSECTIONAL_VARIANT_COUNT
            + NARRATIVE_FRAMING_VARIANT_COUNT
        )
        if len(cf_df) != expected_total:
            summary["warnings"].append(
                f"counterfactual count {len(cf_df)} != expected all-set {expected_total}"
            )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate BenchAssist-IL audit datasets.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Data root (default: DATA_DIR from settings).",
    )
    parser.add_argument(
        "--variant-set",
        default=None,
        choices=[
            "demographic",
            "language_access",
            "intersectional",
            "narrative_framing",
            "core",
            "all",
        ],
        help="Optional expected variant family check against counterfactual_cases.csv.",
    )
    args = parser.parse_args(argv)

    summary = validate_audit_files(data_dir=args.data_dir, variant_set=args.variant_set)
    print("Validation summary")
    for key, path in summary["paths"].items():
        print(f"  {key}: {path}")
    print(f"  counts: {summary['counts']}")
    for warning in summary["warnings"]:
        print(f"WARNING: {warning}")
    for error in summary["errors"]:
        print(f"ERROR: {error}")

    if summary["errors"]:
        return 1
    print("OK — no blocking validation errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
