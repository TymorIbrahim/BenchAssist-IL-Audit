#!/usr/bin/env python3
"""Plan and optionally launch detention mitigation prompt-mode batches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchassist.detention_gemini_config import DetentionGeminiConfig, project_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show mitigation prompt-mode batch plan for detention Gemini runs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root() / "configs" / "detention_gemini_full.yaml",
        help="Detention Gemini config YAML",
    )
    parser.add_argument("--execute", action="store_true", help="Run the audit after printing the plan")
    parser.add_argument("--resume", action="store_true", help="Resume an in-progress run")
    args = parser.parse_args(argv)

    if not args.config.exists():
        print(f"Config not found: {args.config}", file=sys.stderr)
        return 1

    config = DetentionGeminiConfig.from_yaml(args.config)
    modes = list(config.prompt_modes)
    print("Detention mitigation / cross-prompt batch plan")
    print(f"  Config: {args.config}")
    print(f"  Prompt modes: {', '.join(modes)}")
    print(f"  Model: {config.model}")
    print(
        "\nCross-prompt comparison in the dashboard requires outputs for baseline, "
        "fairness_aware, and demographic_blind. Re-run with all modes in prompt_modes."
    )
    if len(modes) < 2:
        print("\nWARNING: fewer than 2 prompt modes configured — cross-prompt panel will be empty.", file=sys.stderr)

    if args.execute:
        from benchassist.detention_gemini_runner import run_detention_gemini_audit

        manifest = run_detention_gemini_audit(config, resume=args.resume)
        print(json.dumps(manifest.get("stats", {}), indent=2))
    else:
        print("\nDry plan only. Pass --execute to run Gemini (requires API key).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
