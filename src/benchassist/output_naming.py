"""Output filename helpers for model batch runs."""

from __future__ import annotations

import re


def sanitize_output_token(value: str) -> str:
    """Sanitize a provider/model token for use in filenames."""
    token = value.strip().lower()
    token = token.replace("/", "-").replace("\\", "-")
    token = re.sub(r"[^\w.\-]+", "-", token)
    token = re.sub(r"-+", "-", token).strip("-")
    return token or "unknown"


def resolve_model_output_basename(
    *,
    provider: str = "mock",
    model_name: str = "mock-benchassist",
    schema_version: str = "v1",
    prompt_mode: str = "baseline",
    output_prefix: str | None = None,
) -> str:
    """Return the basename for model output files (without extension).

    Legacy ``model_outputs`` is preserved for mock v1 baseline runs only.
    """
    if output_prefix:
        return sanitize_output_token(output_prefix)

    version = schema_version.strip().lower()
    mode = prompt_mode.strip().lower()
    resolved_provider = provider.strip().lower()

    if version in {"v3", "3"}:
        model_token = sanitize_output_token(model_name)
        if resolved_provider == "mock" and model_token in {
            "mock-benchassist",
            "mock_benchassist",
            "mock",
        }:
            model_token = "mock-benchassist"
        return f"model_outputs_{model_token}_v3_{mode}"

    if (
        resolved_provider == "mock"
        and version in {"v1", "1"}
        and mode in {"baseline", "default"}
    ):
        return "model_outputs"

    model_token = sanitize_output_token(model_name)
    if resolved_provider == "mock" and model_token in {"mock-benchassist", "mock_benchassist"}:
        model_token = "mock"

    return f"model_outputs_{model_token}_{version}_{mode}"


def build_run_group_id(
    *,
    model_name: str,
    schema_version: str,
    prompt_mode: str,
    timestamp: str,
) -> str:
    """Build a batch-level identifier for a model run."""
    model_token = sanitize_output_token(model_name)
    version = schema_version.strip().lower()
    mode = prompt_mode.strip().lower()
    ts = timestamp.replace(":", "").split(".")[0].rstrip("Z")
    return f"{model_token}_{version}_{mode}_{ts}"
