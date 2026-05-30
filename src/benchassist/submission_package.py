"""Build a reproducible submission package (docs, reports, tables, charts)."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from benchassist.config import get_settings

# Project root: src/benchassist -> project
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

ROOT_DOC_FILES: tuple[str, ...] = (
    "README.md",
    "PROJECT_OVERVIEW.md",
    "CITATIONS.md",
    "SUBMISSION_CHECKLIST.md",
    "SUBMISSION_PACKAGE.md",
    "DATA_DICTIONARY.md",
    "LEGAL_EXPERT_RUNBOOK.md",
    "TESTING_REPORT.md",
)

REPORT_GLOBS: tuple[str, ...] = (
    "final_audit_report.md",
    "qualitative_case_studies*.md",
    "human_review_rubric.md",
    "counterfactual_validity*.md",
    "stereotype_audit*.md",
    "hallucination_audit*.md",
    "statistical_analysis*.md",
    "narrative_robustness*.md",
)

TABLE_GLOBS: tuple[str, ...] = (
    "v2_group_summary*.csv",
    "v2_flagged_cases*.csv",
    "v2_pairwise_comparison*.csv",
    "counterfactual_validity*.csv",
    "stereotype_audit_group_summary*.csv",
    "hallucination_audit_group_summary*.csv",
    "statistical_group_effects*.csv",
    "qualitative_case_studies*.csv",
    "human_review_template*.csv",
    "mitigation_comparison*.csv",
)

EXCLUDE_NAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".env.local",
        ".git",
        ".gitignore",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
    }
)

EXCLUDE_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo")


def _project_version() -> str:
    try:
        from importlib.metadata import version

        return version("benchassist-il-audit")
    except Exception:
        return "0.1.0"


def _should_exclude(path: Path) -> bool:
    name = path.name
    if name in EXCLUDE_NAMES:
        return True
    if name.startswith(".") and name not in {".gitkeep"}:
        return True
    if any(name.endswith(suf) for suf in EXCLUDE_SUFFIXES):
        return True
    if "__pycache__" in path.parts:
        return True
    return False


def _glob_copy(
    source_dir: Path,
    patterns: Iterable[str],
    dest_dir: Path,
    package_root: Path,
    *,
    included: list[str],
    missing: list[str],
) -> None:
    if not source_dir.is_dir():
        for pattern in patterns:
            missing.append(f"{source_dir}/{pattern}")
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for pattern in patterns:
        matches = sorted(source_dir.glob(pattern))
        if not matches:
            missing.append(f"{source_dir}/{pattern}")
            continue
        for src in matches:
            if not src.is_file() or _should_exclude(src):
                continue
            key = f"{dest_dir.name}/{src.name}"
            if key in seen:
                continue
            seen.add(key)
            dest = dest_dir / src.name
            shutil.copy2(src, dest)
            included.append(str(dest.relative_to(package_root)))


def _copy_file_if_exists(
    src: Path,
    dest: Path,
    package_root: Path,
    *,
    included: list[str],
    missing: list[str],
) -> None:
    if not src.exists() or not src.is_file():
        missing.append(str(src))
        return
    if _should_exclude(src):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    included.append(str(dest.relative_to(package_root)))


def _copy_tree_filtered(src: Path, dest: Path, out_root: Path, *, included: list[str]) -> None:
    if not src.is_dir():
        return
    for item in sorted(src.rglob("*")):
        if not item.is_file() or _should_exclude(item):
            continue
        rel = item.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        included.append(str(target.relative_to(out_root)))


def write_readme_for_reviewers(dest: Path) -> None:
    text = """# README for reviewers

Thank you for reviewing the **BenchAssist-IL Audit** project.

## Start here

1. Open **`docs/final_audit_report.md`** (or **`reports/final_audit_report.md`** if copied there).
2. Skim **`docs/PROJECT_OVERVIEW.md`** for context.
3. Optional: run the interactive dashboard from the **repository root** (not from this folder):

   ```bash
   pip install -e '.[dev,dashboard]'
   streamlit run app.py
   ```

## Important cautions

- This is a **toy Responsible AI audit** for a **non-binding** judicial decision-support prototype.
- Outputs are **not legal advice** and the system is **not an AI judge**.
- Automated metrics are **screening tools** only — not proof of unlawful discrimination.
- Cases are **synthetic**; conclusions require **human legal review**.

## Package contents

- `docs/` — project documentation and overview
- `reports/` — Markdown audit reports
- `tables/` — CSV summaries and flagged cases
- `charts/` — figures (if generated)

API keys, `.env`, and raw development caches are **excluded** from this package by design.
"""
    dest.write_text(text, encoding="utf-8")


def build_submission_package(
    *,
    output_dir: Path | None = None,
    project_root: Path | None = None,
    create_zip: bool = True,
) -> dict[str, object]:
    """Assemble submission package directory and optional zip archive."""
    root = project_root or _PROJECT_ROOT
    settings = get_settings()
    results = settings.RESULTS_DIR

    out = output_dir or (results / "submission_package")
    if out.resolve() == root.resolve():
        raise ValueError("output_dir must not be the project root")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    docs_dir = out / "docs"
    reports_dir = out / "reports"
    tables_dir = out / "tables"
    charts_dir = out / "charts"

    included: list[str] = []
    missing: list[str] = []

    for name in ROOT_DOC_FILES:
        _copy_file_if_exists(
            root / name,
            docs_dir / name,
            out,
            included=included,
            missing=missing,
        )

    _glob_copy(
        results / "report",
        REPORT_GLOBS,
        reports_dir,
        out,
        included=included,
        missing=missing,
    )
    _glob_copy(
        results / "tables",
        TABLE_GLOBS,
        tables_dir,
        out,
        included=included,
        missing=missing,
    )

    src_charts = results / "charts"
    if src_charts.is_dir() and any(src_charts.iterdir()):
        _copy_tree_filtered(src_charts, charts_dir, out, included=included)
    else:
        missing.append(str(src_charts))

    readme_path = out / "README_FOR_REVIEWERS.md"
    write_readme_for_reviewers(readme_path)
    included.append("README_FOR_REVIEWERS.md")

    total_size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "included_files": sorted(included),
        "missing_expected_files": sorted(missing),
        "total_file_count": len(included),
        "total_size_bytes": total_size,
        "project_version": _project_version(),
        "note": "API keys, .env, virtual environments, and caches are excluded.",
        "out_of_scope": [
            "party-role / power-asymmetry audit",
            "standalone interactive HTML report",
        ],
    }
    manifest_path = out / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    zip_path: Path | None = None
    if create_zip:
        zip_path = results / "submission_package.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(out.rglob("*")):
                if file_path.is_file():
                    arcname = file_path.relative_to(out.parent)
                    zf.write(file_path, arcname)

    return {
        "output_dir": out,
        "zip_path": zip_path,
        "manifest": manifest,
        "manifest_path": manifest_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build submission package (docs, reports, tables, charts)."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: results/submission_package).",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Use default paths under RESULTS_DIR.",
    )
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Do not create submission_package.zip.",
    )
    args = parser.parse_args(argv)

    output_dir = args.output_dir
    if args.auto and output_dir is None:
        output_dir = get_settings().RESULTS_DIR / "submission_package"

    result = build_submission_package(
        output_dir=output_dir,
        create_zip=not args.no_zip,
    )
    print(f"Submission package: {result['output_dir']}")
    print(f"Manifest:           {result['manifest_path']}")
    print(f"Files included:     {result['manifest']['total_file_count']}")
    print(f"Total size:         {result['manifest']['total_size_bytes']:,} bytes")
    if result.get("zip_path"):
        print(f"Zip archive:        {result['zip_path']}")
    missing = result["manifest"]["missing_expected_files"]
    if missing:
        print(f"Missing optional ({len(missing)} patterns/files) — see MANIFEST.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
