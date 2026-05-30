"""Validate detention dashboard JSON exports before deploy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pair_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("case_id") or ""), str(row.get("variant_id") or "")


def validate_export(data_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        return ["manifest.json missing"]

    manifest = _load_json(manifest_path)
    if manifest.get("use_case") != "detention":
        return []

    pairwise_path = data_dir / "detention_pairwise_comparison.json"
    flagged_path = data_dir / "detention_flagged_cases.json"
    overview_path = data_dir / "detention_overview_metrics.json"
    index_path = data_dir / "detention_case_review_index.json"

    if pairwise_path.exists():
        pairwise = _load_json(pairwise_path)
        keys = [_pair_key(r) for r in pairwise if r.get("case_id")]
        unique = len(set(keys))
        if len(keys) != unique:
            errors.append(f"detention_pairwise_comparison.json: {len(keys)} rows but {unique} unique pairs (possible triple-count)")

    if overview_path.exists():
        overview_list = _load_json(overview_path)
        overview = overview_list[0] if isinstance(overview_list, list) and overview_list else {}
        n_pair = int(overview.get("n_pairwise_comparisons") or 0)
        n_flag = int(overview.get("n_flagged_comparisons") or 0)
        if pairwise_path.exists():
            pairwise = _load_json(pairwise_path)
            unique = len(set(_pair_key(r) for r in pairwise if r.get("case_id")))
            if n_pair and n_pair != unique:
                errors.append(f"overview n_pairwise_comparisons={n_pair} != unique pairs={unique}")
        if flagged_path.exists():
            flagged = _load_json(flagged_path)
            if n_flag and n_flag != len(flagged):
                errors.append(f"overview n_flagged_comparisons={n_flag} != flagged rows={len(flagged)}")

    if index_path.exists():
        index = _load_json(index_path)
        record_count = int(index.get("record_count") or 0)
        index_rows = index.get("records_index") or []
        if record_count != len(index_rows):
            errors.append(f"case review index record_count={record_count} != index rows={len(index_rows)}")
        ids = [str(r.get("review_record_id")) for r in index_rows]
        if len(ids) != len(set(ids)):
            errors.append("case review index contains duplicate review_record_id values")
        if index.get("records_split"):
            split_dir = data_dir / str(index.get("records_dir") or "detention_case_review_records")
            if not split_dir.is_dir():
                errors.append(f"records_split=true but directory missing: {split_dir.name}/")
            else:
                on_disk = len(list(split_dir.glob("*.json")))
                if on_disk != record_count:
                    errors.append(f"split record files={on_disk} != record_count={record_count}")

    row_counts = manifest.get("row_counts") or {}
    for name, key in (
        ("detention_case_review_records.json", "detention_case_review_records.json"),
        ("detention_case_review_index.json", "detention_case_review_index.json"),
    ):
        if key in row_counts and index_path.exists() and name.endswith("index.json"):
            index = _load_json(index_path)
            expected = int(index.get("record_count") or 0)
            if row_counts[key] != expected:
                errors.append(f"manifest row_counts[{key}]={row_counts[key]} != {expected}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate dashboard export data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("web_dashboard/public/data"),
        help="Dashboard public data directory",
    )
    args = parser.parse_args(argv)
    errors = validate_export(args.data_dir.resolve())
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print(f"Export validation passed ({args.data_dir})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
