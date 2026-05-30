"""Shared config loading for detention Gemini pilot/full workflows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from benchassist.dataset_modes import exclude_from_strict_bias


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 10
    retry_with_backoff: bool = True
    min_delay_seconds: float = 6.0


@dataclass
class SafetyConfig:
    dry_run_required: bool = True
    overwrite_existing: bool = False
    resume_supported: bool = True
    print_api_key: bool = False
    strict_schema_validation: bool = True
    stop_on_parse_error_rate_above: float = 0.20


@dataclass
class MethodologyConfig:
    strict_fairness_source: str = "synthetic_counterfactual_only"
    real_cases_in_strict_rates: bool = False
    real_cases_use: str = "realism_legal_reliability_grounding_qualitative_review"


@dataclass
class DashboardConfig:
    export_after_run: bool = True
    data_status: str = "gemini_pilot"
    full_text_internal_only: bool = True
    access_control_required: bool = True


@dataclass
class CostEstimateConfig:
    input_tokens_per_call: int = 1800
    output_tokens_per_call: int = 900
    input_cost_per_million: float = 0.10
    output_cost_per_million: float = 0.40
    caution: str = "Approximate token counts for planning only."


@dataclass
class DetentionGeminiConfig:
    use_case: str
    model: str
    provider: str
    prompt_modes: list[str]
    synthetic_input: Path
    real_case_input: Path
    output_dir: Path
    max_synthetic_base_cases: int | None
    max_variants_per_base_case: int | None
    max_real_cases: int | None
    temperature: float
    top_p: float
    max_output_tokens: int
    request_timeout_seconds: int
    rate_limit: RateLimitConfig
    safety: SafetyConfig
    cost_estimates: CostEstimateConfig
    metadata: dict[str, Any]
    methodology: MethodologyConfig
    dashboard: DashboardConfig
    grounded_enabled: bool = False
    config_path: Path | None = None

    @property
    def run_type(self) -> str:
        return str(self.metadata.get("run_type", "pilot"))

    @property
    def is_full_run(self) -> bool:
        return self.run_type == "full"

    @property
    def dry_run_manifest_path(self) -> Path:
        return self.output_dir / "dry_run_manifest.json"

    @property
    def selected_inputs_path(self) -> Path:
        name = "full_selected_inputs.jsonl" if self.is_full_run else "pilot_selected_inputs.jsonl"
        return self.output_dir / name

    @property
    def parsed_outputs_path(self) -> Path:
        return self.output_dir / "parsed_outputs.jsonl"

    @property
    def raw_responses_path(self) -> Path:
        return self.output_dir / "raw_responses.jsonl"

    @property
    def run_manifest_path(self) -> Path:
        return self.output_dir / "run_manifest.json"

    @property
    def parse_errors_path(self) -> Path:
        return self.output_dir / "parse_errors.jsonl"

    @property
    def request_log_path(self) -> Path:
        return self.output_dir / "request_log_safe.jsonl"


def load_detention_gemini_config(path: Path) -> DetentionGeminiConfig:
    """Load detention Gemini YAML config."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid config: {path}")

    root = project_root()
    dataset = raw.get("dataset") or {}
    rate_raw = raw.get("rate_limit") or {}
    safety_raw = raw.get("safety") or {}
    cost_raw = raw.get("cost_estimates") or {}
    grounded = raw.get("grounded") or {}
    methodology_raw = raw.get("methodology") or {}
    dashboard_raw = raw.get("dashboard") or {}

    def _resolve(p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else root / pp

    def _nullable_int(v: object) -> int | None:
        if v is None or str(v).lower() in {"null", "none", ""}:
            return None
        return int(v)

    prompt_modes = list(raw.get("prompt_modes") or ["baseline"])
    if grounded.get("enabled") and "grounded" not in prompt_modes:
        prompt_modes.append(str(grounded.get("prompt_mode", "grounded")))

    return DetentionGeminiConfig(
        use_case=str(raw.get("use_case", "detention")),
        model=str(raw.get("model", "gemini-2.5-flash-lite")),
        provider=str(raw.get("provider", "gemini")),
        prompt_modes=prompt_modes,
        synthetic_input=_resolve(str(dataset.get("synthetic_input", "data/synthetic/detention_core_cases.csv"))),
        real_case_input=_resolve(str(dataset.get("real_case_input", "data/real_cases/detention/pilot_corpus/detention_pilot_bench_inputs.csv"))),
        output_dir=_resolve(str(raw.get("output_dir", "results/gemini/detention_pilot"))),
        max_synthetic_base_cases=_nullable_int(raw.get("max_synthetic_base_cases")),
        max_variants_per_base_case=_nullable_int(raw.get("max_variants_per_base_case")),
        max_real_cases=_nullable_int(raw.get("max_real_cases")),
        temperature=float(raw.get("temperature", 0)),
        top_p=float(raw.get("top_p", 1)),
        max_output_tokens=int(raw.get("max_output_tokens", 4096)),
        request_timeout_seconds=int(raw.get("request_timeout_seconds", 120)),
        rate_limit=RateLimitConfig(
            requests_per_minute=int(rate_raw.get("requests_per_minute", 10)),
            retry_with_backoff=bool(rate_raw.get("retry_with_backoff", True)),
            min_delay_seconds=float(rate_raw.get("min_delay_seconds", 6.0)),
        ),
        safety=SafetyConfig(
            dry_run_required=bool(safety_raw.get("dry_run_required", True)),
            overwrite_existing=bool(safety_raw.get("overwrite_existing", False)),
            resume_supported=bool(safety_raw.get("resume_supported", True)),
            print_api_key=bool(safety_raw.get("print_api_key", False)),
            strict_schema_validation=bool(safety_raw.get("strict_schema_validation", True)),
            stop_on_parse_error_rate_above=float(safety_raw.get("stop_on_parse_error_rate_above", 0.20)),
        ),
        cost_estimates=CostEstimateConfig(
            input_tokens_per_call=int(cost_raw.get("input_tokens_per_call", 1800)),
            output_tokens_per_call=int(cost_raw.get("output_tokens_per_call", 900)),
            input_cost_per_million=float(cost_raw.get("input_cost_per_million", 0.10)),
            output_cost_per_million=float(cost_raw.get("output_cost_per_million", 0.40)),
            caution=str(cost_raw.get("caution", "Approximate token counts for planning only.")),
        ),
        metadata=dict(raw.get("metadata") or {}),
        methodology=MethodologyConfig(
            strict_fairness_source=str(
                methodology_raw.get("strict_fairness_source")
                or raw.get("metadata", {}).get("strict_fairness_source", "synthetic_counterfactual_only")
            ),
            real_cases_in_strict_rates=bool(
                methodology_raw.get("real_cases_in_strict_rates", raw.get("metadata", {}).get("real_cases_in_strict_rates", False))
            ),
            real_cases_use=str(
                methodology_raw.get("real_cases_use", "realism_legal_reliability_grounding_qualitative_review")
            ),
        ),
        dashboard=DashboardConfig(
            export_after_run=bool(dashboard_raw.get("export_after_run", True)),
            data_status=str(dashboard_raw.get("data_status", "gemini_pilot")),
            full_text_internal_only=bool(dashboard_raw.get("full_text_internal_only", True)),
            access_control_required=bool(dashboard_raw.get("access_control_required", True)),
        ),
        grounded_enabled=bool(grounded.get("enabled", False)),
        config_path=path,
    )


def verify_pilot_qa_passed(root: Path | None = None) -> dict[str, Any]:
    """Verify pilot QA artifacts; no API calls."""
    root = root or project_root()
    pilot_dir = root / "results" / "gemini" / "detention_pilot"
    qa_report = root / "results" / "report" / "gemini_detention_pilot_qa_report.md"
    parsed_path = pilot_dir / "parsed_outputs.jsonl"
    run_manifest_path = pilot_dir / "run_manifest.json"
    metric_path = pilot_dir / "analysis" / "detention_pilot_metric_summary.json"

    checks: list[dict[str, Any]] = []
    all_ok = True

    def add(name: str, ok: bool, detail: str) -> None:
        nonlocal all_ok
        if not ok:
            all_ok = False
        checks.append({"name": name, "ok": ok, "detail": detail})

    add("pilot_qa_report_exists", qa_report.exists(), str(qa_report))
    qa_text = qa_report.read_text(encoding="utf-8") if qa_report.exists() else ""
    add(
        "pilot_qa_planning_ready",
        bool(re.search(r"ready_for_full_run_planning.*?\byes\b", qa_text, re.I)),
        "QA report must recommend ready_for_full_run_planning: yes",
    )

    n_parsed = 0
    if parsed_path.exists():
        n_parsed = sum(1 for line in parsed_path.read_text(encoding="utf-8").splitlines() if line.strip())
    add("pilot_parsed_outputs", n_parsed >= 11, f"{n_parsed} pilot parsed rows (expected ≥11 from completed pilot)")

    if run_manifest_path.exists():
        rm = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        completed = rm.get("stats", {}).get("completed", 0)
        add("pilot_run_manifest", completed >= 11, f"pilot completed requests: {completed}")
    else:
        add("pilot_run_manifest", False, "run_manifest.json missing")

    schema_ok = False
    schema_detail = "not validated"
    if parsed_path.exists():
        from benchassist.detention_schema import validate_detention_outputs_file

        val = validate_detention_outputs_file(parsed_path)
        schema_ok = bool(val.get("passed")) and val.get("n_hard_errors", 1) == 0
        schema_detail = (
            f"passed={val.get('passed')}, hard_errors={val.get('n_hard_errors', 0)}, "
            f"warnings={val.get('n_warnings', 0)}"
        )
    add("pilot_schema_validation", schema_ok, schema_detail)

    strict_excluded = False
    if metric_path.exists():
        metrics = json.loads(metric_path.read_text(encoding="utf-8"))
        strict_excluded = metrics.get("real_cases_in_strict_rates") is False
        add(
            "pilot_strict_filtering",
            strict_excluded,
            f"real_cases_in_strict_rates={metrics.get('real_cases_in_strict_rates')}",
        )
    else:
        add("pilot_strict_filtering", False, "detention_pilot_metric_summary.json missing")

    review_packet = root / "results" / "report" / "gemini_detention_pilot_flagged_cases_review_packet.md"
    add("pilot_review_packet", review_packet.exists(), str(review_packet))

    return {
        "passed": all_ok,
        "checks": checks,
        "pilot_dir": str(pilot_dir),
        "n_parsed_rows": n_parsed,
    }


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")
    return pd.read_csv(path).to_dict(orient="records")


def _variant_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    vt = str(row.get("variant_type", ""))
    if vt == "neutral_he":
        return (0, vt)
    return (1, vt)


def select_pilot_rows(config: DetentionGeminiConfig) -> list[dict[str, Any]]:
    """Select synthetic + real-case pilot rows per config limits."""
    synthetic_df = pd.read_csv(config.synthetic_input)
    selected: list[dict[str, Any]] = []

    if config.max_synthetic_base_cases is None:
        selected.extend(synthetic_df.to_dict(orient="records"))
    else:
        bases = sorted(synthetic_df["base_case_id"].dropna().unique())[: config.max_synthetic_base_cases]
        per_base = config.max_variants_per_base_case or 999
        for base in bases:
            sub = synthetic_df[synthetic_df["base_case_id"] == base].copy()
            sub["_sort"] = sub.apply(_variant_sort_key, axis=1)
            sub = sub.sort_values("_sort").drop(columns=["_sort"])
            selected.extend(sub.head(per_base).to_dict(orient="records"))

    if config.real_case_input.exists():
        real_rows = _load_csv_rows(config.real_case_input)
        if config.max_real_cases is None:
            selected.extend(real_rows)
        else:
            selected.extend(real_rows[: config.max_real_cases])

    for row in selected:
        row.setdefault("use_case", config.use_case)
        if exclude_from_strict_bias(row):
            row["use_for_strict_bias_rates"] = False
            row["exclude_from_strict_bias_rates"] = True
        else:
            row.setdefault("use_for_strict_bias_rates", True)
            row.setdefault("exclude_from_strict_bias_rates", False)

    return selected


def estimate_prompt_chars(row: dict[str, Any]) -> int:
    text = str(row.get("prompt_input") or row.get("input_text") or "")
    return len(text) + 2500  # system prompt + schema overhead


def request_key(row: dict[str, Any], prompt_mode: str) -> str:
    return f"{row.get('case_id')}::{row.get('variant_id')}::{prompt_mode}"


def load_completed_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        k = rec.get("request_key") or request_key(rec, str(rec.get("prompt_mode", "baseline")))
        if rec.get("parse_status") == "success" or rec.get("parsed_ok"):
            keys.add(str(k))
    return keys


def write_jsonl(path: Path, records: list[dict[str, Any]], *, append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
