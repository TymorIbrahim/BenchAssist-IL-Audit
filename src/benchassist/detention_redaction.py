"""Lightweight redaction for detention / remand real-case-inspired material."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

from benchassist.redaction import (
    ADDRESS_HINT_RE,
    CASE_NUMBER_RE,
    EMAIL_RE,
    EN_NAME_RE,
    HEbrew_NAME_RE,
    ID_LIKE_RE,
    PHONE_RE,
    detect_possible_pii,
)

REDACTION_DISCLAIMER = (
    "Automatic lightweight redaction only; manual review is required before publication or model use."
)

RiskLevel = Literal["low", "medium", "high"]

URL_RE = re.compile(r"https?://[^\s\]\)]+", re.IGNORECASE)
BASHAP_RE = re.compile(r'בש"פ\s*\d+/\d+', re.IGNORECASE)
MI_RE = re.compile(r'מ"י\s*\d+/\d+', re.IGNORECASE)


@dataclass
class DetentionRedactionResult:
    redacted_text: str
    pii_redaction_notes: str
    redaction_risk_level: RiskLevel
    manual_review_required: bool = True
    redacted: bool = False
    detected: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _hash_token(value: str, prefix: str = "CASE") -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    return f"[{prefix}_HASH_{digest}]"


def redact_detention_text(
    text: str,
    *,
    hash_case_numbers: bool = False,
    redact_party_names: bool = True,
    redact_urls: bool = True,
) -> DetentionRedactionResult:
    """
    Apply lightweight redaction for detention/remand texts.

    Does not claim complete anonymization.
    """
    if not text:
        return DetentionRedactionResult(
            redacted_text="",
            pii_redaction_notes=REDACTION_DISCLAIMER,
            redaction_risk_level="low",
            manual_review_required=True,
        )

    notes: list[str] = [REDACTION_DISCLAIMER]
    detected = detect_possible_pii(text)
    result = text
    risk: RiskLevel = "low"

    if URL_RE.search(result) and redact_urls:
        result = URL_RE.sub("[REDACTED_URL]", result)
        notes.append("Redacted URL(s).")
        if "url" not in detected:
            detected.append("url")

    if EMAIL_RE.search(result):
        result = EMAIL_RE.sub("[REDACTED_EMAIL]", result)
        notes.append("Redacted email address(es).")
        risk = "medium"

    if PHONE_RE.search(result):
        result = PHONE_RE.sub("[REDACTED_PHONE]", result)
        notes.append("Redacted phone number(s).")
        risk = "medium"

    if ID_LIKE_RE.search(result):
        result = ID_LIKE_RE.sub("[REDACTED_ID]", result)
        notes.append("Redacted ID-like number(s).")
        risk = "medium"

    if hash_case_numbers:
        for pattern in (BASHAP_RE, MI_RE, CASE_NUMBER_RE):
            for match in pattern.finditer(result):
                token = _hash_token(match.group(0))
                result = result.replace(match.group(0), token, 1)
                notes.append("Hashed case number pattern.")
                if "case_number" not in detected:
                    detected.append("case_number")
    elif CASE_NUMBER_RE.search(result) or BASHAP_RE.search(result) or MI_RE.search(result):
        result = BASHAP_RE.sub("[REDACTED_CASE_NO]", result)
        result = MI_RE.sub("[REDACTED_CASE_NO]", result)
        result = CASE_NUMBER_RE.sub("[REDACTED_CASE_NO]", result)
        notes.append("Redacted case number pattern(s).")

    if ADDRESS_HINT_RE.search(result):
        result = ADDRESS_HINT_RE.sub("[REDACTED_ADDRESS]", result)
        notes.append("Redacted address-like fragment(s).")
        risk = "medium"

    if redact_party_names:
        if HEbrew_NAME_RE.search(result):
            result = HEbrew_NAME_RE.sub("[REDACTED_NAME]", result)
            notes.append("Redacted possible Hebrew party/name fragment(s).")
            risk = "high"
        if EN_NAME_RE.search(result):
            result = EN_NAME_RE.sub("[REDACTED_NAME]", result)
            notes.append("Redacted possible English party/name fragment(s).")
            risk = "high"

    if detected:
        risk = "high" if len(detected) >= 3 else ("medium" if len(detected) >= 1 else "low")

    return DetentionRedactionResult(
        redacted_text=result,
        pii_redaction_notes="; ".join(notes),
        redaction_risk_level=risk,
        manual_review_required=True,
        redacted=result != text,
        detected=detected,
        notes=notes,
    )
