"""Normalized domain taxonomy for real Israeli case-inspired audit layer."""

from __future__ import annotations

import re
from typing import Iterable

NORMALIZED_DOMAINS: tuple[str, ...] = (
    "housing",
    "labor_employment",
    "social_benefits_welfare",
    "immigration_status",
    "consumer_small_claims",
    "accessibility_disability_rights",
)

OPTIONAL_DOMAINS: tuple[str, ...] = ("family", "criminal")

DOMAIN_LABELS: dict[str, str] = {
    "housing": "Housing (landlord–tenant, repairs, eviction, rent, deposit, public housing)",
    "labor_employment": "Labor & employment (dismissal, wages, notice, workplace rights)",
    "social_benefits_welfare": "Social benefits & welfare (disability, national insurance, pensions)",
    "immigration_status": "Immigration & status (visas, residency, asylum, foreign workers)",
    "consumer_small_claims": "Consumer & small claims (transactions, contracts, service disputes)",
    "accessibility_disability_rights": "Accessibility & disability rights",
    "family": "Family (optional — not in default demo)",
    "criminal": "Criminal (optional — not in default demo)",
    "unknown": "Unknown / unclassified",
}

# Map common dataset labels → normalized domain
DATASET_DOMAIN_MAP: dict[str, str] = {
    "housing": "housing",
    "landlord_tenant": "housing",
    "landlord-tenant": "housing",
    "rent": "housing",
    "eviction": "housing",
    "labor": "labor_employment",
    "employment": "labor_employment",
    "work": "labor_employment",
    "dismissal": "labor_employment",
    "welfare": "social_benefits_welfare",
    "benefits": "social_benefits_welfare",
    "social": "social_benefits_welfare",
    "national_insurance": "social_benefits_welfare",
    "pension": "social_benefits_welfare",
    "immigration": "immigration_status",
    "visa": "immigration_status",
    "residency": "immigration_status",
    "asylum": "immigration_status",
    "foreign_worker": "immigration_status",
    "consumer": "consumer_small_claims",
    "small_claims": "consumer_small_claims",
    "contract": "consumer_small_claims",
    "accessibility": "accessibility_disability_rights",
    "disability": "accessibility_disability_rights",
    "family": "family",
    "criminal": "criminal",
}

# Keyword rules (Hebrew + English) → normalized domain
DOMAIN_KEYWORD_RULES: dict[str, tuple[str, ...]] = {
    "housing": (
        "דיור", "שכירות", "שכ\"ד", "פינוי", "בעל דירה", "דייר", "landlord", "tenant",
        "rent", "eviction", "deposit", "habitability", "repair", "housing", "שיכון",
    ),
    "labor_employment": (
        "עבודה", "פיטורים", "שכר", "משכורת", "הודעה מוקדמת", "employer", "employee",
        "dismissal", "wages", "workplace", "labor", "employment", "העסקה",
    ),
    "social_benefits_welfare": (
        "קצבה", "ביטוח לאומי", "רווחה", "נכות", "פנסיה", "benefit", "welfare",
        "disability benefit", "national insurance", "allowance", "קצבת",
    ),
    "immigration_status": (
        "ויזה", "אשרה", "תושבות", "מעמד", "פליט", "עובד זר", "visa", "residency",
        "asylum", "immigration", "foreign worker", "מעמד", "הגירה",
    ),
    "consumer_small_claims": (
        "צרכן", "חוזה", "רכישה", "תביעה קטנה", "consumer", "contract", "purchase",
        "small claim", "service dispute", "מוצר", "החזר",
    ),
    "accessibility_disability_rights": (
        "נגישות", "מוגבלות", "כיסא גלגלים", "accessibility", "disability",
        "reasonable accommodation", "התאמות", "נכות",
    ),
    "family": ("משפחה", "גירושין", "משמורת", "family", "divorce", "custody"),
    "criminal": ("פלילי", "עונש", "מעצר", "criminal", "prosecution", "sentence"),
}


def normalize_domain_label(label: str | None) -> str:
    """Map a dataset domain label to a normalized domain id."""
    if not label or not str(label).strip():
        return "unknown"
    key = str(label).strip().lower().replace(" ", "_").replace("-", "_")
    if key in NORMALIZED_DOMAINS or key in OPTIONAL_DOMAINS:
        return key
    if key in DATASET_DOMAIN_MAP:
        return DATASET_DOMAIN_MAP[key]
    for mapped, domain in DATASET_DOMAIN_MAP.items():
        if mapped in key or key in mapped:
            return domain
    return "unknown"


def infer_domain_from_text(text: str) -> str:
    """Infer normalized domain from Hebrew/English/Arabic keyword overlap."""
    if not text or not text.strip():
        return "unknown"
    lower = text.lower()
    scores: dict[str, int] = {d: 0 for d in NORMALIZED_DOMAINS + OPTIONAL_DOMAINS}
    for domain, keywords in DOMAIN_KEYWORD_RULES.items():
        for kw in keywords:
            if kw.lower() in lower or kw in text:
                scores[domain] = scores.get(domain, 0) + 1
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] == 0:
        return "unknown"
    return best[0]


def resolve_domain(original_domain: str | None, text: str) -> str:
    """Resolve domain using label first, then keyword inference."""
    from_label = normalize_domain_label(original_domain)
    if from_label != "unknown":
        return from_label
    return infer_domain_from_text(text)


def is_default_demo_domain(domain: str) -> bool:
    return domain in NORMALIZED_DOMAINS


def filter_domains(domains: Iterable[str] | None) -> list[str]:
    """Parse comma-separated domain filter list."""
    if not domains:
        return list(NORMALIZED_DOMAINS)
    if isinstance(domains, str):
        parts = [p.strip() for p in domains.split(",") if p.strip()]
    else:
        parts = [str(d).strip() for d in domains if str(d).strip()]
    return parts or list(NORMALIZED_DOMAINS)


def detect_language(text: str) -> str:
    """Rough language tag: he, ar, en, mixed."""
    if not text:
        return "unknown"
    he = len(re.findall(r"[\u0590-\u05FF]", text))
    ar = len(re.findall(r"[\u0600-\u06FF]", text))
    en = len(re.findall(r"[A-Za-z]", text))
    if he >= ar and he >= en and he > 0:
        return "he"
    if ar > he and ar > 0:
        return "ar"
    if en > 0:
        return "en"
    return "mixed"
