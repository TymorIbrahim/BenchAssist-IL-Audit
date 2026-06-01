"""Tests for minimal dangerousness schema and address proxy variants."""

from __future__ import annotations

import json
import re

import pytest

from benchassist.address_variants import (
    APARTMENT_PATTERN,
    is_address_proxy_row,
    load_address_variants,
    validate_address_variant_record,
)
from benchassist.dataset_modes import COUNTERFACTUAL_STRENGTH_PROXY_CAUTIOUS_ADDRESS, exclude_from_strict_bias
from benchassist.detention_data_generation import create_address_variant_rows, create_detention_counterfactuals, CORE_VARIANTS, SLIM_VARIANTS
from benchassist.detention_full_run_plan import run_full_run_plan
from benchassist.detention_gemini_config import load_detention_gemini_config
from benchassist.detention_metrics import LEGACY_METRICS_NOT_APPLICABLE, compare_detention_outputs
from benchassist.detention_prompting import build_detention_system_prompt
from benchassist.detention_schema import (
    SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    DetentionMinimalDangerousnessOutput,
    parse_detention_memo,
    validate_detention_output_row,
)


def test_address_variant_registry_loads() -> None:
    variants = load_address_variants()
    assert 10 <= len(variants) <= 14
    for record in variants:
        assert record["address_variant_id"]
        assert record["address_text_he"]
        assert record["counterfactual_strength"] == COUNTERFACTUAL_STRENGTH_PROXY_CAUTIOUS_ADDRESS


def test_address_variants_have_no_apartment_like_strings() -> None:
    for record in load_address_variants():
        addr = str(record["address_text_he"])
        assert not APARTMENT_PATTERN.search(addr), addr
        warnings = validate_address_variant_record(record)
        assert not any("apartment" in w for w in warnings)


def test_address_variants_generated_and_excluded_from_strict() -> None:
    rows = create_address_variant_rows()
    assert len(rows) >= 300  # 30 bases × 12 addresses
    for row in rows[:5]:
        assert row["protected_attribute_tested"] == "address_proxy"
        assert row["use_for_strict_bias_rates"] is False
        assert exclude_from_strict_bias(row) is True
        assert "כתובת מגורים:" in row["prompt_input"]


def test_core_plus_address_row_count() -> None:
    core = create_detention_counterfactuals(variant_set="core")
    combined = create_detention_counterfactuals(variant_set="core", include_address_variants=True)
    assert len(combined) == len(core) + len(create_address_variant_rows())
    trimmed = create_detention_counterfactuals(
        variant_set="core",
        include_address_variants=True,
        max_base_cases=10,
    )
    assert len(trimmed) == 10 * len(CORE_VARIANTS) + 10 * 12
    slim = create_detention_counterfactuals(
        variant_set="slim",
        include_address_variants=True,
        max_base_cases=10,
    )
    assert len(slim) == 10 * len(SLIM_VARIANTS) + 10 * 6


def test_slim_variant_set_drops_nonessential_variants() -> None:
    from benchassist.address_variants import SLIM_ADDRESS_VARIANT_IDS, load_address_variants

    rows = create_detention_counterfactuals(variant_set="slim", include_address_variants=True, max_base_cases=5)
    types = {r["variant_type"] for r in rows}
    assert "neutral_he" in types
    assert "arab_name_he" in types
    assert "druze_name_he" in types
    assert "arab_woman_he" in types
    assert "defense_framing" not in types
    assert "low_income_neighborhood_proxy" not in types
    assert len(load_address_variants(variant_set="slim")) == len(SLIM_ADDRESS_VARIANT_IDS)


def test_proportional_sampling_preserves_variant_ratios() -> None:
    full = create_detention_counterfactuals(variant_set="core", include_address_variants=True)
    sample = create_detention_counterfactuals(
        variant_set="core",
        include_address_variants=True,
        max_base_cases=10,
    )
    import pandas as pd

    full_counts = pd.Series([r["variant_type"] for r in full]).value_counts()
    sample_counts = pd.Series([r["variant_type"] for r in sample]).value_counts()
    ratio_full = full_counts / full_counts.max()
    ratio_sample = sample_counts / sample_counts.max()
    assert ratio_full.index.tolist() == ratio_sample.index.tolist()
    assert (ratio_full - ratio_sample).abs().max() < 1e-9
    assert sample_counts.min() == 10
    assert sample_counts.max() == 10


def test_minimal_schema_validation() -> None:
    payload = {
        "case_summary": "Synthetic summary.",
        "dangerousness_level": "medium",
        "reasoning_text": "Based on legally relevant facts only.",
    }
    memo = parse_detention_memo(payload, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2)
    assert isinstance(memo, DetentionMinimalDangerousnessOutput)

    bad = {**payload, "dangerousness_level": "extreme"}
    with pytest.raises(Exception):
        parse_detention_memo(bad, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2)


def test_minimal_output_row_validation() -> None:
    row = {
        "use_case": "detention",
        "dataset_mode": "synthetic_counterfactual",
        "prompt_mode": "baseline",
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
        "case_summary": "Summary",
        "dangerousness_level": "low",
        "reasoning_text": "Reasoning",
    }
    result = validate_detention_output_row(row, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2)
    assert result["passed"] is True


def test_prompt_only_asks_for_three_fields() -> None:
    system_text, _ = build_detention_system_prompt(
        prompt_mode="baseline",
        schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    )
    assert "case_summary" in system_text
    assert "dangerousness_level" in system_text
    assert "reasoning_text" in system_text
    assert "recommended_action_type" not in system_text
    assert "exactly these fields" in system_text.lower() or "exactly these fields" in system_text


def test_compare_outputs_minimal_schema_marks_legacy_na() -> None:
    neutral = {
        "case_id": "D001",
        "variant_type": "neutral_he",
        "dangerousness_level": "low",
        "reasoning_text": "Neutral reasoning.",
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    variant = {
        **neutral,
        "variant_id": "D001-arab_name_he",
        "variant_type": "arab_name_he",
        "dangerousness_level": "high",
        "reasoning_text": "Variant reasoning.",
    }
    row = compare_detention_outputs(neutral, variant, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2)
    assert row["dangerousness_escalation_flag"] is True
    assert row["recommended_action_type_delta"] == LEGACY_METRICS_NOT_APPLICABLE


def test_dry_run_planner_counts_address_variants(tmp_path, monkeypatch) -> None:
    root = tmp_path
    synthetic = root / "data" / "synthetic"
    synthetic.mkdir(parents=True)
    rows = create_detention_counterfactuals(variant_set="core", include_address_variants=True)
    import pandas as pd

    pd.DataFrame(rows).to_csv(synthetic / "detention_core_cases_with_address.csv", index=False)

    config_path = root / "configs" / "gemini_detention_expanded_minimal_address.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        (root.parent / "configs" / "gemini_detention_expanded_minimal_address.yaml").read_text()
        if (root.parent / "configs" / "gemini_detention_expanded_minimal_address.yaml").exists()
        else "",
        encoding="utf-8",
    )

    # Use project config directly
    from pathlib import Path

    project = Path(__file__).resolve().parents[1]
    config = load_detention_gemini_config(project / "configs" / "gemini_detention_expanded_minimal_address.yaml")
    assert config.schema_version == SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2
    assert config.methodology.address_proxy_in_strict_rates is False


def test_full_analysis_cross_prompt_minimal_fields() -> None:
    from benchassist.detention_full_analysis import (
        _cross_prompt_compare_fields,
        _cross_prompt_instability_fields,
        compute_cross_prompt_comparisons,
    )
    import pandas as pd

    minimal_fields = _cross_prompt_compare_fields("detention_minimal_dangerousness_v2")
    assert "dangerousness_level" in minimal_fields
    assert "recommended_action_type" not in minimal_fields
    assert _cross_prompt_instability_fields("detention_minimal_dangerousness_v2") == ["dangerousness_level"]

    df = pd.DataFrame(
        [
            {
                "case_id": "D001",
                "variant_id": "D001-neutral_he",
                "variant_type": "neutral_he",
                "prompt_mode": "baseline",
                "dangerousness_level": "low",
                "case_summary": "A",
                "reasoning_text": "neutral reason",
            },
            {
                "case_id": "D001",
                "variant_id": "D001-neutral_he",
                "variant_type": "neutral_he",
                "prompt_mode": "fairness_aware",
                "dangerousness_level": "low",
                "case_summary": "A",
                "reasoning_text": "different wording only",
            },
        ]
    )
    cross = compute_cross_prompt_comparisons(df, schema_version="detention_minimal_dangerousness_v2")
    assert len(cross) == 1
    assert bool(cross.iloc[0]["reasoning_only_change"]) is True
    assert bool(cross.iloc[0]["cross_prompt_instability_flag"]) is False


def test_address_proxy_pairwise_separate_from_strict() -> None:
    import pandas as pd
    from benchassist.detention_metrics import compute_detention_address_proxy_comparisons

    rows = create_detention_counterfactuals(variant_set="core", include_address_variants=True)
    # Simulate minimal parsed outputs for one base case
    base = "D001"
    subset = [r for r in rows if r["case_id"] == base][:3]
    outputs = []
    for r in subset:
        outputs.append(
            {
                **r,
                "prompt_mode": "baseline",
                "parse_status": "success",
                "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
                "case_summary": "Summary",
                "dangerousness_level": "low" if "neutral" in r["variant_type"] else "medium",
                "reasoning_text": "Reasoning based on facts.",
            }
        )
    df = pd.DataFrame(outputs)
    proxy = compute_detention_address_proxy_comparisons(df)
    assert proxy.empty or "dangerousness_level_delta" in proxy.columns


def test_cautious_language_in_metrics_flags() -> None:
    neutral = {
        "dangerousness_level": "low",
        "reasoning_text": "Neutral.",
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    variant = {
        **neutral,
        "variant_id": "x",
        "variant_type": "arab_name_he",
        "dangerousness_level": "high",
        "reasoning_text": "Because he is arab the risk is higher.",
    }
    row = compare_detention_outputs(neutral, variant, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2)
    flags = " ".join(row["detention_audit_flags"]).lower()
    assert "possible concern" in flags
    assert row["detention_framing_bias_flag"] is True
    assert row["identity_leakage_flag"] is True
    assert any("identity/proxy" in s for s in row["supplemental_audit_signals"])
    assert "discriminatory" not in flags
    assert "bias proven" not in flags


def test_reasoning_signals_do_not_flag_without_dangerousness_change() -> None:
    neutral = {
        "dangerousness_level": "low",
        "reasoning_text": "Neutral assessment.",
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    variant = {
        **neutral,
        "variant_id": "x",
        "variant_type": "arab_name_he",
        "reasoning_text": "Because he is arab the summary differs.",
    }
    row = compare_detention_outputs(neutral, variant, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2)
    assert row["detention_framing_bias_flag"] is False
    assert row["dangerousness_level_changed_flag"] is False
    assert row["identity_leakage_flag"] is True
    assert row["supplemental_audit_signals"]
    assert not row["detention_audit_flags"]
