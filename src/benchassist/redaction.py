"""Deterministic lightweight PII redaction for real-case-inspired summaries."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+972|0)[\s\-]?(?:5\d|[23489])[\s\-]?\d{3}[\s\-]?\d{4}(?!\d)"
)
ID_LIKE_RE = re.compile(r"\b\d{8,9}\b")
CASE_NUMBER_RE = re.compile(r"\b(?:ת\.?א\.?|ע\"?פ|CR|Case)\s*[\d\-/]+\b", re.IGNORECASE)
ADDRESS_HINT_RE = re.compile(
    r"(?:רח(?:וב)?|שדר(?:ות)?|street|st\.)\s+[\w\u0590-\u05FF\u0600-\u06FF\d\-]+",
    re.IGNORECASE,
)
HEbrew_NAME_RE = re.compile(
    r"\b(?:מר|גב'?|ה'?)?\s*(?:[א-ת]{2,}\s+[א-ת]{2,})\b"
)
EN_NAME_RE = re.compile(r"\b(?:Mr\.|Ms\.|Mrs\.)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


@dataclass
class RedactionResult:
    text: str
    redacted: bool
    notes: list[str] = field(default_factory=list)
    detected: list[str] = field(default_factory=list)


def make_source_hash(text: str) -> str:
    """Stable short hash for source_id when raw ids are sensitive."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"src_{digest[:12]}"


def detect_possible_pii(text: str) -> list[str]:
    """Return list of PII type labels detected (heuristic)."""
    if not text:
        return []
    found: list[str] = []
    if EMAIL_RE.search(text):
        found.append("email")
    if PHONE_RE.search(text):
        found.append("phone")
    if ID_LIKE_RE.search(text):
        found.append("id_like_number")
    if CASE_NUMBER_RE.search(text):
        found.append("case_number")
    if ADDRESS_HINT_RE.search(text):
        found.append("address_hint")
    if HEbrew_NAME_RE.search(text) or EN_NAME_RE.search(text):
        found.append("possible_name")
    return found


def redact_text(text: str, *, redact_names: bool = True) -> RedactionResult:
    """Apply deterministic redaction; preserve Hebrew/Arabic script structure."""
    if not text:
        return RedactionResult(text="", redacted=False)

    notes: list[str] = []
    detected = detect_possible_pii(text)
    result = text

    if EMAIL_RE.search(result):
        result = EMAIL_RE.sub("[REDACTED_EMAIL]", result)
        notes.append("Redacted email address(es).")
    if PHONE_RE.search(result):
        result = PHONE_RE.sub("[REDACTED_PHONE]", result)
        notes.append("Redacted phone number(s).")
    if ID_LIKE_RE.search(result):
        result = ID_LIKE_RE.sub("[REDACTED_ID]", result)
        notes.append("Redacted ID-like number(s).")
    if CASE_NUMBER_RE.search(result):
        result = CASE_NUMBER_RE.sub("[REDACTED_CASE_NO]", result)
        notes.append("Redacted case number pattern(s).")
    if ADDRESS_HINT_RE.search(result):
        result = ADDRESS_HINT_RE.sub("[REDACTED_ADDRESS]", result)
        notes.append("Redacted address-like fragment(s).")
    if redact_names:
        if HEbrew_NAME_RE.search(result):
            result = HEbrew_NAME_RE.sub("[REDACTED_NAME]", result)
            notes.append("Redacted possible Hebrew name(s).")
        if EN_NAME_RE.search(result):
            result = EN_NAME_RE.sub("[REDACTED_NAME]", result)
            notes.append("Redacted possible English name(s).")

    return RedactionResult(
        text=result,
        redacted=result != text,
        notes=notes,
        detected=detected,
    )
