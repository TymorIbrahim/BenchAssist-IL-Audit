"""Live progress monitor for Gemini audit runs."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from benchassist.detention_gemini_config import load_detention_gemini_config

def main() -> int:
    parser = argparse.ArgumentParser(description="Live monitor for Gemini audit run.")
    parser.add_argument("--config", type=Path, required=True, help="Path to run config YAML")
    parser.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds")
    args = parser.parse_args()

    config = load_detention_gemini_config(args.config)
    dry_run_path = config.dry_run_manifest_path
    output_path = config.parsed_outputs_path
    errors_path = config.parse_errors_path

    if not dry_run_path.exists():
        print(f"Error: Dry-run manifest not found at {dry_run_path}.")
        print("Please run the preflight or dry-run planner first.")
        return 1

    try:
        manifest = json.loads(dry_run_path.read_text(encoding="utf-8"))
        total_planned = manifest.get("request_plan", {}).get("total_requests", 0)
        if total_planned == 0:
            total_planned = manifest.get("total_planned_requests", 0)
    except Exception as e:
        print(f"Failed to read dry-run manifest: {e}")
        return 1

    print(f"Monitoring run configured in: {args.config}")
    print(f"Output file: {output_path}")
    print(f"Target total requests: {total_planned}\n")
    print("Waiting for run to start... (Press Ctrl+C to stop)")

    try:
        while True:
            completed = 0
            errors = 0

            if output_path.exists():
                with open(output_path, "r", encoding="utf-8") as f:
                    completed = sum(1 for _ in f)

            if errors_path.exists():
                with open(errors_path, "r", encoding="utf-8") as f:
                    errors = sum(1 for _ in f)

            pct = (completed / total_planned * 100) if total_planned > 0 else 0.0

            # Clear terminal line and update
            sys.stdout.write("\r\033[K")
            sys.stdout.write(
                f"Progress: [{completed}/{total_planned}] ({pct:.1f}%) | "
                f"Parse Errors: {errors}"
            )
            sys.stdout.flush()

            if total_planned > 0 and completed >= total_planned:
                print("\n\nRun completed! (Target reached)")
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
