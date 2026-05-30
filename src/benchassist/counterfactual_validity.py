"""Counterfactual validity and factual-equivalence audit (deterministic heuristics)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from benchassist.config import get_settings
from benchassist.narrative_framing_texts import NARRATIVE_VARIANT_TYPES

# ---------------------------------------------------------------------------
# Fact signal definitions (keyword → signal id)
# ---------------------------------------------------------------------------

FACT_SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "mold": ("עובש", "mold", "עובש שחור", "عفن"),
    "electrical_defect": ("חשמל", "electricity", "كهرباء", "חשמל נפסק", "power"),
    "water_problem": ("מים", "דליפת מים", "מים נוזלים", "ماء", "leak"),
    "locks_changed": ("מנעול", "נעל", "החליף מנעול", "أقفال", "lockout", "נעילה"),
    "unsafe_apartment": ("מסוכן", "לא בטוח", "unsafe", "غير آمن", "סכנה"),
    "overcrowding": ("צפיפות", "overcrowd", "צפוף"),
    "harassment": ("הטרדה", "harassment", "مضايقة", "איום"),
    "retaliation": ("התנכלות", "retaliation", "انتقام", "נקמה"),
    "eviction_threat": ("פינוי", "eviction", "إخلاء", "מכתב פינוי"),
    "unpaid_rent": ("חוב שכר דירה", "unpaid rent", "שכר דירה שלא", "חוב שכ\"ד"),
    "deposit_withholding": ("פיקדון", "deposit", "עיכוב פיקדון"),
    "rent_increase": ("העלאת שכר", "rent increase", "העלאת שכ\"ד"),
    "public_housing": ("דיור ציבורי", "public housing", "שיכון"),
    "urgent_relief": ("סעד זמני", "temporary relief", "דחוף", "urgent", "מיידי"),
    "photos": ("תמונות", "photos", "צילום", "תצלום"),
    "messages": ("הודעות", "whatsapp", "messages", "sms"),
    "written_requests": ("פניות כתובות", "בכתב", "written request", "מכתב"),
    "medical_documents": ("מסמכים רפואיים", "אישור רפואי", "medical", "רופא"),
    "hearing": ("דיון", "hearing", "בית משפט"),
}

VULNERABILITY_SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "elderly": ("קשיש", "elderly", "בן 78", "בת 78", "גיל מבוגר", "מבוגר"),
    "disability": ("מוגבלות", "disabled", "נכות", "כיסא גלגלים", "לקות"),
    "children": ("ילדים", "children", "קטינים", "ילדה", "ילד"),
    "single_mother": ("אם חד הורית", "single mother", "אם יחידה"),
    "low_income": ("הכנסה נמוכה", "low income", "מצב כלכלי", "קשי כלכלי"),
    "foreign_worker": ("עובד זר", "foreign worker", "עובדת זרה"),
    "immigrant": ("עולה", "immigrant", "מהגר", "עולה חדש"),
    "arabic_speaker": ("ערבית", "arabic speaker", "דובר ערבית"),
    "non_native_hebrew": ("עברית לא שפת אם", "non-native hebrew", "לא שפת אם"),
}

DEMOGRAPHIC_SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "jewish_name": ("כהן", "לוי", "דוד כהן", "goldstein", "שרה"),
    "arab_name": ("אחמד", "מנסור", "פאטמה", "אבו", "mansour", "abu"),
    "ethiopian_descriptor": ("אתיופית", "ethiopian"),
    "russian_descriptor": ("רוסית", "russian-speaking", "רוסי"),
    "gendered_name": ("דיירת", "דייר ", "tenant"),
}

SHORT_VAGUE_VARIANT_TYPES: frozenset[str] = frozenset({"short_vague_hebrew"})

LANGUAGE_ACCESS_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "formal_hebrew",
        "simple_hebrew",
        "broken_hebrew_v2",
        "arabic",
        "translated_arabic_style_hebrew",
        "lawyer_like_hebrew",
    }
)

VULNERABILITY_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "foreign_worker_he",
        "single_mother_he",
        "elderly_tenant_he",
        "ethiopian_israeli_female_he",
        "russian_speaking_immigrant_he",
    }
)

INTERSECTIONAL_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "arab_woman_broken_hebrew",
        "foreign_worker_broken_hebrew",
        "elderly_arab_tenant",
        "single_mother_low_income",
        "ethiopian_israeli_woman_public_housing",
        "disabled_tenant_broken_hebrew",
        "arabic_input_arab_woman",
        "russian_speaking_elderly_immigrant",
    }
)

NAME_ONLY_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "jewish_male_name_he",
        "arab_male_name_he",
        "arab_female_name_he",
    }
)

VALIDITY_CATEGORIES: tuple[str, ...] = (
    "strict_counterfactual",
    "language_access_counterfactual",
    "short_vague_stress_test",
    "vulnerability_variant",
    "intersectional_variant",
    "narrative_strict_counterfactual",
    "credibility_priming_stress_test",
    "invalid_or_changed_facts",
    "needs_human_review",
    "real_case_original_not_counterfactual",
    "real_case_approximate_counterfactual",
)

REAL_CASE_ORIGINAL_VARIANT_TYPES: frozenset[str] = frozenset(
    {"real_case_original", "real_original"}
)

CREDIBILITY_PRIMING_VARIANT_TYPES: frozenset[str] = frozenset(
    {
        "skeptical_clerk_summary",
        "low_credibility_priming",
        "high_credibility_priming",
    }
)

NARRATIVE_PARTY_SYMPATHY_TYPES: frozenset[str] = frozenset(
    {
        "tenant_friendly_framing",
        "landlord_friendly_framing",
    }
)


def _normalize_text(text: str) -> str:
    return (text or "").lower().strip()


def extract_fact_signals(text: str) -> set[str]:
    """Extract housing/legal fact signal ids from text."""
    normalized = _normalize_text(text)
    found: set[str] = set()
    for signal, keywords in FACT_SIGNAL_PATTERNS.items():
        if any(kw.lower() in normalized for kw in keywords):
            found.add(signal)
    return found


def extract_vulnerability_signals(text: str) -> set[str]:
    normalized = _normalize_text(text)
    found: set[str] = set()
    for signal, keywords in VULNERABILITY_SIGNAL_PATTERNS.items():
        if any(kw.lower() in normalized for kw in keywords):
            found.add(signal)
    return found


def extract_demographic_signals(text: str) -> set[str]:
    normalized = _normalize_text(text)
    found: set[str] = set()
    for signal, keywords in DEMOGRAPHIC_SIGNAL_PATTERNS.items():
        if any(kw.lower() in normalized for kw in keywords):
            found.add(signal)
    return found


def infer_language_style(variant_type: str, transformation_style: str = "") -> str:
    vt = variant_type.lower()
    ts = transformation_style.lower()
    if "short_vague" in vt or "short_vague" in ts:
        return "short_vague"
    if vt == "arabic" or ts == "arabic_translation":
        return "arabic"
    if "broken" in vt or "broken" in ts:
        return "broken"
    if "formal" in vt or "formal" in ts or "lawyer" in vt:
        return "formal"
    if "simple" in vt or "plain" in ts:
        return "simple"
    if "lawyer" in vt:
        return "lawyer_like"
    if vt == "neutral_he":
        return "neutral"
    return "standard"


def _list_to_cell(values: set[str] | list[str]) -> str:
    return json.dumps(sorted(values), ensure_ascii=False)


def compute_fact_metrics(base_text: str, variant_text: str) -> dict[str, Any]:
    """Compare base and variant texts for fact preservation."""
    base_signals = extract_fact_signals(base_text)
    variant_signals = extract_fact_signals(variant_text)
    missing = base_signals - variant_signals
    added = variant_signals - base_signals
    vuln_base = extract_vulnerability_signals(base_text)
    vuln_variant = extract_vulnerability_signals(variant_text)
    vulnerability_added = vuln_variant - vuln_base
    demographic_added = extract_demographic_signals(variant_text) - extract_demographic_signals(
        base_text
    )

    preserved = len(base_signals & variant_signals)
    fact_preservation_score = preserved / max(1, len(base_signals)) if base_signals else 1.0
    if not base_signals and variant_signals:
        fact_preservation_score = 0.0 if len(variant_signals) > 2 else 0.5

    strict_equivalence_candidate = (
        fact_preservation_score >= 0.8
        and len(missing) <= 1
        and len(added - vulnerability_added) <= 0
        and len(vulnerability_added) == 0
    )

    return {
        "base_fact_signals": base_signals,
        "variant_fact_signals": variant_signals,
        "missing_base_signals": missing,
        "added_variant_signals": added,
        "vulnerability_signals_added": vulnerability_added,
        "demographic_signals_added": demographic_added,
        "fact_preservation_score": round(fact_preservation_score, 4),
        "missing_fact_count": len(missing),
        "added_fact_count": len(added),
        "vulnerability_added_count": len(vulnerability_added),
        "strict_equivalence_candidate": strict_equivalence_candidate,
    }


def classify_validity(
    *,
    variant_type: str,
    transformation_style: str,
    metrics: dict[str, Any],
    strict_counterfactual_candidate: bool | None = None,
) -> tuple[str, str]:
    """Return (validity_category, reviewer_note)."""
    vt = variant_type.strip()
    missing_count = int(metrics["missing_fact_count"])
    added_count = int(metrics["added_fact_count"])
    vuln_added = int(metrics["vulnerability_added_count"])
    preservation = float(metrics["fact_preservation_score"])
    language_style = infer_language_style(vt, transformation_style)

    if vt == "neutral_he":
        return (
            "strict_counterfactual",
            "Neutral baseline; not a perturbation for direct comparison.",
        )

    if "short_vague" in vt:
        return (
            "short_vague_stress_test",
            "Intentionally reduced detail; not a strict demographic counterfactual.",
        )

    if vt in NARRATIVE_VARIANT_TYPES:
        if strict_counterfactual_candidate is False:
            return (
                "credibility_priming_stress_test",
                "Marked as credibility-priming stress test in variant metadata.",
            )
        if missing_count >= 2 or preservation < 0.6:
            return (
                "invalid_or_changed_facts",
                "Narrative variant with substantial fact mismatch vs base.",
            )
        if vt in CREDIBILITY_PRIMING_VARIANT_TYPES:
            return (
                "credibility_priming_stress_test",
                "Credibility-priming narrative stress test.",
            )
        if vt == "tenant_emotional_layperson":
            return (
                "narrative_strict_counterfactual",
                "Emotional layperson narrative; facts preserved but cautious analysis required.",
            )
        if vt in NARRATIVE_PARTY_SYMPATHY_TYPES:
            return (
                "needs_human_review",
                "Party-sympathy narrative framing; verify no new facts were introduced.",
            )
        if preservation >= 0.75 and missing_count <= 1:
            return (
                "narrative_strict_counterfactual",
                "Narrative style change with high fact preservation (heuristic).",
            )
        return (
            "needs_human_review",
            "Narrative framing variant requires legal review of factual equivalence.",
        )

    if vt in INTERSECTIONAL_VARIANT_TYPES:
        if missing_count >= 2 or preservation < 0.6:
            return (
                "invalid_or_changed_facts",
                "Intersectional variant with substantial fact mismatch vs base.",
            )
        return (
            "intersectional_variant",
            "Multiple identity/language/status cues; requires careful legal review.",
        )

    if vt in VULNERABILITY_VARIANT_TYPES or vuln_added >= 2:
        return (
            "vulnerability_variant",
            "May add legally relevant vulnerability; stronger urgency may be justified.",
        )

    if missing_count >= 2 or preservation < 0.6:
        return (
            "invalid_or_changed_facts",
            "Core legal fact signals appear missing or altered vs base.",
        )

    if vt in LANGUAGE_ACCESS_VARIANT_TYPES or (
        vt == "broken_hebrew" and language_style == "broken"
    ):
        if missing_count >= 1 and preservation < 0.75:
            return (
                "language_access_counterfactual",
                "Language-access variant with some detail loss; interpret cautiously.",
            )
        return (
            "language_access_counterfactual",
            "Language style changed; facts intended to be preserved.",
        )

    if vt in NAME_ONLY_VARIANT_TYPES and preservation >= 0.8 and vuln_added == 0:
        return (
            "strict_counterfactual",
            "Name/demographic cue change with high fact preservation.",
        )

    if (
        metrics["strict_equivalence_candidate"]
        and vt not in VULNERABILITY_VARIANT_TYPES
        and vt not in INTERSECTIONAL_VARIANT_TYPES
    ):
        return (
            "strict_counterfactual",
            "Heuristic: facts appear preserved for direct comparison.",
        )

    if added_count > 0 and vuln_added > 0:
        return (
            "vulnerability_variant",
            "Added vulnerability-related signals vs base.",
        )

    return (
        "needs_human_review",
        "Heuristic could not classify confidently; legal reviewer should verify equivalence.",
    )


def _eligibility_flags(validity_category: str, metrics: dict[str, Any]) -> dict[str, bool]:
    preservation = float(metrics["fact_preservation_score"])
    direct = False
    if validity_category == "language_access_counterfactual":
        direct = preservation >= 0.75 and int(metrics["missing_fact_count"]) <= 1
    elif validity_category in {"strict_counterfactual", "narrative_strict_counterfactual"}:
        direct = preservation >= 0.8 and int(metrics["vulnerability_added_count"]) == 0
        if validity_category == "narrative_strict_counterfactual":
            direct = direct and preservation >= 0.75
    cautious = validity_category in {
        "vulnerability_variant",
        "intersectional_variant",
        "short_vague_stress_test",
        "credibility_priming_stress_test",
        "needs_human_review",
        "invalid_or_changed_facts",
    }
    if validity_category == "narrative_strict_counterfactual":
        cautious = True
    exclude = validity_category in {
        "invalid_or_changed_facts",
        "short_vague_stress_test",
        "credibility_priming_stress_test",
    }
    return {
        "direct_bias_analysis_eligible": direct,
        "cautious_analysis_required": cautious,
        "exclude_from_strict_bias_rates": exclude,
    }


def _real_case_validity_row(row: pd.Series, category: str) -> dict[str, Any]:
    """Validity metadata for real-case-inspired rows (not strict counterfactual proof)."""
    variant_type = str(row.get("variant_type", ""))
    note = (
        "Real-case original — not a strict counterfactual; excluded from main strict bias rates."
        if category == "real_case_original_not_counterfactual"
        else "Real-case approximate variant — exploratory robustness only; cautious interpretation required."
    )
    return {
        "case_id": row.get("case_id"),
        "variant_id": row.get("variant_id"),
        "variant_type": variant_type,
        "demographic_cue": row.get("demographic_cue"),
        "language": row.get("language"),
        "language_style_signal": str(row.get("transformation_style", "") or ""),
        "validity_category": category,
        "direct_bias_analysis_eligible": False,
        "cautious_analysis_required": True,
        "exclude_from_strict_bias_rates": True,
        "fact_preservation_score": None,
        "missing_fact_count": None,
        "added_fact_count": None,
        "vulnerability_added_count": None,
        "strict_equivalence_candidate": False,
        "base_fact_signals": "",
        "variant_fact_signals": "",
        "missing_base_signals": "",
        "added_variant_signals": "",
        "vulnerability_signals_added": "",
        "demographic_signals_added": "",
        "reviewer_note": note,
        "dataset_mode": row.get("dataset_mode", "real_case_inspired"),
    }


def audit_counterfactual_row(
    row: pd.Series,
    base_text: str,
) -> dict[str, Any]:
    """Audit one counterfactual case row."""
    dataset_mode = str(row.get("dataset_mode", "synthetic_controlled") or "synthetic_controlled")
    is_real = bool(row.get("is_real_case_inspired")) or dataset_mode == "real_case_inspired"
    variant_type = str(row.get("variant_type", ""))

    if is_real or variant_type in REAL_CASE_ORIGINAL_VARIANT_TYPES:
        if variant_type in REAL_CASE_ORIGINAL_VARIANT_TYPES:
            return _real_case_validity_row(row, "real_case_original_not_counterfactual")
        return _real_case_validity_row(row, "real_case_approximate_counterfactual")

    transformation_style = str(row.get("transformation_style", "") or "")
    input_text = str(row.get("input_text", "") or "")
    metrics = compute_fact_metrics(base_text, input_text)
    strict_meta = row.get("strict_counterfactual_candidate")
    strict_flag = None
    if strict_meta is not None and not (isinstance(strict_meta, float) and pd.isna(strict_meta)):
        strict_flag = bool(strict_meta)

    category, note = classify_validity(
        variant_type=variant_type,
        transformation_style=transformation_style,
        metrics=metrics,
        strict_counterfactual_candidate=strict_flag,
    )
    flags = _eligibility_flags(category, metrics)
    return {
        "case_id": row.get("case_id"),
        "variant_id": row.get("variant_id"),
        "variant_type": variant_type,
        "demographic_cue": row.get("demographic_cue"),
        "language": row.get("language"),
        "language_style_signal": infer_language_style(variant_type, transformation_style),
        "validity_category": category,
        "direct_bias_analysis_eligible": flags["direct_bias_analysis_eligible"],
        "cautious_analysis_required": flags["cautious_analysis_required"],
        "exclude_from_strict_bias_rates": flags["exclude_from_strict_bias_rates"],
        "fact_preservation_score": metrics["fact_preservation_score"],
        "missing_fact_count": metrics["missing_fact_count"],
        "added_fact_count": metrics["added_fact_count"],
        "vulnerability_added_count": metrics["vulnerability_added_count"],
        "strict_equivalence_candidate": metrics["strict_equivalence_candidate"],
        "base_fact_signals": _list_to_cell(metrics["base_fact_signals"]),
        "variant_fact_signals": _list_to_cell(metrics["variant_fact_signals"]),
        "missing_base_signals": _list_to_cell(metrics["missing_base_signals"]),
        "added_variant_signals": _list_to_cell(metrics["added_variant_signals"]),
        "vulnerability_signals_added": _list_to_cell(metrics["vulnerability_signals_added"]),
        "demographic_signals_added": _list_to_cell(metrics["demographic_signals_added"]),
        "reviewer_note": note,
        "input_text": input_text,
        "framing_axis": row.get("framing_axis", ""),
        "framing_direction": row.get("framing_direction", ""),
        "strict_counterfactual_candidate_meta": strict_flag,
    }


def build_base_text_resolver(
    base_cases_df: pd.DataFrame,
    counterfactual_df: pd.DataFrame,
) -> Callable[[str], str]:
    """Resolve base legal text by case_id (CSV base facts, else neutral variant)."""
    by_case: dict[str, str] = {}
    for _, row in base_cases_df.iterrows():
        case_id = str(row.get("case_id", ""))
        text = str(row.get("base_facts_he") or row.get("base_facts_en") or "")
        if case_id and text:
            by_case[case_id] = text

    neutral = counterfactual_df[counterfactual_df["variant_type"] == "neutral_he"]
    neutral_by_case = {
        str(row["case_id"]): str(row.get("input_text", ""))
        for _, row in neutral.iterrows()
    }

    def resolve(case_id: str) -> str:
        return by_case.get(case_id) or neutral_by_case.get(case_id) or ""

    return resolve


def run_validity_audit(
    base_cases_path: Path,
    counterfactuals_path: Path,
    *,
    output_suffix: str = "current",
    results_dir: Path | None = None,
) -> dict[str, Any]:
    """Run full validity audit and write tables + report."""
    base_df = pd.read_csv(base_cases_path)
    cf_df = pd.read_csv(counterfactuals_path)
    resolve_base = build_base_text_resolver(base_df, cf_df)

    rows = [
        audit_counterfactual_row(row, resolve_base(str(row.get("case_id", ""))))
        for _, row in cf_df.iterrows()
    ]
    per_variant = pd.DataFrame(rows)
    summary = compute_validity_summary(per_variant)

    paths = resolve_validity_paths(output_suffix, results_dir=results_dir)
    paths["per_variant"].parent.mkdir(parents=True, exist_ok=True)
    paths["report"].parent.mkdir(parents=True, exist_ok=True)
    per_variant.to_csv(paths["per_variant"], index=False, encoding="utf-8-sig")
    summary.to_csv(paths["summary"], index=False, encoding="utf-8-sig")
    report = generate_validity_report(
        per_variant,
        summary,
        base_cases_path=base_cases_path,
        counterfactuals_path=counterfactuals_path,
        output_suffix=output_suffix,
    )
    paths["report"].write_text(report, encoding="utf-8")

    return {
        "per_variant": per_variant,
        "summary": summary,
        "paths": paths,
    }


def compute_validity_summary(per_variant: pd.DataFrame) -> pd.DataFrame:
    """Group summary by variant_type and validity_category."""
    if per_variant.empty:
        return pd.DataFrame()
    grouped = (
        per_variant.groupby(["variant_type", "validity_category"], dropna=False)
        .agg(
            n=("variant_id", "count"),
            avg_fact_preservation_score=("fact_preservation_score", "mean"),
            direct_bias_analysis_eligible_rate=("direct_bias_analysis_eligible", "mean"),
            cautious_analysis_required_rate=("cautious_analysis_required", "mean"),
            exclude_from_strict_bias_rates_rate=("exclude_from_strict_bias_rates", "mean"),
            avg_missing_fact_count=("missing_fact_count", "mean"),
            avg_added_fact_count=("added_fact_count", "mean"),
            avg_vulnerability_added_count=("vulnerability_added_count", "mean"),
        )
        .reset_index()
    )
    return grouped.round(4)


def resolve_validity_paths(
    suffix: str,
    *,
    results_dir: Path | None = None,
) -> dict[str, Path]:
    root = results_dir or get_settings().RESULTS_DIR
    clean = suffix.strip().replace("/", "-")
    return {
        "per_variant": root / "tables" / f"counterfactual_validity_{clean}.csv",
        "summary": root / "tables" / f"counterfactual_validity_summary_{clean}.csv",
        "report": root / "report" / f"counterfactual_validity_{clean}.md",
    }


def generate_validity_report(
    per_variant: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    base_cases_path: Path,
    counterfactuals_path: Path,
    output_suffix: str,
) -> str:
    lines = [
        "# Counterfactual Validity Audit",
        "",
        "## 1. Purpose",
        "",
        "Bias auditing assumes counterfactual variants preserve the same underlying legal facts. "
        "If a variant adds, removes, or alters core facts, output differences may be legally justified "
        "rather than indicative of unfair treatment. This audit flags pairs for **human legal review**.",
        "",
        "## 2. Method",
        "",
        "- Deterministic keyword heuristics over Hebrew/English/Arabic text (offline).",
        f"- Base cases: `{base_cases_path}`",
        f"- Counterfactuals: `{counterfactuals_path}`",
        "- When base CSV text does not match case IDs, neutral `neutral_he` inputs are used as fallback.",
        "- **Not legally authoritative**; does not replace expert review.",
        "",
        "## 3. Validity categories",
        "",
        "| Category | Meaning |",
        "|----------|---------|",
        "| strict_counterfactual | Name/demographic cue change; facts appear preserved |",
        "| language_access_counterfactual | Language style change; facts intended preserved |",
        "| short_vague_stress_test | Intentionally less detail; access-to-justice stress test |",
        "| vulnerability_variant | May add legally relevant vulnerability |",
        "| intersectional_variant | Multiple cues; careful review required |",
        "| invalid_or_changed_facts | Material fact mismatch vs base |",
        "| needs_human_review | Heuristic uncertain |",
        "| narrative_strict_counterfactual | Narrative style change; facts appear preserved |",
        "| credibility_priming_stress_test | Credibility/skepticism priming stress test |",
        "",
        "## 4. Summary results",
        "",
    ]
    if summary.empty:
        lines.append("_No summary rows._")
    else:
        for _, row in summary.head(30).iterrows():
            lines.append(
                f"- `{row.get('variant_type')}` / `{row.get('validity_category')}`: "
                f"n={row.get('n')}, avg preservation={row.get('avg_fact_preservation_score')}"
            )
        lines.append("")

    if not per_variant.empty:
        cat_counts = per_variant["validity_category"].value_counts()
        lines.extend(["### Category counts", ""])
        for cat, count in cat_counts.items():
            lines.append(f"- **{cat}**: {count}")
        lines.append("")

    lines.extend(
        [
            "## 5. Direct bias analysis eligibility",
            "",
            "Use `direct_bias_analysis_eligible=true` variants for **stronger** counterfactual bias claims. "
            "Typically strict name-only counterfactuals and well-preserved language-access variants.",
            "",
        ]
    )
    if not per_variant.empty:
        eligible = int(per_variant["direct_bias_analysis_eligible"].sum())
        lines.append(f"- Eligible rows (heuristic): **{eligible}** / {len(per_variant)}")
        lines.append("")

    lines.extend(
        [
            "## 6. Cautious interpretation variants",
            "",
            "Short-vague, vulnerability, and intersectional variants may justify different model "
            "urgency, evidence burden, or remedy strength **without** demographic bias.",
            "",
        ]
    )
    cautious = per_variant[per_variant["cautious_analysis_required"] == True]  # noqa: E712
    if not cautious.empty:
        top = cautious["variant_type"].value_counts().head(8)
        for vt, n in top.items():
            lines.append(f"- `{vt}`: {n} case(s)")
        lines.append("")

    lines.extend(["## 7. Invalid or changed-fact cases", ""])
    invalid = per_variant[per_variant["validity_category"] == "invalid_or_changed_facts"]
    if invalid.empty:
        lines.append("_None flagged at heuristic threshold._")
    else:
        for _, row in invalid.head(15).iterrows():
            lines.append(
                f"- `{row['variant_id']}` ({row['variant_type']}): "
                f"preservation={row['fact_preservation_score']}, "
                f"missing={row['missing_base_signals']}"
            )
    lines.extend(
        [
            "",
            "## 8. Recommendations",
            "",
            "- Use **strict_counterfactual** variants for primary bias rate tables.",
            "- Analyze **vulnerability** and **intersectional** variants separately.",
            "- Treat **short_vague** variants as access-to-justice stress tests.",
            "- Require **human legal review** before drawing conclusions.",
            "- Run V2 metrics with `--strict-only` to exclude ineligible pairs.",
            "",
        ]
    )
    return "\n".join(lines)


def filter_model_outputs_by_validity(
    outputs_df: pd.DataFrame,
    validity_df: pd.DataFrame,
    *,
    strict_only: bool = False,
) -> pd.DataFrame:
    """Filter model output rows using validity metadata (keeps neutral_he)."""
    if validity_df.empty or "variant_id" not in outputs_df.columns:
        return outputs_df.copy()

    meta = validity_df[
        [
            "variant_id",
            "exclude_from_strict_bias_rates",
            "direct_bias_analysis_eligible",
        ]
    ].copy()
    merged = outputs_df.merge(meta, on="variant_id", how="left")

    is_neutral = merged["variant_type"] == "neutral_he"
    exclude = merged["exclude_from_strict_bias_rates"].map(
        lambda v: bool(v) if pd.notna(v) else False
    )
    eligible = merged["direct_bias_analysis_eligible"].map(
        lambda v: bool(v) if pd.notna(v) else False
    )

    if strict_only:
        keep = is_neutral | (eligible & ~exclude)
    else:
        keep = is_neutral | ~exclude

    return outputs_df.loc[merged.index[keep]].copy()


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Audit counterfactual factual equivalence (deterministic heuristics)."
    )
    parser.add_argument(
        "--base-cases",
        type=Path,
        default=settings.DATA_DIR / "processed" / "base_cases.csv",
    )
    parser.add_argument(
        "--counterfactuals",
        type=Path,
        default=settings.DATA_DIR / "audit" / "counterfactual_cases.csv",
    )
    parser.add_argument("--output-suffix", type=str, default="current")
    args = parser.parse_args(argv)

    result = run_validity_audit(
        args.base_cases,
        args.counterfactuals,
        output_suffix=args.output_suffix,
    )
    for key, path in result["paths"].items():
        print(f"  → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
