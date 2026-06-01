"""Post-run pipeline: analysis → dashboard export → export validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchassist.detention_full_analysis import run_full_analysis
from benchassist.detention_gemini_config import load_detention_gemini_config, project_root
from benchassist.use_case import normalize_use_case


def run_detention_post_run(
    config_path: Path,
    *,
    output_dir: Path | None = None,
    demo_redact_case_text: bool = False,
    skip_export: bool = False,
) -> dict[str, object]:
    config = load_detention_gemini_config(config_path)
    run_dir = config.output_dir
    if not config.parsed_outputs_path.exists() or config.parsed_outputs_path.stat().st_size == 0:
        raise FileNotFoundError(
            f"No parsed outputs at {config.parsed_outputs_path}. "
            "Complete the Gemini run first (or use --resume)."
        )

    analysis_dir = run_dir / "analysis"
    analysis_result = run_full_analysis(
        config.parsed_outputs_path,
        output_dir=analysis_dir,
        run_manifest_path=config.run_manifest_path if config.run_manifest_path.exists() else None,
    )

    export_manifest: dict[str, object] = {}
    if not skip_export:
        from benchassist.validate_dashboard_export import validate_export
        from benchassist.vercel_export import export_vercel_data

        dashboard_out = output_dir or (project_root() / "web_dashboard" / "public" / "data")
        export_manifest = export_vercel_data(
            output_dir=dashboard_out,
            use_case=normalize_use_case(config.use_case),
            run_dir=run_dir,
            data_status=config.dashboard.data_status,
            demo_redact_case_text=demo_redact_case_text,
        )
        export_errors = validate_export(dashboard_out.resolve())
        if export_errors:
            raise RuntimeError("Dashboard export validation failed:\n" + "\n".join(export_errors))

    return {
        "run_dir": str(run_dir),
        "analysis": analysis_result,
        "export_manifest": export_manifest,
        "demo_redact": demo_redact_case_text,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detention post-run: analysis + dashboard export + validate.")
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root() / "configs" / "gemini_detention_expanded_minimal_address.yaml",
    )
    parser.add_argument("--output-dir", type=Path, default=None, help="Dashboard data dir (default: web_dashboard/public/data).")
    parser.add_argument("--demo-redact-case-text", action="store_true", help="Omit full case text in case review export.")
    parser.add_argument("--skip-export", action="store_true", help="Run analysis only.")
    args = parser.parse_args(argv)

    try:
        result = run_detention_post_run(
            args.config,
            output_dir=args.output_dir,
            demo_redact_case_text=args.demo_redact_case_text,
            skip_export=args.skip_export,
        )
    except FileNotFoundError as exc:
        print(f"Refused: {exc}")
        return 2

    analysis = result.get("analysis") or {}
    paths = analysis.get("paths") or {}
    print("Post-run complete.")
    if paths.get("report"):
        print(f"  Analysis report: {paths['report']}")
    if result.get("export_manifest"):
        em = result["export_manifest"]
        if isinstance(em, dict):
            print(f"  Dashboard export: {em.get('output_dir', 'web_dashboard/public/data')}")
            prov = em.get("export_provenance") if isinstance(em.get("export_provenance"), dict) else {}
            if prov:
                print(f"  Flagging policy: {prov.get('flagging_policy', '—')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
