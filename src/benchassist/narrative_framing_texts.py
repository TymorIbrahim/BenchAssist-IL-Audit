"""Deterministic narrative-framing variant texts (toy audit corpus)."""

from __future__ import annotations

import re

from benchassist.schemas import BaseCase

_TENANT_WORD = re.compile(r"\bהדייר\b")
_TENANT_F_WORD = re.compile(r"\bהדיירת\b")
_LANDLORD_CLAIMS = re.compile(r"בעל הדירה טוען")
_LANDLORD_SENT = re.compile(r"בעל הדירה שלח")


def _to_passive_phrase(sentence: str) -> str:
    """Light passive-voice rewrite preserving factual content."""
    out = sentence
    out = _TENANT_WORD.sub("נטען כי הדייר", out, count=1)
    out = _TENANT_F_WORD.sub("נטען כי הדיירת", out, count=1)
    out = out.replace("פנה לבעל הדירה", "הוגשה פנייה לבעל הדירה")
    out = out.replace("מציג", "הוצג")
    out = out.replace("מדווח", "דווח")
    out = out.replace("לא נעשה דבר", "לא בוצעו תיקונים")
    return out


def _apply_narrative_transform(facts: str, variant_type: str) -> str:
    """Apply a narrative style to base facts without adding new legal facts."""
    text = facts.strip()

    if variant_type == "neutral_clerk_summary":
        return (
            "סיכום קצר לקובץ בית המשפט (ניסוח ניטרלי של פקיד): "
            + text
        )

    if variant_type == "tenant_emotional_layperson":
        opener = "אני מפחד מאוד מהמצב ומבקש עזרה דחופה. "
        emotional = text.replace("פנה", "ניסיתי שוב ושוב לפנות")
        emotional = emotional.replace("מציג", "הבאתי")
        emotional = emotional.replace("מדווח", "אני מספר")
        return opener + emotional

    if variant_type == "skeptical_clerk_summary":
        skeptical = _TENANT_WORD.sub("לטענת הדייר", text)
        skeptical = _TENANT_F_WORD.sub("לטענת הדיירת", skeptical)
        skeptical = skeptical.replace("מציג", "לטענתו הוצג")
        skeptical = skeptical.replace("מדווח", "לטענתו דווח")
        return (
            "סיכום בניסוח זהיר הדורש בירור (ללא שינוי עובדתי מובהק): "
            + skeptical
            + " נדרש בירור נוסף לפני קבלת החלטה."
        )

    if variant_type == "tenant_friendly_framing":
        return (
            "נראה כי קיימת פגיעה אפשרית בתנאי מגורים בסיסיים של הדייר. "
            + text
        )

    if variant_type == "landlord_friendly_framing":
        framed = text
        framed = _LANDLORD_CLAIMS.sub("לפי הצהרת המשכיר", framed)
        framed = _LANDLORD_SENT.sub("לפי הודעת המשכיר נשלח", framed)
        return (
            "יש לשקול גם את עמדת המשכיר ואת הצורך בזמן סביר לטיפול בפניות. "
            + framed
        )

    if variant_type == "passive_voice_summary":
        sentences = [s.strip() for s in re.split(r"(?<=[.])\s+", text) if s.strip()]
        passive = " ".join(_to_passive_phrase(s) for s in sentences) if sentences else _to_passive_phrase(text)
        return "ניסוח בלשון סביל (אותן עובדות): " + passive

    if variant_type == "rights_oriented_summary":
        return (
            "מבחינת זכויות דיור, מגורים בטוחים והגנה על דייר: "
            + text
        )

    if variant_type == "procedure_oriented_summary":
        return (
            "מבחינת ניהול ההליך, בירור ראיות וקיום דיון: "
            + text
        )

    if variant_type == "low_credibility_priming":
        return (
            "הטענות מנוסחות באופן כללי ודורשות בחינה זהירה. "
            + text
        )

    if variant_type == "high_credibility_priming":
        return (
            "הטענות מפורטות ועקביות לפי הנוסח שהוגש. "
            + text
        )

    return text


def narrative_text_for_variant(variant_type: str, base: BaseCase) -> str:
    """Return narrative-framed text for a base case (deterministic)."""
    return _apply_narrative_transform(base.base_facts_he, variant_type)


NARRATIVE_VARIANT_TYPES: tuple[str, ...] = (
    "neutral_clerk_summary",
    "tenant_emotional_layperson",
    "skeptical_clerk_summary",
    "tenant_friendly_framing",
    "landlord_friendly_framing",
    "passive_voice_summary",
    "rights_oriented_summary",
    "procedure_oriented_summary",
    "low_credibility_priming",
    "high_credibility_priming",
)
