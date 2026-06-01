"""Safe Gemini full runner for detention/remand audit — requires dry-run manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchassist.detention_gemini_config import load_detention_gemini_config
from benchassist.detention_gemini_runner import run_detention_gemini_audit


def run_full(config, *, resume: bool = False):
    if not config.is_full_run:
        raise RuntimeError(
            f"Refusing: config run_type is '{config.run_type}', expected full, expanded_full, or expanded_minimal_address."
        )
    return run_detention_gemini_audit(config, resume=resume)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detention Gemini FULL runner (requires dry-run manifest).")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="Resume from partial parsed_outputs.jsonl")
    args = parser.parse_args(argv)

    config = load_detention_gemini_config(args.config)
    try:
        manifest = run_full(config, resume=args.resume)
    except FileNotFoundError as exc:
        print(f"Refused: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"Refused: {exc}")
        return 2

    stats = manifest["stats"]
    print("Full Gemini detention run complete.")
    print(f"  Completed requests: {stats['completed']}")
    print(f"  Skipped (resume): {stats['skipped_resume']}")
    print(f"  Parse success rate: {stats.get('parse_success_rate', 0):.1%}")
    print(f"  Outputs: {config.parsed_outputs_path}")
    if stats.get("stopped_early"):
        print(f"  STOPPED EARLY: {stats.get('stop_reason')}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
