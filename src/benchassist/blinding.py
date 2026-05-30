"""Deterministic demographic blinding for counterfactual audit inputs."""

from __future__ import annotations

import copy
import re
from typing import Any

# (pattern, replacement, category, optional preserved_cue label)
_HebrewRule = tuple[str, str, str, str | None]

_HEBREW_RULES: list[_HebrewRule] = [
    (
        "אישה ישראלית אתיופית המתגוררת בדיור ציבורי",
        "בעלת דין המתגוררת בדיור ציבורי",
        "ethnicity",
        "public_housing",
    ),
    (
        "אם חד-הורית ברמת הכנסה נמוכה",
        "הורה יחיד ברמת הכנסה נמוכה",
        "family_status",
        "low_income",
    ),
    (
        "עולה קשישה דוברת רוסית",
        "בעל דין מבוגר שאינו דובר עברית כשפת אם",
        "language_access",
        "elderly",
    ),
    (
        "עולה קשיש דובר רוסית",
        "בעל דין מבוגר שאינו דובר עברית כשפת אם",
        "language_access",
        "elderly",
    ),
    ("דיירת ערביה קשישה", "בעלת דין מבוגרת", "ethnicity", "elderly"),
    ("דייר ערבי קשיש", "בעל דין מבוגר", "ethnicity", "elderly"),
    ("הדיירת פאטמה אבו-חאלד", "בעלת הדין", "name", None),
    ("הדייר אחמד מנסור", "בעל הדין", "name", None),
    ("הדייר דוד כהן", "בעל הדין", "name", None),
    ("הדייר, עובד זר,", "בעל הדין,", "immigration", None),
    ("הדיירת, עובדת זרה,", "בעלת הדין,", "immigration", None),
    ("עולה דוברת רוסית", "בעל דין שאינו דובר עברית כשפת אם", "language_access", None),
    ("אישה ישראלית אתיופית", "בעלת הדין", "ethnicity", None),
    ("פאטמה אבו-חאלד", "בעלת הדין", "name", None),
    ("אחמד מנסור", "בעל הדין", "name", None),
    ("דוד כהן", "בעל הדין", "name", None),
    ("דיירת עם מוגבלות", "בעלת דין עם מוגבלות", "disability", "disability"),
    ("דייר עם מוגבלות", "בעל דין עם מוגבלות", "disability", "disability"),
    ("הדיירת הקשישה", "בעלת דין מבוגרת", "age", "elderly"),
    ("הדייר הקשיש", "בעל דין מבוגר", "age", "elderly"),
    ("עובדת זרה", "בעל הדין", "immigration", None),
    ("עובד זר", "בעל הדין", "immigration", None),
    ("אם חד-הורית", "הורה יחיד", "family_status", "single_parent"),
    ("ערבייה ישראלית", "בעלת הדין", "ethnicity", None),
    ("ערבי ישראלי", "בעל הדין", "ethnicity", None),
    ("יהודייה", "בעלת הדין", "religion", None),
    ("יהודי", "בעל הדין", "religion", None),
    ("ערבייה", "בעלת הדין", "ethnicity", None),
    ("ערבי", "בעל הדין", "ethnicity", None),
    ("דוברת רוסית", "בעל דין שאינו דובר עברית כשפת אם", "language_access", None),
    ("דובר רוסית", "בעל דין שאינו דובר עברית כשפת אם", "language_access", None),
    ("יוצאת אתיופיה", "בעלת הדין", "ethnicity", None),
    ("יוצא אתיופיה", "בעל הדין", "ethnicity", None),
    ("אתיופית", "בעלת הדין", "ethnicity", None),
    ("אתיופי", "בעל הדין", "ethnicity", None),
    ("רוסייה", "בעלת הדין", "nationality", None),
    ("רוסי", "בעל הדין", "nationality", None),
    ("בעלת מוגבלות", "בעלת דין עם מוגבלות", "disability", "disability"),
    ("בעל מוגבלות", "בעל דין עם מוגבלות", "disability", "disability"),
    ("בת 78", "בעל דין מבוגר", "age", "elderly"),
    ("בן 78", "בעל דין מבוגר", "age", "elderly"),
    ("בן 82", "בעל דין מבוגר", "age", "elderly"),
    ("קשישה", "בעלת דין מבוגרת", "age", "elderly"),
    ("קשיש", "בעל דין מבוגר", "age", "elderly"),
]

_ARABIC_RULES: list[tuple[str, str, str]] = [
    ("المستأجرة", "طرف الدعوى", "gender_role"),
    ("المستأجر", "طرف الدعوى", "gender_role"),
]

_TENANT_CLEANUP_PATTERNS: list[tuple[str, str]] = [
    (r"\bהדיירת בעלת הדין\b", "בעלת הדין"),
    (r"\bהדייר בעל הדין\b", "בעל הדין"),
    (r"\bהדיירת, בעלת הדין,\b", "בעלת הדין,"),
    (r"\bהדייר, בעל הדין,\b", "בעל הדין,"),
]


def _empty_metadata(language: str) -> dict[str, Any]:
    return {
        "original_language": language,
        "replacements": [],
        "preserved_cues": [],
        "warning_notes": [],
    }


def _apply_rules(
    text: str,
    rules: list[tuple[str, str, str] | _HebrewRule],
    metadata: dict[str, Any],
) -> str:
    result = text
    for rule in rules:
        if len(rule) == 4:
            original, replacement, category, preserved = rule
        else:
            original, replacement, category = rule
            preserved = None

        if original not in result:
            continue
        result = result.replace(original, replacement)
        metadata["replacements"].append(
            {
                "original": original,
                "replacement": replacement,
                "category": category,
            }
        )
        if preserved and preserved not in metadata["preserved_cues"]:
            metadata["preserved_cues"].append(preserved)
    return result


def _blind_hebrew(text: str, metadata: dict[str, Any]) -> str:
    blinded = _apply_rules(text, _HEBREW_RULES, metadata)
    for pattern, replacement in _TENANT_CLEANUP_PATTERNS:
        if re.search(pattern, blinded):
            updated = re.sub(pattern, replacement, blinded)
            if updated != blinded:
                metadata["replacements"].append(
                    {
                        "original": pattern,
                        "replacement": replacement,
                        "category": "cleanup",
                    }
                )
                blinded = updated

    if "מוגבלות" in blinded and "disability" not in metadata["preserved_cues"]:
        metadata["preserved_cues"].append("disability")
    if "דיור ציבורי" in blinded and "public_housing" not in metadata["preserved_cues"]:
        metadata["preserved_cues"].append("public_housing")
    if "ילדים" in blinded or "ילד" in blinded:
        if "family_with_children" not in metadata["preserved_cues"]:
            metadata["preserved_cues"].append("family_with_children")
    return blinded


def _blind_arabic(text: str, metadata: dict[str, Any]) -> str:
    blinded = _apply_rules(text, _ARABIC_RULES, metadata)
    if not metadata["replacements"]:
        metadata["warning_notes"].append(
            "Arabic blinding is limited in v1; only common variant phrases were neutralized."
        )
    return blinded


def blind_demographic_cues(text: str, language: str = "he") -> tuple[str, dict]:
    """Blind demographic identity cues while preserving legally relevant vulnerability cues.

    Args:
        text: Original case summary text.
        language: Input language code (``he``, ``ar``, or other).

    Returns:
        ``(blinded_text, metadata)`` where metadata documents replacements and
        preserved neutral vulnerability cues.
    """
    lang = (language or "he").strip().lower()
    metadata = _empty_metadata(lang)
    if not text.strip():
        return text, metadata

    if lang == "ar":
        return _blind_arabic(text, metadata), metadata
    if lang.startswith("he"):
        return _blind_hebrew(text, metadata), metadata

    metadata["warning_notes"].append(
        f"No blinding rules for language {language!r}; text returned unchanged."
    )
    return text, metadata


def metadata_without_duplicates(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of metadata with de-duplicated preserved cues."""
    cleaned = copy.deepcopy(metadata)
    cleaned["preserved_cues"] = list(dict.fromkeys(cleaned.get("preserved_cues", [])))
    return cleaned
