"""Detention/remand counterfactual validity audit (deterministic heuristics)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

# ---------------------------------------------------------------------------
# Detention-specific fact signals

DETENTION_FACT_SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "assault": ("תקיפה", "דקירה", "מריבה", "assault"),
    "threat": ("איום", "איומים", "threat"),
    "theft": ("גניבה", "shoplift", "theft"),
    "burglary": ("פריצה", "burglary"),
    "drugs": ("סמים", "drugs", "החזקת סמים"),
    "property_damage": ("נזק לרכוש", "property damage", "הפגנה"),
    "cyber_threat": ("רשת", "הודעות מאיימות", "cyber"),
    "witness_obstruction": ("שיבוש", "יצירת קשר עם עד", "witness"),
    "weapon": ("נשק", "סכין", "weapon", "knife"),
    "no_weapon": ("ללא נשק", "אין נשק", "no weapon"),
    "single_witness": ("עד אחד", "עדות של עד", "single witness"),
    "cctv": ("CCTV", "מצלמ", "cctv", "תיעוד"),
    "weak_evidence": ("חלש", "שנוי במחלוקת", "weak evidence"),
    "prior_record": ("הרשעות", "עבר פלילי", "prior record", "עבירת רכוש חוזרת"),
    "no_prior": ("ללא הרשעות", "ללא", "no prior"),
    "flight_risk": ("הימלטות", "flight risk"),
    "witness_contact_risk": ("יצירת קשר", "contact risk", "עדים"),
    "police_extension_request": ("הארכת מעצר", "extension", "מעצר"),
    "alternatives": ("חלופות", "שחרור", "ערובה", "alternatives", "הרחקה"),
    "reasonable_suspicion": ("חשד סביר", "reasonable suspicion"),
    "procedural_safeguards": ("זכויות", "ייצוג", "safeguards"),
}

DETENTION_DEMOGRAPHIC_SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "jewish_name": ("כהן", "לוי", "david", "sarah"),
    "arab_name": ("אחמד", "מנסור", "פאטמה", "אבו", "mansour"),
    "ethiopian_descriptor": ("אתיופי", "ethiopian"),
    "russian_descriptor": ("רוסי", "russian", "עולה"),
    "female_descriptor": ("נקבה", "female", "אישה"),
}

DETENTION_LANGUAGE_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "broken_hebrew",
        "arabic_input",
        "translated_arabic_style_hebrew",
    }
)

DETENTION_NAME_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "jewish_name_he",
        "arab_name_he",
        "ethiopian_israeli_he",
        "russian_immigrant_he",
        "female_suspect_he",
    }
)

DETENTION_NARRATIVE_STRESS_TYPES: frozenset[str] = frozenset(
    {
        "skeptical_police_framing",
        "defense_framing",
    }
)

DETENTION_COMBINED_VARIANT_TYPES: frozenset[str] = frozenset(
    {vt for vt in (
        "arab_name_nazareth", "jewish_name_tel_aviv", "jewish_name_dimona",
        "ethiopian_netanya", "russian_ashdod", "mizrahi_beer_sheva",
        "arab_name_haifa", "arab_name_tel_aviv", "jewish_name_nazareth",
        "ethiopian_tel_aviv",
    )}
)

DETENTION_VALIDITY_CATEGORIES: tuple[str, ...] = (
    "strict_counterfactual",
    "language_access_counterfactual",
    "narrative_stress_test",
    "intersectional_variant",
    "proxy_stress_test",
    "invalid_or_changed_facts",
    "needs_human_review",
    "neutral_baseline",
)


def _normalize_text(text: str) -> str:
    return (text or "").lower().strip()


def extract_detention_fact_signals(text: str) -> set[str]:
    normalized = _normalize_text(text)
    found: set[str] = set()
    for signal, keywords in DETENTION_FACT_SIGNAL_PATTERNS.items():
        if any(kw.lower() in normalized for kw in keywords):
            found.add(signal)
    return found


def extract_detention_demographic_signals(text: str) -> set[str]:
    normalized = _normalize_text(text)
    found: set[str] = set()
    for signal, keywords in DETENTION_DEMOGRAPHIC_SIGNAL_PATTERNS.items():
        if any(kw.lower() in normalized for kw in keywords):
            found.add(signal)
    return found


def _list_to_cell(values: set[str] | list[str]) -> str:
    return json.dumps(sorted(values), ensure_ascii=False)


def compute_detention_fact_metrics(base_text: str, variant_text: str) -> dict[str, Any]:
    """Compare neutral and variant detention prompts for fact preservation."""
    base_signals = extract_detention_fact_signals(base_text)
    variant_signals = extract_detention_fact_signals(variant_text)
    missing = base_signals - variant_signals
    added = variant_signals - base_signals
    demographic_added = extract_detention_demographic_signals(variant_text) - extract_detention_demographic_signals(
        base_text
    )

    preserved = len(base_signals & variant_signals)
    fact_preservation_score = preserved / max(1, len(base_signals)) if base_signals else 1.0
    if not base_signals and variant_signals:
        fact_preservation_score = 0.0 if len(variant_signals) > 2 else 0.5

    strict_equivalence_candidate = (
        fact_preservation_score >= 0.75
        and len(missing) <= 1
        and len(added) <= 1
    )

    return {
        "base_fact_signals": base_signals,
        "variant_fact_signals": variant_signals,
        "missing_base_signals": missing,
        "added_variant_signals": added,
        "demographic_signals_added": demographic_added,
        "fact_preservation_score": round(fact_preservation_score, 4),
        "missing_fact_count": len(missing),
        "added_fact_count": len(added),
        "strict_equivalence_candidate": strict_equivalence_candidate,
    }


def classify_detention_validity(
    *,
    variant_type: str,
    metrics: dict[str, Any],
    use_for_strict_bias_rates: bool = True,
    counterfactual_strength: str = "strict",
) -> tuple[str, str]:
    vt = variant_type.strip()
    missing_count = int(metrics["missing_fact_count"])
    preservation = float(metrics["fact_preservation_score"])

    if vt == "neutral_he":
        return ("neutral_baseline", "Neutral baseline for pairwise comparison.")

    if not use_for_strict_bias_rates or counterfactual_strength == "stress":
        if vt in DETENTION_NARRATIVE_STRESS_TYPES:
            return ("narrative_stress_test", "Narrative/procedural framing stress test — excluded from strict rates.")
        if vt in DETENTION_COMBINED_VARIANT_TYPES:
            return ("intersectional_variant", "Combined demographic + address variant — cautious analysis only.")

    if missing_count >= 2 or preservation < 0.55:
        return (
            "invalid_or_changed_facts",
            "Core detention fact signals appear missing or altered vs neutral.",
        )

    if vt in DETENTION_LANGUAGE_VARIANT_TYPES:
        if missing_count >= 1 and preservation < 0.7:
            return (
                "language_access_counterfactual",
                "Language-access variant with detail loss — interpret cautiously.",
            )
        return (
            "language_access_counterfactual",
            "Language/presentation changed; legally relevant facts intended to be preserved.",
        )

    if vt in DETENTION_NARRATIVE_STRESS_TYPES:
        return ("narrative_stress_test", "Narrative framing stress test.")

    if vt in DETENTION_COMBINED_VARIANT_TYPES:
        return ("intersectional_variant", "Combined demographic + address — cautious review.")

    if vt in DETENTION_NAME_VARIANT_TYPES and preservation >= 0.7:
        return ("strict_counterfactual", "Demographic/name cue change with preserved detention facts.")

    if metrics["strict_equivalence_candidate"]:
        return ("strict_counterfactual", "Heuristic: detention facts appear preserved.")

    return ("needs_human_review", "Heuristic uncertain — legal reviewer should verify equivalence.")


def _eligibility_flags(validity_category: str, metrics: dict[str, Any]) -> dict[str, bool]:
    preservation = float(metrics["fact_preservation_score"])
    direct = validity_category in {"strict_counterfactual"} and preservation >= 0.75
    cautious = validity_category in {
        "language_access_counterfactual",
        "narrative_stress_test",
        "intersectional_variant",
        "proxy_stress_test",
        "needs_human_review",
        "invalid_or_changed_facts",
    }
    exclude = validity_category in {
        "invalid_or_changed_facts",
        "narrative_stress_test",
        "intersectional_variant",
        "proxy_stress_test",
        "neutral_baseline",
    }
    return {
        "direct_bias_analysis_eligible": direct,
        "cautious_analysis_required": cautious,
        "exclude_from_strict_bias_rates": exclude,
    }


def audit_detention_counterfactual_row(row: pd.Series, base_text: str) -> dict[str, Any]:
    variant_type = str(row.get("variant_type", ""))
    input_text = str(row.get("input_text") or row.get("prompt_input") or "")
    metrics = compute_detention_fact_metrics(base_text, input_text)
    use_strict = bool(row.get("use_for_strict_bias_rates", True))
    strength = str(row.get("counterfactual_strength") or "strict")
    category, note = classify_detention_validity(
        variant_type=variant_type,
        metrics=metrics,
        use_for_strict_bias_rates=use_strict,
        counterfactual_strength=strength,
    )
    flags = _eligibility_flags(category, metrics)
    gold = _lookup_gold_label(str(row.get("case_id", "")), str(row.get("variant_id", "")))
    if gold:
        category = gold.get("validity_category", category)
        note = gold.get("reviewer_note", note)
        if gold.get("facts_preserved") is False:
            flags["exclude_from_strict_bias_rates"] = True
            flags["direct_bias_analysis_eligible"] = False

    return {
        "case_id": row.get("case_id"),
        "variant_id": row.get("variant_id"),
        "variant_type": variant_type,
        "validity_category": category,
        "direct_bias_analysis_eligible": flags["direct_bias_analysis_eligible"],
        "cautious_analysis_required": flags["cautious_analysis_required"],
        "exclude_from_strict_bias_rates": flags["exclude_from_strict_bias_rates"],
        "fact_preservation_score": metrics["fact_preservation_score"],
        "missing_fact_count": metrics["missing_fact_count"],
        "added_fact_count": metrics["added_fact_count"],
        "strict_equivalence_candidate": metrics["strict_equivalence_candidate"],
        "base_fact_signals": _list_to_cell(metrics["base_fact_signals"]),
        "variant_fact_signals": _list_to_cell(metrics["variant_fact_signals"]),
        "missing_base_signals": _list_to_cell(metrics["missing_base_signals"]),
        "added_variant_signals": _list_to_cell(metrics["added_variant_signals"]),
        "demographic_signals_added": _list_to_cell(metrics["demographic_signals_added"]),
        "reviewer_note": note,
        "gold_label_applied": bool(gold),
    }


def _gold_labels_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "audit"
        / "detention"
        / "validity_gold_labels.jsonl"
    )


def _load_gold_labels() -> dict[str, dict[str, Any]]:
    path = _gold_labels_path()
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = f"{row.get('case_id')}::{row.get('variant_id')}"
        out[key] = row
    return out


def _lookup_gold_label(case_id: str, variant_id: str) -> dict[str, Any] | None:
    return _load_gold_labels().get(f"{case_id}::{variant_id}")


def build_detention_base_text_resolver(counterfactual_df: pd.DataFrame) -> Callable[[str], str]:
    neutral = counterfactual_df[counterfactual_df["variant_type"] == "neutral_he"]
    neutral_by_case = {
        str(row["case_id"]): str(row.get("input_text") or row.get("prompt_input") or "")
        for _, row in neutral.iterrows()
    }

    def resolve(case_id: str) -> str:
        return neutral_by_case.get(case_id, "")

    return resolve


def compute_detention_validity_summary(per_variant: pd.DataFrame) -> pd.DataFrame:
    if per_variant.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for category, grp in per_variant.groupby("validity_category"):
        rows.append(
            {
                "validity_category": category,
                "n_variants": len(grp),
                "mean_fact_preservation_score": round(float(grp["fact_preservation_score"].mean()), 4),
                "n_direct_eligible": int(grp["direct_bias_analysis_eligible"].sum()),
                "n_excluded_from_strict": int(grp["exclude_from_strict_bias_rates"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("n_variants", ascending=False)


def calibrate_validity_against_gold(per_variant: pd.DataFrame) -> dict[str, Any]:
    """Compare heuristic validity to expert gold labels where available."""
    gold = _load_gold_labels()
    if not gold:
        return {"n_gold_labels": 0, "accuracy": None, "notes": "No gold labels file."}

    matched = 0
    correct = 0
    for _, row in per_variant.iterrows():
        key = f"{row['case_id']}::{row['variant_id']}"
        g = gold.get(key)
        if not g:
            continue
        matched += 1
        expected_exclude = not g.get("facts_preserved", True) or g.get("exclude_from_strict", False)
        predicted_exclude = bool(row.get("exclude_from_strict_bias_rates"))
        if expected_exclude == predicted_exclude:
            correct += 1
    accuracy = correct / matched if matched else None
    return {
        "n_gold_labels": len(gold),
        "n_matched": matched,
        "exclude_decision_accuracy": round(accuracy, 4) if accuracy is not None else None,
        "notes": "Calibration compares strict-rate exclusion vs expert facts_preserved labels.",
    }


def run_detention_validity_audit(
    counterfactuals_path: Path,
    *,
    output_suffix: str = "detention",
    results_dir: Path | None = None,
) -> dict[str, Any]:
    cf_df = pd.read_csv(counterfactuals_path)
    resolve_base = build_detention_base_text_resolver(cf_df)
    rows = [
        audit_detention_counterfactual_row(row, resolve_base(str(row.get("case_id", ""))))
        for _, row in cf_df.iterrows()
    ]
    per_variant = pd.DataFrame(rows)
    summary = compute_detention_validity_summary(per_variant)
    calibration = calibrate_validity_against_gold(per_variant)

    root = Path(__file__).resolve().parent.parent.parent
    tables_dir = results_dir or (root / "results" / "tables")
    report_dir = root / "results" / "report"
    tables_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    per_path = tables_dir / f"detention_counterfactual_validity_{output_suffix}.csv"
    summary_path = tables_dir / f"detention_counterfactual_validity_summary_{output_suffix}.csv"
    report_path = report_dir / f"detention_counterfactual_validity_{output_suffix}.md"

    per_variant.to_csv(per_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    report_lines = [
        "# Detention Counterfactual Validity Report",
        "",
        f"Source: `{counterfactuals_path}`",
        "",
        "## Summary",
        "",
    ]
    if not summary.empty:
        for _, srow in summary.iterrows():
            report_lines.append(
                f"- **{srow['validity_category']}**: n={srow['n_variants']}, "
                f"mean preservation={srow['mean_fact_preservation_score']}"
            )
    else:
        report_lines.append("_No rows_")
    report_lines.extend(
        [
            "",
            "## Gold-label calibration",
            "",
            json.dumps(calibration, ensure_ascii=False, indent=2),
            "",
            "**Heuristic screening only — not proof of factual equivalence.**",
        ]
    )
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "per_variant": per_variant,
        "summary": summary,
        "calibration": calibration,
        "paths": {"per_variant": per_path, "summary": summary_path, "report": report_path},
    }


def merge_validity_into_pairwise(
    pairwise_df: pd.DataFrame,
    validity_df: pd.DataFrame,
) -> pd.DataFrame:
    if pairwise_df.empty or validity_df.empty:
        return pairwise_df
    cols = [
        "variant_id",
        "validity_category",
        "fact_preservation_score",
        "direct_bias_analysis_eligible",
        "exclude_from_strict_bias_rates",
        "reviewer_note",
    ]
    valid_cols = [c for c in cols if c in validity_df.columns]
    merged = pairwise_df.merge(validity_df[valid_cols], on="variant_id", how="left", suffixes=("", "_validity"))
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Run detention counterfactual validity audit")
    parser.add_argument(
        "--counterfactuals",
        type=Path,
        default=Path("data/audit/detention/detention_counterfactual_cases.csv"),
    )
    parser.add_argument("--output-suffix", default="detention")
    args = parser.parse_args()
    result = run_detention_validity_audit(args.counterfactuals, output_suffix=args.output_suffix)
    print(f"Wrote {result['paths']['per_variant']}")


if __name__ == "__main__":
    main()
