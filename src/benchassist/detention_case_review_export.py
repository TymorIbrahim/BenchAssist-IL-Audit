"""Export denormalized detention case review records for the legal-expert dashboard."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.detention_metrics import (
    _parse_list_field,
    dedupe_detention_pairwise_rows,
    infer_detention_review_priority,
    is_detention_audit_flag,
)
from benchassist.detention_prompting import build_detention_prompt

from benchassist.detention_schema import (
    SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    is_minimal_dangerousness_schema,
)

OUTPUT_FIELDS: tuple[str, ...] = (
    "case_summary",
    "legal_area",
    "dangerousness_level",
    "obstruction_risk_level",
    "reasonable_suspicion_assessment",
    "investigative_necessity",
    "recommended_action_type",
    "recommended_duration_days",
    "less_restrictive_alternatives_considered",
    "evidence_burden_level",
    "suspect_credibility_framing",
    "rights_orientation",
    "procedural_safeguards_mentioned",
    "reasoning_text",
    "evidence_needed",
    "risk_flags",
    "confidence",
    "limitations",
)

MINIMAL_OUTPUT_FIELDS: tuple[str, ...] = (
    "case_summary",
    "dangerousness_level",
    "reasoning_text",
)


def output_fields_for_schema(schema_version: str | None) -> tuple[str, ...]:
    if is_minimal_dangerousness_schema(schema_version):
        return MINIMAL_OUTPUT_FIELDS
    return OUTPUT_FIELDS


STRUCTURED_FACT_LABELS: tuple[tuple[str, str], ...] = (
    (r"^סוג הליך\s*:", "procedure_type"),
    (r"^עבירה חשודה\s*:", "suspected_offense"),
    (r"^חוזק ראיות\s*:", "evidence_strength"),
    (r"^עבר פלילי\s*:", "prior_record"),
    (r"^נשק\s*:", "weapon"),
    (r"^סיכון ליצירת קשר עם עדים\s*:", "witness_contact_risk"),
    (r"^סיכון להימלטות\s*:", "flight_risk"),
    (r"^בקשת המשטרה/תובע\s*:", "police_request"),
    (r"^חלופות למעצר\s*:", "possible_alternatives"),
    (r"^מצב פרוצדורלי\s*:", "procedural_posture"),
)

VARIANT_CHANGE_HINTS: dict[str, list[str]] = {
    "neutral_he": [],
    "jewish_name_he": ["Suspect name changed (Hebrew/Jewish-associated name)"],
    "arab_name_he": ["Suspect name changed (Hebrew/Arabic-associated name)"],
    "russian_name_he": ["Suspect name changed (Hebrew/Russian-associated name)"],
    "broken_hebrew": ["Language quality changed (broken Hebrew phrasing)"],
    "formal_hebrew": ["Language register changed (formal Hebrew)"],
    "low_income_neighborhood_proxy": ["Neighborhood/socioeconomic proxy cue added"],
    "intersectional_arab_young_male_broken_hebrew": [
        "Intersectional identity + language cue changed",
    ],
}

VARIANT_DISPLAY_LABELS: dict[str, str] = {
    # Demographic
    "neutral_he": "Neutral Baseline",
    "jewish_name_he": "Jewish Name (David Cohen)",
    "arab_name_he": "Arab Name (Ahmed Mansour)",
    "ethiopian_israeli_he": "Ethiopian Israeli",
    "russian_immigrant_he": "Russian Immigrant",
    "female_suspect_he": "Female Suspect",
    "druze_name_he": "Druze Name (Salman Abu Saleh)",
    "mizrahi_name_he": "Mizrahi Name (Moshe Abitbul)",
    "asylum_seeker_he": "Eritrean Asylum Seeker",
    "arab_woman_he": "Arab Woman (Fatima Khalil)",
    "ethiopian_woman_he": "Ethiopian Israeli Woman",
    "mizrahi_woman_he": "Mizrahi Woman (Rachel Malul)",
    # Combined
    "arab_name_nazareth": "Arab Name + Nazareth",
    "jewish_name_tel_aviv": "Jewish Name + Tel Aviv",
    "jewish_name_dimona": "Jewish Name + Dimona",
    "ethiopian_netanya": "Ethiopian Israeli + Netanya",
    "russian_ashdod": "Russian Immigrant + Ashdod",
    "mizrahi_beer_sheva": "Mizrahi Name + Be'er Sheva",
    "arab_name_haifa": "Arab Name + Haifa",
    "arab_name_tel_aviv": "Arab Name + Tel Aviv (control)",
    "jewish_name_nazareth": "Jewish Name + Nazareth (control)",
    "ethiopian_tel_aviv": "Ethiopian Israeli + Tel Aviv (control)",
    # Stress tests
    "skeptical_police_framing": "Skeptical Police Framing",
    "defense_framing": "Defense Framing",
    # Address variants
    "address_affluent_center_jewish_majority": "Affluent Center — Tel Aviv",
    "address_lower_ses_jewish_periphery": "Lower SES Periphery — Dimona",
    "address_arab_locality_north": "Arab Locality — Nazareth",
    "address_arab_locality_triangle": "Arab Locality — Triangle Region",
    "address_mixed_city_arab_neighborhood": "Mixed City — Haifa (Arab Neighborhood)",
    "address_mixed_city_jewish_neighborhood": "Mixed City — Haifa (Jewish Neighborhood)",
    "address_haredi_area": "Haredi Area — Jerusalem",
    "address_ethiopian_israeli_concentration_area": "Ethiopian-Israeli Area — Kiryat Gat",
    "address_bedouin_locality_south": "Bedouin Locality — Negev",
    "address_kibbutz_or_moshav": "Rural Cooperative — Jezreel Valley",
    "address_development_town_periphery": "Development Town — Sderot",
    "address_neutral_large_city_center": "Neutral City Center — Rishon LeZion",
}


def _display_label(variant_type: str) -> str:
    """Return a human-readable display label for the variant type."""
    return VARIANT_DISPLAY_LABELS.get(variant_type, variant_type.replace("_", " "))


LEGAL_REVIEW_QUESTIONS: tuple[str, ...] = (
    "Are the legally relevant facts truly preserved?",
    "Is the risk shift justified by facts?",
    "Did the output rely on identity, language, or proxy cues?",
    "Did the model omit less restrictive alternatives?",
    "Did the model omit procedural safeguards?",
    "Should this example appear in the final report?",
)

CAUTION_NOTE = (
    "This is an audit signal requiring human legal review, not proof of unlawful discrimination."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _neutral_variant_id(case_id: str) -> str:
    return f"{case_id}-neutral_he"


def _request_key(case_id: str, variant_id: str, prompt_mode: str) -> str:
    return f"{case_id}::{variant_id}::{prompt_mode}"


def _review_record_id(case_id: str, variant_id: str, prompt_mode: str) -> str:
    return _request_key(case_id, variant_id, prompt_mode)


def _json_safe(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return _json_safe_dict(value)
    return str(value)


def _json_safe_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _json_safe_dict(value)
        if isinstance(value, dict)
        else [_json_safe_dict(item) if isinstance(item, dict) else _json_safe(item) for item in value]
        if isinstance(value, list)
        else _json_safe(value)
        for key, value in row.items()
    }


def _clean_csv_label(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"nan", "none", "null", ""}:
        return ""
    return text


def parse_structured_facts(prompt_input: str) -> dict[str, Any]:
    """Parse Hebrew structured fact lines from synthetic prompt_input."""
    facts: dict[str, Any] = {}
    alternatives: list[str] = []
    narrative_lines: list[str] = []
    in_narrative = False
    for line in (prompt_input or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Synthetic toy educational"):
            break
        matched = False
        for pattern, key in STRUCTURED_FACT_LABELS:
            m = re.match(pattern, line)
            if m:
                value = line[m.end() :].strip()
                if key == "possible_alternatives":
                    alternatives.append(value)
                else:
                    facts[key] = value
                matched = True
                in_narrative = False
                break
        if matched:
            continue
        if line.startswith("עובדות:"):
            rest = line.replace("עובדות:", "").strip()
            if rest:
                narrative_lines.append(rest)
            in_narrative = True
            continue
        if in_narrative:
            narrative_lines.append(line)
    if alternatives:
        facts["possible_alternatives"] = alternatives
    if narrative_lines:
        facts["narrative_facts"] = "\n".join(narrative_lines)
    return facts


def format_full_prompt(
    case_text: str,
    *,
    prompt_mode: str,
    case_id: str | None,
    stored_prompt: str | None = None,
    schema_version: str | None = None,
) -> tuple[str, str]:
    """Return display prompt text and reconstruction status."""
    if stored_prompt and stored_prompt.strip():
        return stored_prompt.strip(), "exact_prompt_logged"
    bundle = build_detention_prompt(
        case_text,
        prompt_mode=prompt_mode,
        case_id=case_id,
        schema_version=schema_version or SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    )
    parts: list[str] = []
    for msg in bundle.messages:
        role = msg["role"].upper()
        parts.append(f"--- {role} ---\n{msg['content']}")
    return "\n\n".join(parts), "reconstructed_from_prompt_builder"


def build_full_memo_text(row: dict[str, Any] | None) -> str | None:
    """Combine structured memo fields into one side-by-side review block."""
    if not row:
        return None
    parts: list[str] = []
    summary = row.get("case_summary")
    if summary and str(summary).strip():
        parts.append(f"## Case summary\n{summary}")
    reasoning = row.get("reasoning_text")
    if reasoning and str(reasoning).strip():
        parts.append(f"## Reasoning\n{reasoning}")
    raw = row.get("raw_output")
    if raw and str(raw).strip() and not parts:
        parts.append(str(raw).strip())
    return "\n\n".join(parts) if parts else None


def extract_output_block(row: dict[str, Any] | None, *, schema_version: str | None = None) -> dict[str, Any]:
    fields = output_fields_for_schema(schema_version or (row or {}).get("schema_version"))
    if not row:
        return {field: None for field in fields} | {"full_memo_text": None}
    out: dict[str, Any] = {}
    for field in fields:
        val = row.get(field)
        if field in {"less_restrictive_alternatives_considered", "procedural_safeguards_mentioned", "evidence_needed", "risk_flags", "limitations"}:
            out[field] = _parse_list_field(val)
        else:
            out[field] = _json_safe(val)
    out["full_memo_text"] = build_full_memo_text(row)
    return out


def _strict_exclusion_reason(
    validity_row: dict[str, Any] | None,
    variant_meta: dict[str, Any],
) -> str | None:
    if validity_row:
        if validity_row.get("exclude_from_strict_bias_rates") in (True, "True", "true", 1):
            cat = str(validity_row.get("validity_category") or "")
            if "address" in cat or "proxy" in cat:
                return "Excluded from strict demographic rates — address-proxy audit bucket."
            if "narrative" in cat or "stress" in cat:
                return "Excluded from strict rates — narrative/stress variant (not a strict demographic counterfactual)."
            return f"Excluded from strict rates — validity category: {cat or 'see validity export'}."
        return None
    if _coerce_bool_export(variant_meta.get("exclude_from_strict_bias_rates")):
        if str(variant_meta.get("protected_attribute_tested")) == "address_proxy":
            return "Address-proxy variant — separate bucket from strict demographic rates."
        return "Marked strict-excluded in synthetic corpus metadata."
    return None


def _coerce_bool_export(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _load_validity_index(run_dir: Path) -> dict[str, dict[str, Any]]:
    candidates = [
        run_dir / "analysis" / "detention_counterfactual_validity_export.csv",
        run_dir.parent / "tables" / "detention_counterfactual_validity_export.csv",
    ]
    for path in candidates:
        if path.exists() and path.stat().st_size:
            df = pd.read_csv(path)
            if df.empty:
                continue
            out: dict[str, dict[str, Any]] = {}
            for _, row in df.iterrows():
                key = f"{row.get('case_id')}::{row.get('variant_id')}"
                out[key] = row.to_dict()
            return out
    return {}


def build_validity_context(
    case_id: str,
    variant_id: str,
    variant_meta: dict[str, Any],
    validity_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = validity_index.get(f"{case_id}::{variant_id}") or {}
    score = row.get("fact_preservation_score")
    if score is None and variant_meta:
        score = variant_meta.get("fact_preservation_score")
    return {
        "fact_preservation_score": _json_safe(score),
        "validity_category": row.get("validity_category") or variant_meta.get("counterfactual_strength"),
        "exclude_from_strict_bias_rates": row.get("exclude_from_strict_bias_rates", variant_meta.get("exclude_from_strict_bias_rates")),
        "strict_exclusion_reason": _strict_exclusion_reason(row or None, variant_meta),
        "gold_label_applied": row.get("gold_label_applied"),
    }


def _is_address_proxy_pairwise_row(row: dict[str, Any]) -> bool:
    protected = str(row.get("protected_attribute_tested") or "")
    variant_type = str(row.get("variant_type") or "")
    return protected == "address_proxy" or variant_type.startswith("address_")


def _analysis_bucket_for_pairwise_row(row: dict[str, Any]) -> str:
    return "address_proxy" if _is_address_proxy_pairwise_row(row) else "strict_demographic"


def infer_review_priority(pairwise_row: dict[str, Any], *, schema_version: str | None = None) -> str:
    """Backward-compatible alias — see ``infer_detention_review_priority`` in detention_metrics."""
    return infer_detention_review_priority(pairwise_row, schema_version=schema_version)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return value != 0
    return str(value).strip().lower() in {"true", "1", "yes"}


def _num(value: Any) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_level(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return str(value).replace("_", " ")


def _shift_label(delta: Any, *, positive_label: str, negative_label: str) -> str | None:
    n = _num(delta)
    if n == 0:
        return None
    return positive_label if n > 0 else negative_label


def build_diff_summary(
    pairwise_row: dict[str, Any],
    neutral: dict[str, Any],
    variant: dict[str, Any],
    *,
    schema_version: str | None = None,
) -> dict[str, Any]:
    fields = output_fields_for_schema(schema_version)
    changed: list[str] = []
    for field in fields:
        n_val = neutral.get(field)
        v_val = variant.get(field)
        if field in {"less_restrictive_alternatives_considered", "procedural_safeguards_mentioned", "evidence_needed", "risk_flags", "limitations"}:
            if _parse_list_field(n_val) != _parse_list_field(v_val):
                changed.append(field)
        elif _json_safe(n_val) != _json_safe(v_val):
            changed.append(field)

    diff: dict[str, Any] = {
        "changed_fields": changed,
        "dangerousness_shift": _shift_label(pairwise_row.get("dangerousness_level_delta"), positive_label="increased", negative_label="decreased"),
        "obstruction_risk_shift": _shift_label(pairwise_row.get("obstruction_risk_level_delta"), positive_label="increased", negative_label="decreased"),
        "recommended_action_shift": _shift_label(pairwise_row.get("recommended_action_type_delta"), positive_label="stricter recommendation", negative_label="less strict recommendation"),
        "duration_shift": _shift_label(pairwise_row.get("recommended_duration_days_delta"), positive_label="longer duration", negative_label="shorter duration"),
        "credibility_framing_shift": _shift_label(pairwise_row.get("suspect_credibility_framing_shift"), positive_label="more skeptical", negative_label="less skeptical"),
        "rights_orientation_shift": _shift_label(pairwise_row.get("rights_orientation_shift"), positive_label="weaker rights framing", negative_label="stronger rights framing"),
        "alternatives_omitted": _coerce_bool(pairwise_row.get("less_restrictive_alternatives_considered_omission")),
        "procedural_safeguards_omitted": _coerce_bool(pairwise_row.get("procedural_safeguards_mentioned_omission")),
        "identity_leakage_flag": _coerce_bool(pairwise_row.get("identity_leakage_flag")),
        "unsupported_risk_inference_flag": _coerce_bool(pairwise_row.get("unsupported_risk_inference_flag")),
        "address_mention_in_reasoning": _coerce_bool(pairwise_row.get("address_mention_in_reasoning")),
        "insufficient_information_shift": _coerce_bool(pairwise_row.get("insufficient_information_shift")),
    }
    if is_minimal_dangerousness_schema(schema_version):
        diff["obstruction_risk_shift"] = None
        diff["recommended_action_shift"] = None
        diff["duration_shift"] = None
        diff["credibility_framing_shift"] = None
        diff["rights_orientation_shift"] = None
        diff["alternatives_omitted"] = None
        diff["procedural_safeguards_omitted"] = None

    parts: list[str] = []
    if diff["dangerousness_shift"]:
        parts.append(
            f"Dangerousness: {_format_level(neutral.get('dangerousness_level'))} → {_format_level(variant.get('dangerousness_level'))}"
        )
    if diff["obstruction_risk_shift"] and not is_minimal_dangerousness_schema(schema_version):
        parts.append(
            f"Obstruction risk: {_format_level(neutral.get('obstruction_risk_level'))} → {_format_level(variant.get('obstruction_risk_level'))}"
        )
    if diff["recommended_action_shift"] and not is_minimal_dangerousness_schema(schema_version):
        parts.append(
            f"Recommended action: {_format_level(neutral.get('recommended_action_type'))} → {_format_level(variant.get('recommended_action_type'))}"
        )
    n_dur = neutral.get("recommended_duration_days")
    v_dur = variant.get("recommended_duration_days")
    if _json_safe(n_dur) != _json_safe(v_dur) and not is_minimal_dangerousness_schema(schema_version):
        parts.append(f"Duration: {_format_level(n_dur)} → {_format_level(v_dur)}")
    if diff["alternatives_omitted"] and not is_minimal_dangerousness_schema(schema_version):
        parts.append("Less restrictive alternatives: present → omitted in variant")
    if diff["procedural_safeguards_omitted"] and not is_minimal_dangerousness_schema(schema_version):
        parts.append("Procedural safeguards: present → omitted in variant")
    if diff["credibility_framing_shift"] and not is_minimal_dangerousness_schema(schema_version):
        parts.append(
            f"Credibility framing: {_format_level(neutral.get('suspect_credibility_framing'))} → {_format_level(variant.get('suspect_credibility_framing'))}"
        )
    if _coerce_bool(pairwise_row.get("insufficient_information_shift")):
        parts.append("Insufficient-information assessment changed between neutral and variant")
    if _coerce_bool(pairwise_row.get("address_mention_in_reasoning")):
        parts.append("Possible address/locality mention in variant reasoning (audit signal)")
    diff["diff_summary"] = "; ".join(parts) if parts else "No structured output field changes detected."
    return diff


def build_why_flagged(pairwise_row: dict[str, Any]) -> str:
    flags = _parse_list_field(pairwise_row.get("detention_audit_flags"))
    review_label = _clean_csv_label(pairwise_row.get("review_label"))
    if flags:
        return f"Flagged because: {'; '.join(flags)}"
    if review_label:
        return f"Flagged for legal review: {review_label}"
    if is_detention_audit_flag(pairwise_row):
        return "Flagged because structured audit signals were detected between neutral and variant outputs."
    return "Not flagged — included for controlled-comparison review."


def build_plain_language_summary(
    pairwise_row: dict[str, Any],
    neutral: dict[str, Any],
    variant: dict[str, Any],
    variant_meta: dict[str, Any],
    *,
    schema_version: str | None = None,
) -> str:
    variant_type = str(pairwise_row.get("variant_type") or variant_meta.get("variant_type") or "variant")
    variant_display = _display_label(variant_type)
    protected = str(pairwise_row.get("protected_attribute_tested") or "—")
    n_danger = _format_level(neutral.get("dangerousness_level"))
    v_danger = _format_level(variant.get("dangerousness_level"))
    flagged = is_detention_audit_flag(pairwise_row, schema_version=schema_version)
    intro = (
        f"In this comparison, the legally relevant facts are intended to remain constant, "
        f"but the variant ({variant_display}) changes presentation while testing {protected.replace('_', ' ')}. "
    )
    if is_minimal_dangerousness_schema(schema_version):
        body = (
            f"The model assessed dangerousness as {v_danger} in the variant and {n_danger} in the neutral case."
        )
    else:
        n_action = _format_level(neutral.get("recommended_action_type"))
        v_action = _format_level(variant.get("recommended_action_type"))
        body = (
            f"The model assessed dangerousness as {v_danger} in the variant and {n_danger} in the neutral case, "
            f"with recommended action {v_action} vs {n_action}."
        )
    tail = (
        " This case is flagged for legal review."
        if flagged
        else " This comparison is available for expert review."
    )
    return intro + body + tail


def infer_what_changed(variant_type: str, base_text: str, variant_text: str) -> list[str]:
    hints = list(VARIANT_CHANGE_HINTS.get(variant_type, []))
    if not hints:
        label = _display_label(variant_type)
        hints.append(f"Variant condition changed: {label}")
    if base_text.strip() != variant_text.strip():
        if "name" in variant_type:
            pass
        elif "broken" in variant_type or "formal" in variant_type:
            hints.append("Language or phrasing changed in the case narrative")
        elif "framing" in variant_type or "proxy" in variant_type:
            hints.append("Narrative framing or proxy cue changed")
    return hints


def infer_facts_preserved(variant_meta: dict[str, Any]) -> tuple[bool | None, str]:
    strength = str(variant_meta.get("counterfactual_strength") or "").lower()
    variant_type = str(variant_meta.get("variant_type") or "")
    if strength == "strict" and variant_type != "neutral_he":
        return True, "Strict synthetic counterfactual — legally relevant facts intended to be preserved."
    if variant_type in {"low_income_neighborhood_proxy"} or "framing" in variant_type:
        return None, "Narrative or proxy variant — may change non-legal cues; requires expert review."
    if str(variant_meta.get("protected_attribute_tested") or "") == "address_proxy" or variant_type.startswith("address_"):
        return None, "Address-proxy variant — analyze separately from strict demographic fairness rates."
    if strength == "stress":
        return None, "Stress-test variant — facts preservation should be verified by a legal expert."
    return True, "Synthetic comparison — intended same legal facts with presentation change only."


DEMO_REDACTED_CASE_TEXT = "[Full case text omitted in demo-redacted export — use full export for expert review.]"


def _maybe_redact_case_text(text: str | None, *, redact: bool) -> str | None:
    if not redact or not text:
        return text
    return DEMO_REDACTED_CASE_TEXT


def build_case_side(
    row: dict[str, Any] | None,
    *,
    prompt_mode: str,
    role: str,
    redact_full_case_text: bool = False,
    schema_version: str | None = None,
) -> dict[str, Any]:
    if not row:
        return {
            "case_id": None,
            "variant_id": None,
            "title": None,
            "full_case_text": None,
            "structured_facts": {},
            "prompt_input": None,
            "full_prompt_sent_to_model": None,
            "prompt_reconstruction_status": "missing_output",
            "prompt_mode": prompt_mode,
        }
    prompt_input = str(row.get("prompt_input") or row.get("input_text") or "")
    stored = str(row.get("full_prompt_sent_to_model") or "") if row else ""
    full_prompt, status = format_full_prompt(
        prompt_input,
        prompt_mode=prompt_mode,
        case_id=str(row.get("case_id") or ""),
        stored_prompt=stored or None,
        schema_version=schema_version,
    )
    display_text = _maybe_redact_case_text(prompt_input, redact=redact_full_case_text) or prompt_input
    export_prompt = _maybe_redact_case_text(full_prompt, redact=redact_full_case_text) if redact_full_case_text else full_prompt
    block: dict[str, Any] = {
        "case_id": row.get("case_id"),
        "title": row.get("title"),
        "full_case_text": display_text,
        "structured_facts": {} if redact_full_case_text else parse_structured_facts(prompt_input),
        "prompt_input": display_text if redact_full_case_text else prompt_input,
        "full_prompt_sent_to_model": export_prompt,
        "prompt_reconstruction_status": status,
        "prompt_mode": prompt_mode,
    }
    if role == "variant":
        block["variant_id"] = row.get("variant_id")
        block["variant_label"] = str(
            row.get("display_label_en")
            or row.get("display_label")
            or row.get("variant_type")
            or ""
        ).replace("_", " ")
        block["protected_attribute_tested"] = row.get("protected_attribute_tested")
        block["language_or_framing_condition"] = row.get("variant_type")
    return block


def build_review_record(
    pairwise_row: dict[str, Any],
    *,
    outputs_index: dict[str, dict[str, Any]],
    outputs_all_modes: dict[str, dict[str, Any]],
    synthetic_index: dict[str, dict[str, Any]],
    cross_prompt_rows: list[dict[str, Any]],
    prompt_mode: str,
    data_status: str,
    schema_version: str | None = None,
    redact_full_case_text: bool = False,
    validity_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    case_id = str(pairwise_row.get("case_id") or "")
    variant_id = str(pairwise_row.get("variant_id") or "")
    if not case_id or not variant_id:
        return None

    neutral_id = _neutral_variant_id(case_id)
    neutral_out = outputs_index.get(_request_key(case_id, neutral_id, prompt_mode))
    variant_out = outputs_index.get(_request_key(case_id, variant_id, prompt_mode))
    neutral_meta = synthetic_index.get(neutral_id) or neutral_out or {}
    variant_meta = synthetic_index.get(variant_id) or variant_out or {}

    version = schema_version or str((variant_out or {}).get("schema_version") or SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2)

    neutral_block = extract_output_block(neutral_out, schema_version=version)
    variant_block = extract_output_block(variant_out, schema_version=version)
    diff = build_diff_summary(pairwise_row, neutral_block, variant_block, schema_version=version)

    base_side = build_case_side(neutral_meta, prompt_mode=prompt_mode, role="base", redact_full_case_text=redact_full_case_text, schema_version=version)
    variant_side = build_case_side(variant_meta, prompt_mode=prompt_mode, role="variant", redact_full_case_text=redact_full_case_text, schema_version=version)
    base_text = str(base_side.get("full_case_text") or "")
    variant_text = str(variant_side.get("full_case_text") or "")
    variant_side["what_changed_from_base"] = infer_what_changed(
        str(pairwise_row.get("variant_type") or ""),
        base_text,
        variant_text,
    )
    preserved, preservation_notes = infer_facts_preserved(variant_meta if isinstance(variant_meta, dict) else {})
    variant_side["legally_relevant_facts_preserved"] = preserved
    variant_side["facts_preservation_notes"] = preservation_notes

    flags = _parse_list_field(pairwise_row.get("detention_audit_flags"))
    review_label = _clean_csv_label(pairwise_row.get("review_label"))
    issue_types = flags if flags else ([review_label] if review_label else [])
    issue_types = [t for t in issue_types if t and str(t).strip().lower() not in {"nan", "none", ""}]

    meta = variant_meta if isinstance(variant_meta, dict) else {}
    use_strict = not _coerce_bool(meta.get("exclude_from_strict_bias_rates"))
    v_index = validity_index or {}

    return {
        "review_record_id": _review_record_id(case_id, variant_id, prompt_mode),
        "use_case": "detention",
        "data_status": data_status,
        "base_case_id": case_id,
        "base_case_title": str(meta.get("title") or neutral_meta.get("title") or case_id),
        "variant_id": variant_id,
        "prompt_mode": prompt_mode,
        "dataset_mode": str(pairwise_row.get("dataset_mode") or meta.get("dataset_mode") or "synthetic_counterfactual"),
        "counterfactual_strength": str(meta.get("counterfactual_strength") or "strict"),
        "use_for_strict_bias_rates": use_strict,
        "review_priority": infer_detention_review_priority(pairwise_row, schema_version=version),
        "is_flagged": is_detention_audit_flag(pairwise_row, schema_version=version),
        "issue_types": issue_types,
        "variant_type": str(pairwise_row.get("variant_type") or ""),
        "protected_attribute_tested": str(pairwise_row.get("protected_attribute_tested") or ""),
        "analysis_bucket": _analysis_bucket_for_pairwise_row(pairwise_row),
        "schema_version": version,
        "address_variant_id": _json_safe(meta.get("address_variant_id")),
        "address_text_he": _json_safe(meta.get("address_text_he")),
        "base_case": base_side,
        "variant_case": variant_side,
        "neutral_output": neutral_block,
        "variant_output": variant_block,
        "diff": diff,
        "cross_prompt": build_cross_prompt_block(case_id, variant_id, outputs_all_modes, cross_prompt_rows),
        "validity_context": build_validity_context(case_id, variant_id, meta, v_index),
        "review_guidance": {
            "why_flagged": build_why_flagged(pairwise_row),
            "plain_language_summary": build_plain_language_summary(
                pairwise_row, neutral_block, variant_block, meta, schema_version=version
            ),
            "legal_review_questions": list(LEGAL_REVIEW_QUESTIONS),
            "caution_note": CAUTION_NOTE,
        },
    }


def build_outputs_index_all_modes(
    parsed_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in parsed_rows:
        mode = str(row.get("prompt_mode") or "baseline")
        key = _request_key(str(row.get("case_id") or ""), str(row.get("variant_id") or ""), mode)
        index[key] = row
    return index


def build_cross_prompt_block(
    case_id: str,
    variant_id: str,
    outputs_all: dict[str, dict[str, Any]],
    cross_prompt_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach variant/neutral outputs across prompt modes for expert review."""
    modes = ("baseline", "fairness_aware", "demographic_blind")
    neutral_id = _neutral_variant_id(case_id)
    variant_by_mode: dict[str, Any] = {}
    neutral_by_mode: dict[str, Any] = {}
    for mode in modes:
        v_row = outputs_all.get(_request_key(case_id, variant_id, mode))
        n_row = outputs_all.get(_request_key(case_id, neutral_id, mode))
        if v_row:
            variant_by_mode[mode] = extract_output_block(v_row)
        if n_row:
            neutral_by_mode[mode] = extract_output_block(n_row)

    instability: list[dict[str, Any]] = []
    for cp in cross_prompt_rows:
        if str(cp.get("case_id")) == case_id and str(cp.get("variant_id")) == variant_id:
            instability.append(
                {
                    "comparison_mode": cp.get("comparison_mode"),
                    "fields_changed": _parse_list_field(cp.get("fields_changed")),
                    "n_fields_changed": cp.get("n_fields_changed"),
                    "cross_prompt_instability_flag": cp.get("cross_prompt_instability_flag"),
                    "review_note": cp.get("review_note"),
                }
            )

    return {
        "modes_available": [m for m in modes if m in variant_by_mode],
        "variant_outputs_by_mode": variant_by_mode,
        "neutral_outputs_by_mode": neutral_by_mode,
        "cross_prompt_instability": instability,
    }


def record_filename(review_record_id: str) -> str:
    """Safe filename for per-record JSON export."""
    return review_record_id.replace("::", "__").replace("/", "_") + ".json"


def record_relpath(review_record_id: str) -> str:
    return f"detention_case_review_records/{record_filename(review_record_id)}"


def build_review_index_entry(record: dict[str, Any]) -> dict[str, Any]:
    """Lightweight queue row for fast dashboard load."""
    rid = record["review_record_id"]
    diff = record.get("diff") or {}
    neutral = record.get("neutral_output") or {}
    variant = record.get("variant_output") or {}
    guidance = record.get("review_guidance") or {}
    search_parts = [
        str(record.get("base_case_title") or ""),
        str(record.get("base_case_id") or ""),
        str(record.get("variant_id") or ""),
        str(record.get("variant_type") or ""),
        str(guidance.get("plain_language_summary") or ""),
        str(guidance.get("why_flagged") or ""),
        str(neutral.get("full_memo_text") or neutral.get("reasoning_text") or "")[:400],
        str(variant.get("full_memo_text") or variant.get("reasoning_text") or "")[:400],
    ]
    return {
        "review_record_id": rid,
        "record_path": record_relpath(rid),
        "base_case_id": record["base_case_id"],
        "base_case_title": record["base_case_title"],
        "variant_id": record["variant_id"],
        "variant_type": record["variant_type"],
        "variant_label": record.get("variant_case", {}).get("variant_label"),
        "prompt_mode": record["prompt_mode"],
        "review_priority": record["review_priority"],
        "is_flagged": record["is_flagged"],
        "issue_types": record.get("issue_types", [])[:3],
        "protected_attribute_tested": record.get("protected_attribute_tested"),
        "analysis_bucket": record.get("analysis_bucket"),
        "why_flagged_short": str(guidance.get("why_flagged", ""))[:120],
        "search_blob": " ".join(p for p in search_parts if p).lower()[:800],
        "issue_flags": {
            "dangerousness": bool(diff.get("dangerousness_shift")),
            "obstruction": bool(diff.get("obstruction_risk_shift")),
            "recommended_action": bool(diff.get("recommended_action_shift")),
            "duration": bool(diff.get("duration_shift")),
            "alternatives": bool(diff.get("alternatives_omitted")),
            "safeguards": bool(diff.get("procedural_safeguards_omitted")),
            "identity": bool(diff.get("identity_leakage_flag")),
            "unsupported": bool(diff.get("unsupported_risk_inference_flag")),
        },
    }


def write_split_review_records(
    records: list[dict[str, Any]],
    output_dir: Path,
    *,
    incremental: bool = True,
) -> Path:
    """Write one JSON file per review record for lazy dashboard loading."""
    split_dir = output_dir / "detention_case_review_records"
    split_dir.mkdir(parents=True, exist_ok=True)
    expected_names = {record_filename(str(record["review_record_id"])) for record in records}
    for stale in split_dir.glob("*.json"):
        if stale.name not in expected_names:
            stale.unlink()
    for record in records:
        path = split_dir / record_filename(str(record["review_record_id"]))
        payload = json.dumps(_json_safe_dict(record), ensure_ascii=False, indent=2)
        if incremental and path.exists():
            try:
                if hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest() == hashlib.sha256(
                    payload.encode()
                ).hexdigest():
                    continue
            except OSError:
                pass
        path.write_text(payload, encoding="utf-8")
    return split_dir


def build_outputs_index(
    parsed_rows: list[dict[str, Any]],
    *,
    prompt_mode: str = "baseline",
) -> dict[str, dict[str, Any]]:
    all_modes = build_outputs_index_all_modes(parsed_rows)
    if prompt_mode == "all":
        return all_modes
    return {k: v for k, v in all_modes.items() if k.endswith(f"::{prompt_mode}")}


def build_synthetic_index(synthetic_csv: Path) -> dict[str, dict[str, Any]]:
    if not synthetic_csv.exists():
        return {}
    df = pd.read_csv(synthetic_csv)
    index = {str(r["variant_id"]): r.to_dict() for _, r in df.iterrows()}

    # Enrich address variants with display labels from the address JSON
    addr_json = synthetic_csv.parent.parent / "address_variants" / "israeli_address_variants.json"
    if addr_json.exists():
        try:
            addr_data = json.loads(addr_json.read_text(encoding="utf-8"))
            addr_variants = addr_data.get("variants", [])
            addr_labels = {
                str(v.get("address_variant_id", "")): str(v.get("display_label", ""))
                for v in addr_variants
                if v.get("display_label")
            }
            for vid, row in index.items():
                vtype = str(row.get("variant_type", ""))
                if vtype.startswith("address_") and (
                    not row.get("display_label_en")
                    or str(row.get("display_label_en")) in ("nan", "None", "")
                ):
                    addr_id = str(row.get("address_variant_id", ""))
                    label = addr_labels.get(addr_id, "")
                    if label:
                        row["display_label_en"] = label
                        row["display_label"] = label
        except Exception:
            pass

    return index


def _dedupe_pairwise_rows(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    return dedupe_detention_pairwise_rows(pairwise_df)


def _flagged_lookup(flagged_df: pd.DataFrame) -> set[tuple[str, ...]]:
    keys: set[tuple[str, ...]] = set()
    if flagged_df.empty:
        return keys
    has_mode = "prompt_mode" in flagged_df.columns
    for _, fr in flagged_df.iterrows():
        base = (str(fr.get("case_id")), str(fr.get("variant_id")))
        if has_mode and pd.notna(fr.get("prompt_mode")):
            keys.add((*base, str(fr.get("prompt_mode"))))
        else:
            keys.add(base)
    return keys


def _is_flagged_row(row: dict[str, Any], flagged_keys: set[tuple[str, ...]]) -> bool:
    if is_detention_audit_flag(row):
        return True
    base = (str(row.get("case_id")), str(row.get("variant_id")))
    mode = str(row.get("prompt_mode") or "")
    if mode and any(len(k) == 3 for k in flagged_keys):
        return (*base, mode) in flagged_keys
    return base in flagged_keys


def _append_records_from_pairwise_df(
    records: list[dict[str, Any]],
    pairwise_df: pd.DataFrame,
    *,
    mode: str,
    outputs_index: dict[str, dict[str, Any]],
    outputs_all_modes: dict[str, dict[str, Any]],
    synthetic_index: dict[str, dict[str, Any]],
    cross_prompt_rows: list[dict[str, Any]],
    flagged_keys: set[tuple[str, ...]],
    data_status: str,
    resolved_schema: str | None,
    include_unflagged: bool,
    redact_full_case_text: bool = False,
    validity_index: dict[str, dict[str, Any]] | None = None,
) -> None:
    mode_pairwise = pairwise_df
    if not pairwise_df.empty and "prompt_mode" in pairwise_df.columns:
        mode_pairwise = pairwise_df[pairwise_df["prompt_mode"] == mode]

    if mode_pairwise.empty:
        for key in sorted(flagged_keys):
            if len(key) == 3 and key[2] != mode:
                continue
            case_id, variant_id = key[0], key[1]
            pairwise_row = {
                "case_id": case_id,
                "variant_id": variant_id,
                "prompt_mode": mode,
                "detention_framing_bias_flag": True,
            }
            rec = build_review_record(
                pairwise_row,
                outputs_index=outputs_index,
                outputs_all_modes=outputs_all_modes,
                synthetic_index=synthetic_index,
                cross_prompt_rows=cross_prompt_rows,
                prompt_mode=mode,
                data_status=data_status,
                schema_version=resolved_schema,
                redact_full_case_text=redact_full_case_text,
                validity_index=validity_index,
            )
            if rec:
                records.append(rec)
        return

    for _, pr in mode_pairwise.iterrows():
        row = pr.to_dict()
        row.setdefault("prompt_mode", mode)
        is_flagged = _is_flagged_row(row, flagged_keys)
        if not include_unflagged and not is_flagged:
            continue
        rec = build_review_record(
            row,
            outputs_index=outputs_index,
            outputs_all_modes=outputs_all_modes,
            synthetic_index=synthetic_index,
            cross_prompt_rows=cross_prompt_rows,
            prompt_mode=mode,
            data_status=data_status,
            schema_version=resolved_schema,
            redact_full_case_text=redact_full_case_text,
            validity_index=validity_index,
        )
        if rec:
            records.append(rec)


def export_case_review_records(
    *,
    run_dir: Path,
    synthetic_input: Path,
    output: Path,
    data_status: str = "gemini_full",
    prompt_mode: str = "baseline",
    include_unflagged: bool = True,
    all_prompt_modes: bool = False,
    dry_run: bool = False,
    schema_version: str | None = None,
    redact_full_case_text: bool = False,
) -> dict[str, Any]:
    """Build denormalized review JSON for the dashboard."""
    analysis_dir = run_dir / "analysis"
    parsed_path = run_dir / "parsed_outputs.jsonl"
    pairwise_path = analysis_dir / "detention_pairwise_comparison.csv"
    address_proxy_path = analysis_dir / "detention_address_proxy_pairwise_comparison.csv"
    flagged_path = analysis_dir / "detention_flagged_cases.csv"

    cross_prompt_path = analysis_dir / "detention_cross_prompt_comparisons.csv"
    cross_prompt_rows: list[dict[str, Any]] = []
    if cross_prompt_path.exists() and cross_prompt_path.stat().st_size:
        try:
            cross_prompt_df = pd.read_csv(cross_prompt_path)
            if not cross_prompt_df.empty:
                cross_prompt_rows = cross_prompt_df.to_dict(orient="records")
        except pd.errors.EmptyDataError:
            cross_prompt_rows = []

    parsed_rows = _load_jsonl(parsed_path)
    resolved_schema = schema_version or next(
        (str(r.get("schema_version")) for r in parsed_rows if r.get("schema_version")),
        None,
    )
    outputs_all_modes = build_outputs_index_all_modes(parsed_rows)
    synthetic_index = build_synthetic_index(synthetic_input)
    validity_index = _load_validity_index(run_dir)

    pairwise_df = pd.read_csv(pairwise_path) if pairwise_path.exists() and pairwise_path.stat().st_size else pd.DataFrame()
    if not pairwise_df.empty:
        pairwise_df = _dedupe_pairwise_rows(pairwise_df)

    address_proxy_df = pd.DataFrame()
    if address_proxy_path.exists() and address_proxy_path.stat().st_size:
        address_proxy_df = pd.read_csv(address_proxy_path)
        if not address_proxy_df.empty:
            address_proxy_df = _dedupe_pairwise_rows(address_proxy_df)

    flagged_df = pd.DataFrame()
    if flagged_path.exists() and flagged_path.stat().st_size:
        flagged_df = pd.read_csv(flagged_path)
    flagged_keys = _flagged_lookup(flagged_df)

    modes: list[str]
    combined_pairwise = pairwise_df
    if not address_proxy_df.empty:
        combined_pairwise = pd.concat([pairwise_df, address_proxy_df], ignore_index=True) if not pairwise_df.empty else address_proxy_df
    if all_prompt_modes and not combined_pairwise.empty and "prompt_mode" in combined_pairwise.columns:
        modes = sorted(combined_pairwise["prompt_mode"].dropna().astype(str).unique().tolist())
    else:
        modes = [prompt_mode]

    records: list[dict[str, Any]] = []
    for mode in modes:
        outputs_index = build_outputs_index(parsed_rows, prompt_mode=mode)
        _append_records_from_pairwise_df(
            records,
            pairwise_df,
            mode=mode,
            outputs_index=outputs_index,
            outputs_all_modes=outputs_all_modes,
            synthetic_index=synthetic_index,
            cross_prompt_rows=cross_prompt_rows,
            flagged_keys=flagged_keys,
            data_status=data_status,
            resolved_schema=resolved_schema,
            include_unflagged=include_unflagged,
            redact_full_case_text=redact_full_case_text,
            validity_index=validity_index,
        )
        if not address_proxy_df.empty:
            _append_records_from_pairwise_df(
                records,
                address_proxy_df,
                mode=mode,
                outputs_index=outputs_index,
                outputs_all_modes=outputs_all_modes,
                synthetic_index=synthetic_index,
                cross_prompt_rows=cross_prompt_rows,
                flagged_keys=flagged_keys,
                data_status=data_status,
                resolved_schema=resolved_schema,
                include_unflagged=include_unflagged,
                redact_full_case_text=redact_full_case_text,
                validity_index=validity_index,
            )

    records.sort(key=lambda r: (
        0 if r.get("review_priority") == "high" else 1 if r.get("review_priority") == "medium" else 2,
        0 if r.get("is_flagged") else 1,
        str(r.get("base_case_id")),
        str(r.get("variant_id")),
    ))

    split_dir = write_split_review_records(records, output.parent)
    flagged_count = sum(1 for r in records if r.get("is_flagged"))
    strict_count = sum(1 for r in records if r.get("analysis_bucket") == "strict_demographic")
    address_proxy_count = sum(1 for r in records if r.get("analysis_bucket") == "address_proxy")
    exported_at = _utc_now()
    prompt_note = (
        "Prompts use exact API payloads when full_prompt_sent_to_model was logged by the runner; "
        "otherwise they are reconstructed from the prompt builder."
    )
    payload = {
        "exported_at": exported_at,
        "data_status": data_status,
        "prompt_mode": "all" if all_prompt_modes and len(modes) > 1 else (modes[0] if modes else prompt_mode),
        "prompt_modes": modes,
        "prompt_reconstruction_note": prompt_note,
        "record_count": len(records),
        "strict_demographic_record_count": strict_count,
        "address_proxy_record_count": address_proxy_count,
        "flagged_count": flagged_count,
        "records_split": True,
        "records_dir": "detention_case_review_records",
        "records": [],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return {
            "output": output,
            "index_output": output.parent / "detention_case_review_index.json",
            "split_dir": None,
            "record_count": len(records),
            "flagged_count": flagged_count,
            "data_status": data_status,
            "dry_run": True,
            "validation": {
                "has_pairwise_or_flagged_source": not pairwise_df.empty or bool(flagged_keys),
                "has_parsed_outputs": bool(parsed_rows),
                "has_synthetic_index": bool(synthetic_index),
                "sample_record_fields_ok": bool(records) and all(
                    r.get("base_case_id") and r.get("variant_id") and r.get("review_record_id") for r in records[:3]
                ),
                "records_would_write": len(records),
            },
        }

    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    index_path = output.parent / "detention_case_review_index.json"
    index_payload = {
        "exported_at": exported_at,
        "data_status": data_status,
        "prompt_mode": payload["prompt_mode"],
        "prompt_modes": modes,
        "record_count": len(records),
        "strict_demographic_record_count": strict_count,
        "address_proxy_record_count": address_proxy_count,
        "flagged_count": flagged_count,
        "records_split": True,
        "records_dir": "detention_case_review_records",
        "records_index": [build_review_index_entry(r) for r in records],
    }
    index_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "output": output,
        "index_output": index_path,
        "split_dir": split_dir,
        "record_count": len(records),
        "strict_demographic_record_count": strict_count,
        "address_proxy_record_count": address_proxy_count,
        "flagged_count": flagged_count,
        "data_status": data_status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export detention case review records for dashboard.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--synthetic-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--data-status",
        default="gemini_full",
        choices=["mock", "gemini_pilot", "gemini_full", "gemini_expanded_full", "gemini_minimal_address"],
    )
    parser.add_argument("--schema-version", default=None, help="Detention output schema version for export.")
    parser.add_argument("--prompt-mode", default="baseline", help="Single prompt mode, or use with --all-prompt-modes.")
    parser.add_argument("--all-prompt-modes", action="store_true", help="Export review records for every prompt mode.")
    parser.add_argument("--flagged-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate export shape without writing dashboard files.")
    args = parser.parse_args(argv)

    result = export_case_review_records(
        run_dir=args.run_dir,
        synthetic_input=args.synthetic_input,
        output=args.output,
        data_status=args.data_status,
        prompt_mode=args.prompt_mode,
        include_unflagged=not args.flagged_only,
        all_prompt_modes=args.all_prompt_modes,
        dry_run=args.dry_run,
        schema_version=args.schema_version,
    )
    if args.dry_run:
        print(f"Case review export dry-run OK — would write {result['record_count']} records to {args.output}")
        print(f"  Validation: {result.get('validation')}")
    else:
        print(f"Case review export complete → {result['output']}")
        print(f"  Records: {result['record_count']} ({result['flagged_count']} flagged)")
        print(f"  Data status: {result['data_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
