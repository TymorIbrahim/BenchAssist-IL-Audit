"""Deterministic mock detention audit runner (no external API calls)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from benchassist.detention_schema import DetentionRiskMemoOutput
from benchassist.use_case import USE_CASE_DETENTION

PromptMode = Literal["baseline", "fairness_aware", "demographic_blind", "grounded"]

_MOCK_MODEL = "mock-detention-local"
_LIMITATIONS = [
    "Toy non-binding audit memo — not legal advice.",
    "Not an AI judge. Does not decide detention.",
    "Mock output for pipeline QA only — not research findings.",
    "Requires human legal review.",
]

# Variants that intentionally receive harsher mock outputs for metric QA
_HARSHER_VARIANTS: frozenset[str] = frozenset(
    {
        "arab_name_he",
        "broken_hebrew",
        "translated_arabic_style_hebrew",
        "low_income_neighborhood_proxy",
    }
)

_WEAK_EVIDENCE_CASES: frozenset[str] = frozenset({"D003", "D010", "D012"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_int(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _load_inputs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")
    if path.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def _map_legal_area(raw: str) -> str:
    mapping = {
        "arrest_extension": "arrest_extension",
        "post_indictment_remand": "post_indictment_remand",
        "pre_indictment_detention": "pre_indictment_detention",
        "detention_appeal": "detention_appeal",
    }
    return mapping.get(str(raw), "arrest_extension")


def _base_levels(case_id: str, variant_type: str) -> dict[str, Any]:
    """Deterministic baseline mock levels."""
    seed = _seed_int(case_id, variant_type)
    is_weak = case_id in _WEAK_EVIDENCE_CASES
    is_harsher = variant_type in _HARSHER_VARIANTS

    if is_weak and variant_type == "neutral_he":
        return {
            "dangerousness_level": "insufficient_information",
            "obstruction_risk_level": "low",
            "reasonable_suspicion_assessment": "weak",
            "investigative_necessity": "low",
            "recommended_action_type": "insufficient_information",
            "recommended_duration_days": None,
            "evidence_burden_level": "low",
            "suspect_credibility_framing": "neutral",
            "rights_orientation": "liberty_oriented",
            "confidence": 0.35,
        }

    danger = "medium"
    action = "short_extension"
    duration = 3 + (seed % 3)
    credibility = "neutral"
    rights = "balanced"

    if is_harsher:
        danger = "high" if seed % 2 == 0 else "medium"
        action = "longer_extension" if seed % 3 == 0 else "short_extension"
        duration = duration + 3
        credibility = "skeptical"
        rights = "public_safety_oriented"

    if variant_type == "neutral_he":
        danger = "low" if not is_weak else "insufficient_information"
        action = "release_with_conditions" if not is_weak else "insufficient_information"
        duration = 3 if not is_weak else None
        credibility = "neutral"
        rights = "balanced"

    return {
        "dangerousness_level": danger,
        "obstruction_risk_level": "medium" if case_id == "D008" else "low",
        "reasonable_suspicion_assessment": "moderate" if not is_weak else "weak",
        "investigative_necessity": "medium" if not is_weak else "low",
        "recommended_action_type": action,
        "recommended_duration_days": duration,
        "evidence_burden_level": "medium" if not is_weak else "low",
        "suspect_credibility_framing": credibility,
        "rights_orientation": rights,
        "confidence": 0.55 + (seed % 20) / 100.0,
    }


def generate_mock_memo(
    row: dict[str, Any],
    *,
    prompt_mode: PromptMode = "baseline",
) -> dict[str, Any]:
    """Generate one deterministic mock detention memo output."""
    case_id = str(row.get("case_id") or row.get("base_case_id") or "D000")
    variant_type = str(row.get("variant_type") or "neutral_he")
    variant_id = str(row.get("variant_id") or f"{case_id}-{variant_type}")
    levels = _base_levels(case_id, variant_type)

    if prompt_mode == "fairness_aware" and variant_type == "neutral_he":
        levels["rights_orientation"] = "balanced"
    if prompt_mode == "demographic_blind":
        levels["suspect_credibility_framing"] = "neutral"

    legal_area = _map_legal_area(str(row.get("legal_area") or "arrest_extension"))
    alternatives = ["ערובה", "פיקוח", "איזוק אלקטרוני"]
    safeguards = ["זכות לייצוג", "בדיקת חלופות למעצר"]
    if variant_type in _HARSHER_VARIANTS and variant_type != "neutral_he":
        alternatives = alternatives[:1]

    memo = DetentionRiskMemoOutput(
        case_summary=str(row.get("title") or f"Mock detention summary for {case_id}"),
        legal_area=legal_area,  # type: ignore[arg-type]
        dangerousness_level=levels["dangerousness_level"],  # type: ignore[arg-type]
        obstruction_risk_level=levels["obstruction_risk_level"],  # type: ignore[arg-type]
        reasonable_suspicion_assessment=levels["reasonable_suspicion_assessment"],  # type: ignore[arg-type]
        investigative_necessity=levels["investigative_necessity"],  # type: ignore[arg-type]
        recommended_action_type=levels["recommended_action_type"],  # type: ignore[arg-type]
        recommended_duration_days=levels["recommended_duration_days"],
        less_restrictive_alternatives_considered=alternatives,
        evidence_burden_level=levels["evidence_burden_level"],  # type: ignore[arg-type]
        suspect_credibility_framing=levels["suspect_credibility_framing"],  # type: ignore[arg-type]
        rights_orientation=levels["rights_orientation"],  # type: ignore[arg-type]
        procedural_safeguards_mentioned=safeguards,
        reasoning_text=(
            f"Mock reasoning for {variant_id} ({prompt_mode}). "
            "Assessment based on legally relevant facts only. "
            "This is a pipeline QA memo — not a detention decision."
        ),
        evidence_needed=["תסקיר מעצר", "ראיות לכאורה", "בדיקת חלופות"],
        risk_flags=["requires_human_review", "mock_output_not_for_submission"],
        confidence=min(1.0, levels["confidence"]),
        limitations=list(_LIMITATIONS),
    )

    output = {
        **row,
        **memo.model_dump(),
        "use_case": USE_CASE_DETENTION,
        "prompt_mode": prompt_mode,
        "model_name": _MOCK_MODEL,
        "provider": "mock",
        "timestamp": _utc_now(),
        "parse_status": "success",
        "parse_error": None,
        "raw_output": json.dumps(memo.model_dump(), ensure_ascii=False),
    }
    return output


def run_mock_batch(
    inputs: Path,
    output: Path,
    *,
    prompt_mode: PromptMode = "baseline",
) -> dict[str, Any]:
    """Run mock batch and write JSONL."""
    rows = _load_inputs(inputs)
    output.parent.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    with open(output, "w", encoding="utf-8") as fh:
        for row in rows:
            out = generate_mock_memo(row, prompt_mode=prompt_mode)
            outputs.append(out)
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    return {
        "n_inputs": len(rows),
        "n_outputs": len(outputs),
        "prompt_mode": prompt_mode,
        "output": output,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mock detention audit runner (no API calls).")
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--prompt-mode",
        default="baseline",
        choices=["baseline", "fairness_aware", "demographic_blind", "grounded"],
    )
    args = parser.parse_args(argv)

    result = run_mock_batch(args.inputs, args.output, prompt_mode=args.prompt_mode)  # type: ignore[arg-type]
    print(f"Mock detention run: {result['n_outputs']} outputs → {result['output']} ({result['prompt_mode']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
