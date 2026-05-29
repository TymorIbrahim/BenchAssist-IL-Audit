"""Optional loading of Israeli legal text from Hugging Face.

Can export samples for inspection or build :class:`BaseCase` rows for the audit
pipeline (excerpt adaptation only — no model training).

Dataset: ``BrainboxAI/legal-training-il`` on Hugging Face.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.audit_metrics import infer_remedy_strength_score
from benchassist.schemas import BaseCase, Urgency

logger = logging.getLogger(__name__)

DATASET_ID = "BrainboxAI/legal-training-il"
DATASET_URL = "https://huggingface.co/datasets/BrainboxAI/legal-training-il"
SOURCE_NOTE = (
    "adapted excerpt from BrainboxAI/legal-training-il (Hugging Face); "
    "not a real court file; for audit research only"
)
MAX_FACTS_CHARS = 2_500
MIN_FACTS_CHARS = 150

HOUSING_KEYWORDS: tuple[str, ...] = (
    "שכירות",
    "דירה",
    "משכיר",
    "שוכר",
    "פינוי",
    "ליקוי",
    "עובש",
    "דיור",
)

# Hebrew keyword hints per legal domain (first match wins on ties via declaration order).
LEGAL_AREA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "housing": HOUSING_KEYWORDS,
    "labor": (
        "עבודה",
        "שכר",
        "פיטורים",
        "מעסיק",
        "עובד",
        "הסכם עבודה",
        "ועד עובדים",
        "שביתה",
    ),
    "family": (
        "משפחה",
        "גירושין",
        "מזונות",
        "משמורת",
        "הורות",
        "ילדים",
        "אימוץ",
    ),
    "criminal": (
        "פלילי",
        "אישום",
        "עונש",
        "מעצר",
        "חקירה",
        "תסקיר שירות",
    ),
    "tort": (
        "נזיקין",
        "תאונה",
        "פיצוי",
        "רשלנות",
        "נזק גוף",
        "ביטוח חובה",
    ),
    "administrative": (
        "עתירה",
        "בג\"ץ",
        "בג״ץ",
        "רשות",
        "ועדה",
        "החלטה מנהלית",
        "סמכות ועדה",
    ),
    "commercial": (
        "חברה",
        "חוזה",
        "מניות",
        "שותפות",
        "חדלות פירעון",
        "פירוק",
        "תביעה כספית",
    ),
    "immigration": (
        "מעמד",
        "אשרה",
        "הגירה",
        "עולה",
        "אזרחות",
        "רשות האוכלוסין",
    ),
}

KNOWN_LEGAL_AREAS: tuple[str, ...] = tuple(LEGAL_AREA_KEYWORDS.keys()) + ("general",)


def _datasets_import_error() -> ImportError:
    return ImportError(
        "The optional 'datasets' package is required to load Hugging Face data. "
        "Install it with:\n\n"
        "  pip install -e '.[datasets]'\n"
    )


def record_text(record: dict[str, Any]) -> str:
    """Concatenate string fields from a dataset row for keyword search."""
    parts: list[str] = []
    for value in record.values():
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return "\n".join(parts)


def load_legal_training_il_sample(limit: int = 100) -> list[dict[str, Any]]:
    """Load a small sample from ``BrainboxAI/legal-training-il``.

    Requires the optional ``datasets`` package and network access on first
    download. The audit pipeline does **not** call this function.

    Args:
        limit: Maximum number of rows to load from the ``train`` split.

    Returns:
        A list of row dicts (at most *limit* items).

    Raises:
        ImportError: If ``datasets`` is not installed.
        ValueError: If *limit* is not positive.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise _datasets_import_error() from exc

    logger.info("Loading up to %d rows from %s …", limit, DATASET_ID)
    dataset = load_dataset(DATASET_ID, split=f"train[:{limit}]")
    records = [dict(row) for row in dataset]
    logger.info("Loaded %d records", len(records))
    return records


def infer_legal_area(text: str) -> str:
    """Classify Hebrew legal text into a coarse domain label."""
    best_area = "general"
    best_score = 0
    for area, keywords in LEGAL_AREA_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_score = score
            best_area = area
    return best_area


def filter_records_by_legal_areas(
    records: list[dict[str, Any]],
    legal_areas: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Keep records whose text matches at least one requested legal area."""
    if not legal_areas:
        return records

    allowed = set(legal_areas)
    filtered: list[dict[str, Any]] = []
    for record in records:
        text = record_text(record)
        area = infer_legal_area(text)
        if area in allowed:
            filtered.append(record)
    return filtered


def filter_housing_like_examples(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep records whose text contains housing-related Hebrew keywords.

    Args:
        records: Rows returned by :func:`load_legal_training_il_sample`.

    Returns:
        Filtered list (may be empty).
    """
    return filter_records_by_legal_areas(records, ("housing",))


def _strip_leading_question(instruction: str) -> str:
    """Remove a leading QA prompt so the remaining text is case facts."""
    text = instruction.strip()
    if "?" in text[:400]:
        text = text.split("?", 1)[1].strip()
    for prefix in (
        "נתח את ההחלטה המשפטית הבאה:",
        "נתח את פסק הדין הבא:",
        "Analyze the following",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    return text


def _extract_facts_he(record: dict[str, Any], *, max_chars: int = MAX_FACTS_CHARS) -> str:
    """Pick Hebrew case text from the instruction-tuning row."""
    instruction = str(record.get("instruction") or "").strip()
    inp = str(record.get("input") or "").strip()
    out = str(record.get("output") or "").strip()

    candidates: list[str] = []
    if len(inp) >= MIN_FACTS_CHARS:
        candidates.append(inp)
    if instruction:
        body = _strip_leading_question(instruction)
        if len(body) >= MIN_FACTS_CHARS:
            candidates.append(body)
        elif len(instruction) >= MIN_FACTS_CHARS:
            candidates.append(instruction)
    if len(out) >= MIN_FACTS_CHARS:
        candidates.append(out)
    if inp and out:
        candidates.append(f"{inp}\n\n{out}")

    facts = max(candidates, key=len) if candidates else instruction or inp or out
    facts = re.sub(r"\n{3,}", "\n\n", facts).strip()
    return facts[:max_chars]


def _infer_urgency_label(text: str) -> Urgency:
    if any(k in text for k in ("דחוף", "פינוי", "סכנה", "עובש", "חשמל", "מיידי", "ארעי")):
        return "high"
    if any(k in text for k in ("פיקדון", "העלאת שכר", "הגבלת")):
        return "low"
    return "medium"


def _default_remedy_for_area(legal_area: str) -> str:
    remedies = {
        "housing": "סעד מבוקש בנוגע לדיור או לשכירות לפי הכתב",
        "labor": "סעד מבוקש בנוגע ליחסי עבודה לפי הכתב",
        "family": "סעד מבוקש בנוגע למשפחה או מזונות לפי הכתב",
        "criminal": "סעד מבוקש בנוגע להליך פלילי לפי הכתב",
        "tort": "סעד מבוקש בנוגע לנזיקין או פיצוי לפי הכתב",
        "administrative": "סעד מבוקש בעתירה מנהלית לפי הכתב",
        "commercial": "סעד מבוקש בנוגע לחוזה או חברה לפי הכתב",
        "immigration": "סעד מבוקש בנוגע למעמד או אשרה לפי הכתב",
    }
    return remedies.get(legal_area, "סעד מבוקש לפי העתירה או התביעה")


def _infer_requested_remedy(
    record: dict[str, Any], facts: str, *, legal_area: str
) -> str:
    instruction = str(record.get("instruction") or "").strip()
    if "סעד" in instruction:
        line = instruction.split("?")[0].strip()
        return line[:240] if line else _default_remedy_for_area(legal_area)
    return _default_remedy_for_area(legal_area)


def _infer_expected_direction(facts: str, remedy: str) -> str:
    score = infer_remedy_strength_score(remedy, facts)
    if score <= 0:
        return "deny"
    if score <= 1:
        return "partial"
    return "grant"


def _make_title(record: dict[str, Any], case_id: str, facts: str) -> str:
    instruction = str(record.get("instruction") or "").strip()
    if instruction:
        title = instruction.split("?")[0].strip()
        if len(title) > 10:
            return title[:120]
    snippet = facts.replace("\n", " ")[:80]
    return f"{case_id} — {snippet}…" if snippet else case_id


def convert_record_to_base_case(
    record: dict[str, Any],
    index: int,
    *,
    facts: str | None = None,
    legal_area: str | None = None,
) -> BaseCase:
    """Map one Hugging Face row to a :class:`BaseCase` for the audit pipeline."""
    facts_he = facts if facts is not None else _extract_facts_he(record)
    area = legal_area or infer_legal_area(facts_he)
    case_id = f"IL-HF-{index:04d}"
    remedy = _infer_requested_remedy(record, facts_he, legal_area=area)
    return BaseCase(
        case_id=case_id,
        legal_area=area,
        title=_make_title(record, case_id, facts_he),
        base_facts_he=facts_he,
        base_facts_en=None,
        requested_remedy=remedy,
        expected_urgency=_infer_urgency_label(facts_he),
        expected_direction=_infer_expected_direction(facts_he, remedy),
        source_note=SOURCE_NOTE,
    )


def _resolve_legal_area_filter(
    *,
    housing_only: bool,
    legal_areas: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    """Return area names to filter by, or None for no area filter."""
    if legal_areas is not None:
        unknown = set(legal_areas) - set(KNOWN_LEGAL_AREAS)
        if unknown:
            raise ValueError(
                f"Unknown legal area(s): {sorted(unknown)}. "
                f"Known: {', '.join(KNOWN_LEGAL_AREAS)}"
            )
        if "general" in legal_areas:
            raise ValueError(
                "'general' is inferred at runtime; pick explicit domains "
                f"such as: {', '.join(LEGAL_AREA_KEYWORDS)}"
            )
        return legal_areas
    if housing_only:
        return ("housing",)
    return None


def build_base_cases_from_legal_training_il(
    target_count: int = 100,
    fetch_limit: int = 5_000,
    *,
    housing_only: bool = True,
    legal_areas: tuple[str, ...] | None = None,
    stratify_by_area: bool = False,
    exclude_general: bool = True,
) -> list[BaseCase]:
    """Download HF samples and convert them into :class:`BaseCase` rows.

    Args:
        target_count: How many base cases to produce.
        fetch_limit: How many raw dataset rows to scan (must be >= target_count).
        housing_only: If True and *legal_areas* is unset, keep housing-keyword rows only.
        legal_areas: Optional explicit domains (e.g. ``("housing", "labor")``). Overrides
            *housing_only* when set. Use with ``housing_only=False`` and no areas to
            accept any domain with extractable facts.
        stratify_by_area: When multiple areas are requested, round-robin across areas.
        exclude_general: Skip rows classified as ``general`` when not filtering by area.

    Returns:
        List of base cases ready for counterfactual generation.

    Raises:
        ImportError: If ``datasets`` is not installed.
        ValueError: If no usable rows are found.
    """
    if target_count < 1:
        raise ValueError("target_count must be at least 1")
    if fetch_limit < target_count:
        fetch_limit = max(target_count * 5, 1_000)

    area_filter = _resolve_legal_area_filter(
        housing_only=housing_only, legal_areas=legal_areas
    )

    records = load_legal_training_il_sample(fetch_limit)
    if area_filter is not None:
        records = filter_records_by_legal_areas(records, area_filter)
        logger.info(
            "Pool after legal-area filter %s: %d rows",
            list(area_filter),
            len(records),
        )

    base_cases: list[BaseCase] = []
    seen: set[str] = set()
    per_area_counts: dict[str, int] = {a: 0 for a in (area_filter or ())}

    def _area_quota_met(area: str) -> bool:
        if not stratify_by_area or area_filter is None or len(area_filter) < 2:
            return False
        quota = (target_count + len(area_filter) - 1) // len(area_filter)
        return per_area_counts.get(area, 0) >= quota

    for record in records:
        if len(base_cases) >= target_count:
            break
        facts = _extract_facts_he(record)
        if len(facts) < MIN_FACTS_CHARS:
            continue
        area = infer_legal_area(facts)
        if exclude_general and area == "general":
            continue
        if area_filter is not None and area not in area_filter:
            continue
        if _area_quota_met(area):
            continue
        dedupe_key = facts[:400]
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        base_cases.append(
            convert_record_to_base_case(
                record, len(base_cases) + 1, facts=facts, legal_area=area
            )
        )
        per_area_counts[area] = per_area_counts.get(area, 0) + 1

    if not base_cases:
        hint = (
            "Try increasing --hf-fetch, use --hf-all-areas, or set "
            "--hf-legal-areas housing,labor,family,..."
        )
        raise ValueError(
            f"No usable records found in the Hugging Face sample. {hint}"
        )

    if area_filter:
        dist = ", ".join(
            f"{a}={sum(1 for c in base_cases if c.legal_area == a)}"
            for a in area_filter
        )
        logger.info("Legal-area distribution: %s", dist)
    logger.info("Built %d base cases from %s", len(base_cases), DATASET_ID)
    return base_cases


def parse_legal_areas_arg(value: str | None) -> tuple[str, ...] | None:
    """Parse a comma-separated CLI value into area names."""
    if value is None or not value.strip():
        return None
    return tuple(part.strip() for part in value.split(",") if part.strip())


def export_sample_to_csv(
    records: list[dict[str, Any]],
    path: Path | None = None,
) -> Path:
    """Write sample records to ``data/raw/legal_training_il_sample.csv``.

    Args:
        records: Rows to export.
        path: Optional override for the destination CSV path.

    Returns:
        Path to the written CSV file.
    """
    from benchassist.config import get_settings

    out_path = path or (get_settings().DATA_DIR / "raw" / "legal_training_il_sample.csv")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        pd.DataFrame().to_csv(out_path, index=False, encoding="utf-8-sig")
        logger.warning("No records to export; wrote empty CSV to %s", out_path)
        return out_path

    df = pd.DataFrame(records)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info("Exported %d records to %s", len(records), out_path)
    return out_path


def _print_sample_preview(records: list[dict[str, Any]], n: int = 3) -> None:
    """Print a short preview of the first rows to stdout."""
    print(f"\nPreview (first {min(n, len(records))} of {len(records)} records):\n")
    for index, record in enumerate(records[:n], start=1):
        text = record_text(record)
        snippet = text[:400].replace("\n", " ")
        if len(text) > 400:
            snippet += "…"
        print(f"--- Record {index} ---")
        print(snippet or "(empty)")
        print()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``python -m benchassist.israeli_data``."""
    parser = argparse.ArgumentParser(
        description=(
            "Optionally download a small sample from BrainboxAI/legal-training-il "
            "for inspection (not used by the audit pipeline)."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of dataset rows to load (default: 100).",
    )
    parser.add_argument(
        "--housing-only",
        action="store_true",
        help="Keep only housing-related rows (default when no other area flags).",
    )
    parser.add_argument(
        "--all-areas",
        action="store_true",
        help="Include all classifiable legal domains (not only housing).",
    )
    parser.add_argument(
        "--legal-areas",
        metavar="AREAS",
        default=None,
        help=(
            "Comma-separated domains, e.g. housing,labor,family. "
            f"Known: {', '.join(LEGAL_AREA_KEYWORDS)}"
        ),
    )
    parser.add_argument(
        "--stratify-areas",
        action="store_true",
        help="Balance base cases across requested legal areas.",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip writing data/raw/legal_training_il_sample.csv.",
    )
    parser.add_argument(
        "--build-base-cases",
        type=int,
        metavar="N",
        default=None,
        help="Also build N BaseCase rows and save to data/processed/ (pipeline input).",
    )
    parser.add_argument(
        "--fetch-limit",
        type=int,
        default=5_000,
        help="Raw HF rows to scan when building base cases (default: 5000).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    try:
        records = load_legal_training_il_sample(limit=args.limit)
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"Failed to load dataset (network or Hugging Face error): {exc}",
            file=sys.stderr,
        )
        return 1

    areas = parse_legal_areas_arg(args.legal_areas)
    housing_only = args.housing_only or (areas is None and not args.all_areas)
    if areas is not None:
        records = filter_records_by_legal_areas(records, areas)
        print(f"Rows matching {list(areas)}: {len(records)}")
    elif housing_only:
        records = filter_housing_like_examples(records)
        print(f"Housing-like rows: {len(records)}")

    if not args.no_export:
        out_path = export_sample_to_csv(records)
        print(f"Exported to: {out_path}")

    if args.build_base_cases is not None:
        from benchassist.data_generation import save_base_cases_csv, save_base_cases_jsonl
        from benchassist.config import get_settings

        base_cases = build_base_cases_from_legal_training_il(
            target_count=args.build_base_cases,
            fetch_limit=args.fetch_limit,
            housing_only=housing_only,
            legal_areas=areas,
            stratify_by_area=args.stratify_areas,
        )
        processed = get_settings().DATA_DIR / "processed"
        save_base_cases_csv(base_cases, processed / "base_cases.csv")
        save_base_cases_jsonl(base_cases, processed / "base_cases.jsonl")
        print(f"Saved {len(base_cases)} base cases to {processed}")

    _print_sample_preview(records)
    print(
        "Note: Audit cases in this project are synthetic counterfactuals. "
        "Check dataset licensing before reusing any text.\n"
        f"Dataset: {DATASET_URL}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
