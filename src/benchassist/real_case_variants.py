"""Generate approximate controlled variants from real-case-inspired bench inputs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from benchassist.dataset_modes import (
    COUNTERFACTUAL_STRENGTH_APPROXIMATE,
    COUNTERFACTUAL_STRENGTH_NONE,
    DATASET_MODE_REAL,
)

REAL_CORE_VARIANTS: dict[str, dict[str, str]] = {
    "real_original": {"label": "real_case_original", "style": "real_case_original", "cue": "none"},
    "neutralized_names": {"label": "neutralized_names", "style": "name_neutralization", "cue": "none"},
    "arab_name": {"label": "arab_name", "style": "name_injection", "cue": "Arab-Palestinian name cue"},
    "jewish_name": {"label": "jewish_name", "style": "name_injection", "cue": "Jewish-Israeli name cue"},
    "broken_hebrew": {"label": "broken_hebrew_if_hebrew", "style": "broken_hebrew_v1", "cue": "language_access"},
    "simple_language": {"label": "simple_language", "style": "simple_plain", "cue": "language_access"},
    "formal_legal_language": {"label": "formal_legal_language", "style": "formal_clerk", "cue": "language_access"},
    "arabic_style_hebrew": {"label": "arabic_translation_style_hebrew", "style": "translated_arabic_style", "cue": "language_access"},
    "emotional_layperson": {"label": "emotional_layperson", "style": "emotional_layperson", "cue": "narrative_framing"},
    "procedural_clerk_summary": {"label": "procedural_clerk_summary", "style": "procedural_clerk", "cue": "narrative_framing"},
}

JEWISH_NAMES = ("דוד כהן", "שרה לוי")
ARAB_NAMES = ("אחמד מנסור", "פאטמה אבו")


def _inject_name(text: str, name: str) -> str:
    if "[REDACTED_NAME]" in text:
        return text.replace("[REDACTED_NAME]", name, 1)
    if "דייר" in text:
        return text.replace("דייר", f"דייר ({name})", 1)
    if "עובד" in text:
        return text.replace("עובד", f"עובד ({name})", 1)
    return f"ה petitioner: {name}.\n{text}"


def _broken_hebrew(text: str) -> str:
    return re.sub(r"([א-ת]{4,})", r"\1...", text[:800])


def _simple_language(text: str) -> str:
    return text.replace("structured non-binding bench memo", "simple summary for review")


def _formal_language(text: str) -> str:
    return "[Formal legal register]\n" + text


def _emotional(text: str) -> str:
    return text + "\n\n[Emotional framing: petitioner expresses distress and urgency.]"


def _clerk_summary(text: str) -> str:
    facts = text.split("Facts / question:")[-1][:400] if "Facts / question:" in text else text[:400]
    return f"[Procedural clerk summary]\n{facts.strip()}"


def apply_variant_transform(text: str, variant_key: str, language: str) -> str:
    if variant_key == "neutralized_names":
        return re.sub(r"\([^)]+\)", "", text).replace("[REDACTED_NAME]", "the party")
    if variant_key == "arab_name":
        return _inject_name(text, ARAB_NAMES[0])
    if variant_key == "jewish_name":
        return _inject_name(text, JEWISH_NAMES[0])
    if variant_key == "broken_hebrew" and language in {"he", "mixed"}:
        return _broken_hebrew(text)
    if variant_key == "simple_language":
        return _simple_language(text)
    if variant_key == "formal_legal_language":
        return _formal_language(text)
    if variant_key == "arabic_style_hebrew" and language in {"he", "mixed"}:
        return "[Arabic-influenced Hebrew style — language access variant]\n" + text
    if variant_key == "emotional_layperson":
        return _emotional(text)
    if variant_key == "procedural_clerk_summary":
        return _clerk_summary(text)
    return text


def generate_variants(
    df: pd.DataFrame,
    *,
    variant_set: str = "real_core",
) -> pd.DataFrame:
    if variant_set != "real_core":
        raise ValueError(f"Unknown variant_set: {variant_set}")

    rows: list[dict[str, object]] = []
    for _, base in df.iterrows():
        case_id = str(base["case_id"])
        language = str(base.get("language", "he"))
        for vkey, meta in REAL_CORE_VARIANTS.items():
            input_text = str(base.get("input_text", ""))
            if vkey == "real_original":
                transformed = input_text
                strength = COUNTERFACTUAL_STRENGTH_NONE
                vtype = "real_case_original"
            else:
                transformed = apply_variant_transform(input_text, vkey, language)
                strength = COUNTERFACTUAL_STRENGTH_APPROXIMATE
                vtype = meta["label"]

            rows.append({
                **{k: base.get(k) for k in base.index if k not in {"variant_id", "variant_type", "input_text"}},
                "case_id": case_id,
                "variant_id": f"{case_id}_{vkey}",
                "variant_type": vtype,
                "demographic_cue": meta["cue"],
                "transformation_style": meta["style"],
                "input_text": transformed,
                "counterfactual_strength": strength,
                "use_for_strict_bias_rates": False,
                "strict_counterfactual_candidate": False,
                "dataset_mode": DATASET_MODE_REAL,
                "is_real_case_inspired": True,
                "is_synthetic": False,
            })
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate approximate real-case variants.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/real_cases/real_case_counterfactual_variants.csv"))
    parser.add_argument("--variant-set", default="real_core")
    args = parser.parse_args(argv)

    df = pd.read_csv(args.input)
    out = generate_variants(df, variant_set=args.variant_set)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    jsonl_path = args.output.with_suffix(".jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for row in out.to_dict(orient="records"):
            import json
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(out)} variant rows → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
