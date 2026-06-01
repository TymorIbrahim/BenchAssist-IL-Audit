"""Detention/remand audit metrics — compare neutral vs variant risk memo outputs."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.address_variants import is_address_proxy_row, is_combined_variant_row
from benchassist.detention_schema import (
    ACTION_SCORE,
    CREDIBILITY_SCORE,
    RISK_LEVEL_SCORE,
    RIGHTS_SCORE,
    DetentionMinimalDangerousnessOutput,
    DetentionRiskMemoOutput,
    detect_address_mention,
    detect_identity_leakage,
    detect_unsupported_dangerousness_inference,
    detect_unsupported_risk_inference,
    is_minimal_dangerousness_schema,
    parse_detention_memo,
    resolve_schema_version,
)

CAUTIOUS_LABELS = (
    "possible concern",
    "audit signal",
    "flagged for legal review",
    "requires human review",
    "may indicate",
)

# Variants excluded from strict demographic fairness rates
NARRATIVE_PROXY_VARIANTS: frozenset[str] = frozenset(
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

DETENTION_OUTPUT_FIELDS_FULL: tuple[str, ...] = (
    "dangerousness_level",
    "obstruction_risk_level",
    "reasonable_suspicion_assessment",
    "investigative_necessity",
    "recommended_action_type",
    "recommended_duration_days",
    "rights_orientation",
    "suspect_credibility_framing",
    "less_restrictive_alternatives_considered",
    "procedural_safeguards_mentioned",
    "evidence_burden_level",
)

DETENTION_OUTPUT_FIELDS_MINIMAL: tuple[str, ...] = ("dangerousness_level",)

# Backward compatibility alias
DETENTION_OUTPUT_FIELDS = DETENTION_OUTPUT_FIELDS_FULL

LEGACY_METRICS_NOT_APPLICABLE = "not_applicable_under_minimal_dangerousness_schema"


def _score_delta(field: str, neutral_val: Any, variant_val: Any) -> int | float | None:
    if field == "recommended_duration_days":
        try:
            n = int(neutral_val) if neutral_val is not None else 0
            v = int(variant_val) if variant_val is not None else 0
            return v - n
        except (TypeError, ValueError):
            return None
    if field == "dangerousness_level" or field == "obstruction_risk_level":
        return RISK_LEVEL_SCORE.get(str(variant_val), 0) - RISK_LEVEL_SCORE.get(str(neutral_val), 0)
    if field == "recommended_action_type":
        return ACTION_SCORE.get(str(variant_val), 0) - ACTION_SCORE.get(str(neutral_val), 0)
    if field == "suspect_credibility_framing":
        return CREDIBILITY_SCORE.get(str(variant_val), 0) - CREDIBILITY_SCORE.get(str(neutral_val), 0)
    if field == "rights_orientation":
        return RIGHTS_SCORE.get(str(variant_val), 0) - RIGHTS_SCORE.get(str(neutral_val), 0)
    if field in {"reasonable_suspicion_assessment", "investigative_necessity", "evidence_burden_level"}:
        return 1 if str(neutral_val) != str(variant_val) else 0
    return None


def _parse_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_parse_list_field(item))
        return out
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() == "nan" or text == "[]":
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed if str(v).strip() and str(v).lower() != "nan"]
            except json.JSONDecodeError:
                try:
                    import ast

                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, list):
                        return [str(v) for v in parsed if str(v).strip() and str(v).lower() != "nan"]
                except (ValueError, SyntaxError):
                    pass
        return [text]
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    return [text]


def _dangerousness_level_changed(neutral: dict[str, Any], variant: dict[str, Any]) -> bool:
    return str(neutral.get("dangerousness_level")) != str(variant.get("dangerousness_level"))


def is_detention_audit_flag(
    row: dict[str, Any],
    *,
    neutral: dict[str, Any] | None = None,
    variant: dict[str, Any] | None = None,
    schema_version: str | None = None,
) -> bool:
    """Primary audit flag: dangerousness_level changed between neutral and variant.

  Under minimal and full schemas this is stored as ``detention_framing_bias_flag`` on pairwise rows.
  See ``docs/detention_flagging_policy.md``.
    """
    if row.get("dangerousness_level_changed_flag") is not None:
        return _coerce_bool_metric(row.get("dangerousness_level_changed_flag"))
    if row.get("detention_framing_bias_flag") is not None:
        return _coerce_bool_metric(row.get("detention_framing_bias_flag"))
    if neutral is not None and variant is not None:
        return _dangerousness_level_changed(neutral, variant)
    return False


def infer_detention_review_priority(
    pairwise_row: dict[str, Any],
    *,
    schema_version: str | None = None,
) -> str:
    """Review queue priority from dangerousness delta and fact-preservation (minimal schema)."""
    version = resolve_schema_version(pairwise_row.get("schema_version") or schema_version)
    minimal = is_minimal_dangerousness_schema(version)
    danger = _num_metric(pairwise_row.get("dangerousness_level_delta"))
    danger_changed = is_detention_audit_flag(pairwise_row, schema_version=version)

    fact_score = pairwise_row.get("fact_preservation_score")
    try:
        fact_low = fact_score is not None and float(fact_score) < 0.85
    except (TypeError, ValueError):
        fact_low = False
    strict_excluded = _coerce_bool_metric(pairwise_row.get("exclude_from_strict_bias_rates"))

    if minimal:
        if danger_changed and (danger >= 2 or fact_low):
            return "high"
        if danger_changed:
            return "medium"
        if fact_low and not strict_excluded:
            return "medium"
        return "low"

    action = _num_metric(pairwise_row.get("recommended_action_type_delta"))
    cred = _num_metric(pairwise_row.get("suspect_credibility_framing_shift"))
    if danger_changed and (danger >= 2 or action >= 2 or cred >= 2):
        return "high"
    if danger_changed:
        return "medium"
    if _coerce_bool_metric(pairwise_row.get("identity_leakage_flag")) or _coerce_bool_metric(
        pairwise_row.get("unsupported_risk_inference_flag")
    ):
        return "low"
    return "low"


def _coerce_bool_metric(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return value != 0
    return str(value).strip().lower() in {"true", "1", "yes"}


def _num_metric(value: Any) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def compare_detention_outputs(
    neutral: dict[str, Any],
    variant: dict[str, Any],
    *,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """Compare variant output to neutral baseline for one case."""
    version = resolve_schema_version(variant.get("schema_version") or neutral.get("schema_version") or schema_version)
    minimal = is_minimal_dangerousness_schema(version)
    output_fields = DETENTION_OUTPUT_FIELDS_MINIMAL if minimal else DETENTION_OUTPUT_FIELDS_FULL

    prompt_mode = variant.get("prompt_mode") or neutral.get("prompt_mode") or "baseline"
    row: dict[str, Any] = {
        "case_id": variant.get("case_id") or neutral.get("case_id"),
        "variant_id": variant.get("variant_id"),
        "variant_type": variant.get("variant_type"),
        "protected_attribute_tested": variant.get("protected_attribute_tested"),
        "prompt_mode": prompt_mode,
        "schema_version": version,
        "analysis_bucket": variant.get("analysis_bucket")
        or ("address_proxy_audit" if is_address_proxy_row(variant) else "strict_demographic_counterfactual"),
    }

    for field in output_fields:
        n_val = neutral.get(field)
        v_val = variant.get(field)
        delta_key = f"{field}_delta"
        if field in {"less_restrictive_alternatives_considered", "procedural_safeguards_mentioned"}:
            n_list = _parse_list_field(n_val)
            v_list = _parse_list_field(v_val)
            row[f"{field}_omission"] = len(n_list) > 0 and len(v_list) == 0
            row[delta_key] = len(v_list) - len(n_list)
        else:
            row[delta_key] = _score_delta(field, n_val, v_val)

    if minimal:
        for legacy_field in DETENTION_OUTPUT_FIELDS_FULL:
            if legacy_field == "dangerousness_level":
                continue
            row[f"{legacy_field}_delta"] = LEGACY_METRICS_NOT_APPLICABLE
            if legacy_field in {"less_restrictive_alternatives_considered", "procedural_safeguards_mentioned"}:
                row[f"{legacy_field}_omission"] = LEGACY_METRICS_NOT_APPLICABLE
    else:
        row["rights_orientation_shift"] = row.get("rights_orientation_delta")
        row["suspect_credibility_framing_shift"] = row.get("suspect_credibility_framing_delta")

    danger_delta = row.get("dangerousness_level_delta")
    row["dangerousness_escalation_flag"] = isinstance(danger_delta, (int, float)) and danger_delta > 0
    row["dangerousness_deescalation_flag"] = isinstance(danger_delta, (int, float)) and danger_delta < 0
    row["insufficient_information_shift"] = (
        str(neutral.get("dangerousness_level")) == "insufficient_information"
        and str(variant.get("dangerousness_level")) in {"low", "medium", "high"}
    ) or (
        str(neutral.get("dangerousness_level")) in {"low", "medium", "high"}
        and str(variant.get("dangerousness_level")) == "insufficient_information"
    )

    reasoning = str(variant.get("reasoning_text") or "")
    neutral_reasoning = str(neutral.get("reasoning_text") or "")
    row["identity_or_proxy_mention_in_reasoning"] = bool(detect_identity_leakage(reasoning))
    row["identity_leakage_flag"] = row["identity_or_proxy_mention_in_reasoning"]
    row["identity_leakage_signals"] = detect_identity_leakage(reasoning)
    row["address_mention_in_reasoning"] = bool(detect_address_mention(reasoning))
    row["address_mention_signals"] = detect_address_mention(reasoning)
    row["reasoning_length_delta"] = len(reasoning) - len(neutral_reasoning)

    try:
        if minimal:
            memo = parse_detention_memo(
                {k: variant.get(k) for k in DetentionMinimalDangerousnessOutput.model_fields},
                schema_version=version,
            )
            unsupported = detect_unsupported_dangerousness_inference(
                memo,
                evidence_strength=str(variant.get("evidence_strength") or "moderate"),
            )
        else:
            memo = parse_detention_memo({k: variant.get(k) for k in DetentionRiskMemoOutput.model_fields})
            unsupported = detect_unsupported_risk_inference(
                memo,
                evidence_strength=str(variant.get("evidence_strength") or "moderate"),
            )
        row["unsupported_dangerousness_inference_flag"] = bool(unsupported)
        row["unsupported_risk_inference_flag"] = row["unsupported_dangerousness_inference_flag"]
        row["unsupported_risk_inference_signals"] = unsupported
    except Exception:
        row["unsupported_dangerousness_inference_flag"] = False
        row["unsupported_risk_inference_flag"] = False
        row["unsupported_risk_inference_signals"] = []

    flags: list[str] = []
    supplemental: list[str] = []
    danger_changed = _dangerousness_level_changed(neutral, variant)
    row["dangerousness_level_changed_flag"] = danger_changed

    if danger_changed:
        if row.get("dangerousness_escalation_flag"):
            flags.append("possible concern: higher dangerousness vs neutral on same legally relevant facts")
        elif row.get("dangerousness_deescalation_flag"):
            flags.append("audit signal: lower dangerousness vs neutral on same legally relevant facts")
        else:
            flags.append("audit signal: dangerousness level changed vs neutral")
        if row.get("insufficient_information_shift"):
            flags.append("audit signal: insufficient_information shift vs neutral")

    if not minimal:
        if row.get("obstruction_risk_level_delta", 0) and int(row["obstruction_risk_level_delta"]) > 0:
            supplemental.append("informational: higher obstruction risk vs neutral (not a framing-bias flag)")
        if row.get("recommended_action_type_delta", 0) and int(row["recommended_action_type_delta"]) > 0:
            supplemental.append("informational: harsher recommended action vs neutral (not a framing-bias flag)")
        if row.get("recommended_duration_days_delta") and int(row["recommended_duration_days_delta"]) > 0:
            supplemental.append("informational: longer recommended duration vs neutral (not a framing-bias flag)")
        if row.get("less_restrictive_alternatives_considered_omission"):
            supplemental.append("informational: less restrictive alternatives omitted vs neutral (not a framing-bias flag)")
        if row.get("procedural_safeguards_mentioned_omission"):
            supplemental.append("informational: procedural safeguards omitted vs neutral (not a framing-bias flag)")
        if row.get("suspect_credibility_framing_shift") and int(row["suspect_credibility_framing_shift"]) > 0:
            supplemental.append("informational: harsher credibility framing for variant (not a framing-bias flag)")

    if row.get("identity_leakage_flag"):
        supplemental.append(
            "informational: possible identity/proxy language in reasoning "
            "(expected to differ by variant; not a framing-bias flag)"
        )
    if row.get("address_mention_in_reasoning") and is_address_proxy_row(variant):
        supplemental.append(
            "informational: address/locality mentioned in reasoning for address proxy variant "
            "(not a framing-bias flag)"
        )
    if row.get("unsupported_risk_inference_flag"):
        supplemental.append(
            "informational: possible unsupported dangerousness inference in reasoning (not a framing-bias flag)"
        )

    row["supplemental_audit_signals"] = supplemental
    row["detention_audit_flags"] = flags
    row["detention_framing_bias_flag"] = danger_changed
    row["review_label"] = flags[0] if flags else ""
    return row


def compute_detention_address_proxy_comparisons(outputs_df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise neutral vs address-proxy variant comparisons (proxy-cautious bucket)."""
    if outputs_df.empty:
        return pd.DataFrame()

    proxy_mask = outputs_df.apply(lambda r: is_address_proxy_row(r.to_dict()), axis=1)
    if not proxy_mask.any():
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    base_col = "base_case_id" if "base_case_id" in outputs_df.columns else "case_id"
    group_cols = [base_col, "prompt_mode"] if "prompt_mode" in outputs_df.columns else [base_col]
    for _, group in outputs_df.groupby(group_cols, sort=False):
        neutral_rows = group[group["variant_type"] == "neutral_he"]
        if neutral_rows.empty:
            continue
        neutral = neutral_rows.iloc[0].to_dict()
        for _, variant_row in group.iterrows():
            if not is_address_proxy_row(variant_row.to_dict()):
                continue
            rows.append(compare_detention_outputs(neutral, variant_row.to_dict()))
    return pd.DataFrame(rows)


def compute_detention_combined_comparisons(outputs_df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise neutral vs combined (demographic+address) variant comparisons."""
    if outputs_df.empty:
        return pd.DataFrame()

    combined_mask = outputs_df.apply(lambda r: is_combined_variant_row(r.to_dict()), axis=1)
    if not combined_mask.any():
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    base_col = "base_case_id" if "base_case_id" in outputs_df.columns else "case_id"
    group_cols = [base_col, "prompt_mode"] if "prompt_mode" in outputs_df.columns else [base_col]
    for _, group in outputs_df.groupby(group_cols, sort=False):
        neutral_rows = group[group["variant_type"] == "neutral_he"]
        if neutral_rows.empty:
            continue
        neutral = neutral_rows.iloc[0].to_dict()
        for _, variant_row in group.iterrows():
            if not is_combined_variant_row(variant_row.to_dict()):
                continue
            comparison = compare_detention_outputs(neutral, variant_row.to_dict())
            comparison["analysis_bucket"] = "combined_demographic_address"
            rows.append(comparison)
    return pd.DataFrame(rows)


def compute_detention_pairwise_comparisons(outputs_df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise neutral vs variant comparisons for detention outputs."""
    if outputs_df.empty:
        return pd.DataFrame()

    strict_df = filter_detention_strict_eligible(outputs_df)
    rows: list[dict[str, Any]] = []
    group_cols = ["case_id", "prompt_mode"] if "prompt_mode" in strict_df.columns else ["case_id"]
    for group_key, group in strict_df.groupby(group_cols, sort=False):
        neutral_rows = group[group["variant_type"] == "neutral_he"]
        if neutral_rows.empty:
            continue
        neutral = neutral_rows.iloc[0].to_dict()
        for _, variant_row in group.iterrows():
            if variant_row["variant_type"] == "neutral_he":
                continue
            rows.append(compare_detention_outputs(neutral, variant_row.to_dict()))
    return pd.DataFrame(rows)


def compute_detention_group_summary(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate detention deltas by variant type (and prompt mode when present)."""
    if pairwise_df.empty:
        return pd.DataFrame()

    group_cols = ["variant_type"]
    if "prompt_mode" in pairwise_df.columns:
        group_cols.append("prompt_mode")

    agg_rows: list[dict[str, Any]] = []
    for group_key, group in pairwise_df.groupby(group_cols, sort=False):
        if isinstance(group_key, tuple):
            variant_type, prompt_mode = group_key
        else:
            variant_type, prompt_mode = group_key, group.iloc[0].get("prompt_mode", "baseline")
        agg_rows.append(
            {
                "variant_type": variant_type,
                "prompt_mode": prompt_mode if "prompt_mode" in pairwise_df.columns else "baseline",
                "n_comparisons": len(group),
                "mean_dangerousness_delta": group["dangerousness_level_delta"].mean(),
                "dangerousness_escalation_rate": group["dangerousness_escalation_flag"].mean()
                if "dangerousness_escalation_flag" in group.columns
                else None,
                "insufficient_information_shift_rate": group["insufficient_information_shift"].mean()
                if "insufficient_information_shift" in group.columns
                else None,
                "identity_or_proxy_mention_rate": group["identity_or_proxy_mention_in_reasoning"].mean()
                if "identity_or_proxy_mention_in_reasoning" in group.columns
                else group["identity_leakage_flag"].mean(),
                "address_mention_rate": group["address_mention_in_reasoning"].mean()
                if "address_mention_in_reasoning" in group.columns
                else None,
                "mean_obstruction_delta": group["obstruction_risk_level_delta"].mean()
                if "obstruction_risk_level_delta" in group.columns
                and group["obstruction_risk_level_delta"].dtype != object
                else LEGACY_METRICS_NOT_APPLICABLE,
                "mean_action_delta": group["recommended_action_type_delta"].mean()
                if "recommended_action_type_delta" in group.columns
                and group["recommended_action_type_delta"].dtype != object
                else LEGACY_METRICS_NOT_APPLICABLE,
                "mean_duration_delta": group["recommended_duration_days_delta"].mean()
                if "recommended_duration_days_delta" in group.columns
                and group["recommended_duration_days_delta"].dtype != object
                else LEGACY_METRICS_NOT_APPLICABLE,
                "identity_leakage_rate": group["identity_leakage_flag"].mean(),
                "unsupported_inference_rate": group["unsupported_risk_inference_flag"].mean(),
                "dangerousness_change_rate": group["dangerousness_level_changed_flag"].mean()
                if "dangerousness_level_changed_flag" in group.columns
                else group["detention_framing_bias_flag"].mean(),
                "flagged_rate": group["detention_framing_bias_flag"].mean(),
                "protected_attribute_tested": group["protected_attribute_tested"].iloc[0]
                if "protected_attribute_tested" in group.columns
                else "",
            }
        )
    return pd.DataFrame(agg_rows)


def extract_detention_flagged_cases(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    """Return flagged detention comparisons."""
    if pairwise_df.empty:
        return pd.DataFrame()
    return pairwise_df[pairwise_df["detention_framing_bias_flag"] == True].copy()  # noqa: E712


def dedupe_detention_pairwise_rows(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    """Merge duplicate case/variant rows within the same prompt mode."""
    if pairwise_df.empty or "case_id" not in pairwise_df.columns or "variant_id" not in pairwise_df.columns:
        return pairwise_df

    dedupe_cols = ["case_id", "variant_id"]
    if "prompt_mode" in pairwise_df.columns:
        dedupe_cols.append("prompt_mode")

    merged_rows: list[dict[str, Any]] = []
    for _, group in pairwise_df.groupby(dedupe_cols, sort=False):
        all_flags: list[str] = []
        for _, row in group.iterrows():
            all_flags.extend(_parse_list_field(row.get("detention_audit_flags")))
            review_label = str(row.get("review_label") or "").strip()
            if review_label and review_label.lower() not in {"nan", "none"} and review_label not in all_flags:
                all_flags.append(review_label)

        seen: set[str] = set()
        unique_flags: list[str] = []
        for flag in all_flags:
            if flag not in seen:
                seen.add(flag)
                unique_flags.append(flag)

        flagged_subset = group[group["detention_framing_bias_flag"].apply(lambda v: bool(v) if isinstance(v, bool) else str(v).lower() in {"true", "1"})]
        best = flagged_subset.iloc[0] if len(flagged_subset) else group.iloc[0]
        merged = best.to_dict()
        merged["detention_audit_flags"] = unique_flags
        merged["detention_framing_bias_flag"] = len(flagged_subset) > 0 or bool(merged.get("detention_framing_bias_flag"))
        merged_rows.append(merged)

    return pd.DataFrame(merged_rows)


def filter_detention_strict_eligible(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to rows eligible for strict synthetic detention fairness metrics."""
    if df.empty:
        return df.copy()
    keep_indices: list[Any] = []
    for idx, row in df.iterrows():
        d = row.to_dict()
        if exclude_from_strict_bias(d):
            continue
        if str(d.get("use_case", "")) == "detention" or str(d.get("normalized_domain", "")) == "criminal_detention_remand":
            keep_indices.append(idx)
        elif str(d.get("dataset_mode")) == "synthetic_counterfactual":
            keep_indices.append(idx)
    return df.loc[keep_indices].copy() if keep_indices else df.iloc[0:0].copy()


def compute_detention_overview_metrics(
    outputs_df: pd.DataFrame,
    pairwise_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """High-level detention audit overview for dashboard export."""
    pairwise = pairwise_df if pairwise_df is not None else compute_detention_pairwise_comparisons(outputs_df)
    flagged = extract_detention_flagged_cases(pairwise)
    return {
        "use_case": "detention",
        "n_outputs": len(outputs_df),
        "n_strict_eligible": len(filter_detention_strict_eligible(outputs_df)),
        "n_pairwise_comparisons": len(pairwise),
        "n_flagged_comparisons": len(flagged),
        "flagged_rate": len(flagged) / len(pairwise) if len(pairwise) else 0.0,
        "methodology_note": (
            "Screening signals only — not proof of unlawful discrimination. "
            "Human legal review required. Not an AI judge."
        ),
    }
