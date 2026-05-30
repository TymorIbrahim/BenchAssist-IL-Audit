"""Use-case selection for BenchAssist-IL (housing vs detention/remand)."""

from __future__ import annotations

from typing import Literal

UseCase = Literal["housing", "detention"]

USE_CASE_HOUSING: UseCase = "housing"
USE_CASE_DETENTION: UseCase = "detention"

DEFAULT_USE_CASE: UseCase = USE_CASE_HOUSING

USE_CASES: tuple[UseCase, ...] = (USE_CASE_HOUSING, USE_CASE_DETENTION)

USE_CASE_LABELS: dict[str, str] = {
    USE_CASE_HOUSING: "BenchAssist-IL Housing Audit",
    USE_CASE_DETENTION: "BenchAssist-IL Detention Audit",
}

USE_CASE_ALIASES: dict[str, UseCase] = {
    "housing": USE_CASE_HOUSING,
    "landlord": USE_CASE_HOUSING,
    "tenant": USE_CASE_HOUSING,
    "detention": USE_CASE_DETENTION,
    "remand": USE_CASE_DETENTION,
    "remandassist": USE_CASE_DETENTION,
    "criminal_detention_remand": USE_CASE_DETENTION,
}


def normalize_use_case(value: str | None) -> UseCase:
    """Normalize CLI/API use-case strings; default to housing."""
    if value is None or not str(value).strip():
        return DEFAULT_USE_CASE
    key = str(value).strip().lower().replace("-", "_")
    if key in USE_CASE_ALIASES:
        return USE_CASE_ALIASES[key]
    if key in USE_CASES:
        return key  # type: ignore[return-value]
    raise ValueError(
        f"Unknown use_case {value!r}. Expected one of: {', '.join(USE_CASES)}"
    )


def add_use_case_arg(parser) -> None:
    """Add standard --use-case argument to an argparse parser."""
    parser.add_argument(
        "--use-case",
        default=None,
        choices=list(USE_CASES),
        help=(
            "Audit use case: housing (default) or detention/remand. "
            "When omitted, existing housing behavior is preserved."
        ),
    )
