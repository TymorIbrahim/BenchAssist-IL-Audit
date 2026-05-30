"""Safe experiment runner: plan, estimate cost, and optionally execute audit workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from benchassist.config import get_settings, resolve_gemini_api_key
from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.output_naming import sanitize_output_token

REAL_PROVIDERS: frozenset[str] = frozenset({"gemini", "openai"})


@dataclass
class GroundedConfig:
    enabled: bool = False
    schema_version: str = "v3"
    prompt_mode: str = "grounded"
    top_k_sources: int = 5


@dataclass
class CostEstimateConfig:
    input_cost_per_million: float = 0.10
    output_cost_per_million: float = 0.40
    v2_input_tokens_per_call: int = 1200
    v2_output_tokens_per_call: int = 500
    v3_input_tokens_per_call: int = 2200
    v3_output_tokens_per_call: int = 650
    caution: str = "Approximate token counts; actual billing may differ."


@dataclass
class PostProcessingConfig:
    audit_metrics: bool = True
    mitigation_comparison: bool = True
    counterfactual_validity: bool = True
    stereotype_audit: bool = True
    narrative_robustness: bool = True
    statistical_analysis: bool = True
    qualitative_cases: bool = True
    human_review_template: bool = True
    hallucination_audit: bool = True
    final_report: bool = True


@dataclass
class ExperimentConfig:
    experiment_name: str
    provider: str
    model_name: str
    schema_version: str = "v2"
    variant_set: str = "all"
    prompt_modes: list[str] = field(default_factory=lambda: ["baseline"])
    temperature: float = 0.0
    repetitions: int = 1
    limit: int | None = None
    input_cases: str | None = None
    grounded: GroundedConfig = field(default_factory=GroundedConfig)
    cost_estimates: CostEstimateConfig = field(default_factory=CostEstimateConfig)
    post_processing: PostProcessingConfig = field(default_factory=PostProcessingConfig)
    statistical_bootstrap_samples: int = 2000
    statistical_seed: int = 42
    qualitative_top_n: int = 10
    config_path: Path | None = None
    output_prefix: str | None = None
    knowledge_base: str | None = None

    @property
    def is_real_provider(self) -> bool:
        return self.provider.strip().lower() in REAL_PROVIDERS


@dataclass
class PlannedCommand:
    """One subprocess step in the experiment."""

    step_id: str
    command: list[str]
    expected_outputs: list[Path]
    description: str = ""


@dataclass
class CostEstimateResult:
    v2_calls: int
    v3_calls: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_total_cost_usd: float
    caution: str


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load experiment YAML into :class:`ExperimentConfig`."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid experiment config (expected mapping): {path}")

    grounded_raw = raw.get("grounded") or {}
    cost_raw = raw.get("cost_estimates") or {}
    post_raw = raw.get("post_processing") or {}
    stat_raw = raw.get("statistical_analysis") or {}
    qual_raw = raw.get("qualitative_cases") or {}

    limit = raw.get("limit")
    if limit is not None and str(limit).lower() in {"null", "none", ""}:
        limit = None
    elif limit is not None:
        limit = int(limit)

    return ExperimentConfig(
        experiment_name=str(raw["experiment_name"]),
        provider=str(raw.get("provider", "mock")).strip().lower(),
        model_name=str(raw.get("model_name", "mock-benchassist")),
        schema_version=str(raw.get("schema_version", "v2")),
        variant_set=str(raw.get("variant_set", "all")),
        prompt_modes=[str(m) for m in raw.get("prompt_modes", ["baseline"])],
        temperature=float(raw.get("temperature", 0.0)),
        repetitions=max(1, int(raw.get("repetitions", 1))),
        limit=limit,
        input_cases=str(raw["input_cases"]) if raw.get("input_cases") else None,
        grounded=GroundedConfig(
            enabled=bool(grounded_raw.get("enabled", False)),
            schema_version=str(grounded_raw.get("schema_version", "v3")),
            prompt_mode=str(grounded_raw.get("prompt_mode", "grounded")),
            top_k_sources=int(grounded_raw.get("top_k_sources", 5)),
        ),
        cost_estimates=CostEstimateConfig(
            input_cost_per_million=float(cost_raw.get("input_cost_per_million", 0.10)),
            output_cost_per_million=float(cost_raw.get("output_cost_per_million", 0.40)),
            v2_input_tokens_per_call=int(cost_raw.get("v2_input_tokens_per_call", 1200)),
            v2_output_tokens_per_call=int(cost_raw.get("v2_output_tokens_per_call", 500)),
            v3_input_tokens_per_call=int(cost_raw.get("v3_input_tokens_per_call", 2200)),
            v3_output_tokens_per_call=int(cost_raw.get("v3_output_tokens_per_call", 650)),
            caution=str(
                cost_raw.get(
                    "caution",
                    "Approximate token counts; actual billing may differ.",
                )
            ),
        ),
        post_processing=PostProcessingConfig(
            **{k: bool(post_raw.get(k, True)) for k in PostProcessingConfig.__dataclass_fields__}
        ),
        statistical_bootstrap_samples=int(stat_raw.get("bootstrap_samples", 2000)),
        statistical_seed=int(stat_raw.get("seed", 42)),
        qualitative_top_n=int(qual_raw.get("top_n", 10)),
        config_path=path.resolve(),
        output_prefix=str(raw["output_prefix"]) if raw.get("output_prefix") else None,
        knowledge_base=str(raw["knowledge_base"]) if raw.get("knowledge_base") else None,
    )


def output_prefix_for_run(
    config: ExperimentConfig,
    *,
    schema_version: str,
    prompt_mode: str,
) -> str:
    """Build sanitized output prefix: experiment_model_schema_mode."""
    if config.output_prefix:
        return sanitize_output_token(config.output_prefix)
    parts = [
        config.experiment_name,
        config.model_name,
        schema_version.strip().lower(),
        prompt_mode.strip().lower(),
    ]
    return sanitize_output_token("_".join(parts))


def output_suffix_for_tables(config: ExperimentConfig, prompt_mode: str) -> str:
    """Suffix for v2_group_summary_* and related tables (same as prefix token)."""
    return output_prefix_for_run(
        config, schema_version=config.schema_version, prompt_mode=prompt_mode
    )


def count_cases(config: ExperimentConfig) -> tuple[int, int]:
    """Return (base_case_count, counterfactual_count) respecting limit."""
    base_cases = create_base_cases()
    n_base = len(base_cases)
    variants = create_counterfactual_cases(
        base_cases,
        variant_set=config.variant_set,  # type: ignore[arg-type]
    )
    if config.limit is not None:
        variants = variants[: config.limit]
    return n_base, len(variants)


def estimate_cost(config: ExperimentConfig, *, n_counterfactual: int) -> CostEstimateResult:
    """Rough Gemini cost estimate from config token assumptions."""
    ce = config.cost_estimates
    v2_calls = n_counterfactual * config.repetitions * len(config.prompt_modes)
    v3_calls = 0
    if config.grounded.enabled:
        v3_calls = n_counterfactual * config.repetitions

    v2_in = v2_calls * ce.v2_input_tokens_per_call
    v2_out = v2_calls * ce.v2_output_tokens_per_call
    v3_in = v3_calls * ce.v3_input_tokens_per_call
    v3_out = v3_calls * ce.v3_output_tokens_per_call

    total_in = v2_in + v3_in
    total_out = v2_out + v3_out
    cost = (total_in / 1_000_000) * ce.input_cost_per_million + (
        total_out / 1_000_000
    ) * ce.output_cost_per_million

    return CostEstimateResult(
        v2_calls=v2_calls,
        v3_calls=v3_calls,
        estimated_input_tokens=total_in,
        estimated_output_tokens=total_out,
        estimated_total_cost_usd=round(cost, 4),
        caution=ce.caution,
    )


def experiment_dir(config: ExperimentConfig, results_dir: Path | None = None) -> Path:
    root = results_dir or get_settings().RESULTS_DIR
    return root / "experiments" / sanitize_output_token(config.experiment_name)


def _paths_for_v2_mode(
    config: ExperimentConfig,
    prompt_mode: str,
    settings: Any,
) -> dict[str, Path]:
    prefix = output_prefix_for_run(
        config, schema_version=config.schema_version, prompt_mode=prompt_mode
    )
    suffix = output_suffix_for_tables(config, prompt_mode)
    outputs = settings.RESULTS_DIR / "outputs"
    tables = settings.RESULTS_DIR / "tables"
    report = settings.RESULTS_DIR / "report"
    return {
        "model_csv": outputs / f"{prefix}.csv",
        "model_jsonl": outputs / f"{prefix}.jsonl",
        "pairwise": tables / f"v2_pairwise_comparison_{suffix}.csv",
        "group_summary": tables / f"v2_group_summary_{suffix}.csv",
        "flagged": tables / f"v2_flagged_cases_{suffix}.csv",
        "stereotype_per": tables / f"stereotype_audit_per_output_{suffix}.csv",
        "stereotype_group": tables / f"stereotype_audit_group_summary_{suffix}.csv",
        "stereotype_report": report / f"stereotype_audit_{suffix}.md",
        "stat_effects": tables / f"statistical_group_effects_{suffix}.csv",
        "stat_tests": tables / f"statistical_pairwise_tests_{suffix}.csv",
        "stat_report": report / f"statistical_analysis_{suffix}.md",
        "qualitative_csv": tables / f"qualitative_case_studies_{suffix}.csv",
        "qualitative_report": report / f"qualitative_case_studies_{suffix}.md",
    }


def grounded_output_prefix(config: ExperimentConfig) -> str:
    """Prefix for V3 grounded batch outputs (avoids collision with custom output_prefix)."""
    if config.output_prefix:
        return sanitize_output_token(f"{config.output_prefix}_v3")
    return output_prefix_for_run(
        config,
        schema_version=config.grounded.schema_version,
        prompt_mode=config.grounded.prompt_mode,
    )


def build_command_plan(config: ExperimentConfig) -> list[PlannedCommand]:
    """Build ordered list of commands for the full experiment."""
    settings = get_settings()
    data = settings.DATA_DIR
    results = settings.RESULTS_DIR
    python = sys.executable
    plan: list[PlannedCommand] = []

    cf_csv = data / "audit" / "counterfactual_cases.csv"
    base_csv = data / "processed" / "base_cases.csv"
    validity_csv = results / "tables" / f"counterfactual_validity_{sanitize_output_token(config.experiment_name)}.csv"
    validity_summary = (
        results / "tables" / f"counterfactual_validity_summary_{sanitize_output_token(config.experiment_name)}.csv"
    )

    plan.append(
        PlannedCommand(
            step_id="data_generation",
            command=[
                python,
                "-m",
                "benchassist.data_generation",
                "--variant-set",
                config.variant_set,
            ],
            expected_outputs=[cf_csv],
            description="Generate counterfactual cases",
        )
    )
    plan.append(
        PlannedCommand(
            step_id="ensure_base_cases",
            command=[
                python,
                "-c",
                "from benchassist.data_generation import ensure_base_case_files; "
                "ensure_base_case_files()",
            ],
            expected_outputs=[base_csv],
            description="Ensure base_cases.csv exists under data/processed",
        )
    )

    if config.post_processing.counterfactual_validity:
        plan.append(
            PlannedCommand(
                step_id="counterfactual_validity",
                command=[
                    python,
                    "-m",
                    "benchassist.counterfactual_validity",
                    "--base-cases",
                    str(base_csv),
                    "--counterfactuals",
                    str(cf_csv),
                    "--output-suffix",
                    sanitize_output_token(config.experiment_name),
                ],
                expected_outputs=[validity_csv, validity_summary],
                description="Counterfactual validity audit",
            )
        )

    mode_paths: dict[str, dict[str, Path]] = {}
    for mode in config.prompt_modes:
        paths = _paths_for_v2_mode(config, mode, settings)
        mode_paths[mode] = paths
        prefix = output_prefix_for_run(
            config, schema_version=config.schema_version, prompt_mode=mode
        )
        suffix = output_suffix_for_tables(config, mode)

        batch_cmd = [
            python,
            "-m",
            "benchassist.run_batch",
            "--provider",
            config.provider,
            "--model-name",
            config.model_name,
            "--schema-version",
            config.schema_version,
            "--prompt-mode",
            mode,
            "--output-prefix",
            prefix,
            "--repetitions",
            str(config.repetitions),
        ]
        if config.temperature is not None:
            batch_cmd.extend(["--temperature", str(config.temperature)])
        if config.limit is not None:
            batch_cmd.extend(["--limit", str(config.limit)])
        if config.input_cases:
            batch_cmd.extend(["--input-cases", config.input_cases])

        plan.append(
            PlannedCommand(
                step_id=f"run_batch_{mode}",
                command=batch_cmd,
                expected_outputs=[paths["model_csv"]],
                description=f"V2 model batch ({mode})",
            )
        )

        if config.post_processing.audit_metrics:
            metrics_cmd = [
                python,
                "-m",
                "benchassist.audit_metrics",
                "--version",
                "v2",
                "--input",
                str(paths["model_csv"]),
                "--output-suffix",
                suffix,
            ]
            metrics_cmd.extend(["--validity", str(validity_csv)])
            plan.append(
                PlannedCommand(
                    step_id=f"audit_metrics_{mode}",
                    command=metrics_cmd,
                    expected_outputs=[
                        paths["pairwise"],
                        paths["group_summary"],
                        paths["flagged"],
                    ],
                    description=f"V2 audit metrics ({mode})",
                )
            )

        if config.post_processing.stereotype_audit:
            plan.append(
                PlannedCommand(
                    step_id=f"stereotype_audit_{mode}",
                    command=[
                        python,
                        "-m",
                        "benchassist.stereotype_audit",
                        "--outputs",
                        str(paths["model_csv"]),
                        "--output-suffix",
                        suffix,
                    ],
                    expected_outputs=[
                        paths["stereotype_per"],
                        paths["stereotype_group"],
                    ],
                    description=f"Stereotype audit ({mode})",
                )
            )

        if config.post_processing.statistical_analysis:
            plan.append(
                PlannedCommand(
                    step_id=f"statistical_analysis_{mode}",
                    command=[
                        python,
                        "-m",
                        "benchassist.statistical_analysis",
                        "--pairwise",
                        str(paths["pairwise"]),
                        "--output-suffix",
                        suffix,
                        "--bootstrap-samples",
                        str(config.statistical_bootstrap_samples),
                        "--seed",
                        str(config.statistical_seed),
                    ],
                    expected_outputs=[paths["stat_effects"], paths["stat_report"]],
                    description=f"Statistical analysis ({mode})",
                )
            )

        if config.post_processing.qualitative_cases:
            plan.append(
                PlannedCommand(
                    step_id=f"qualitative_cases_{mode}",
                    command=[
                        python,
                        "-m",
                        "benchassist.qualitative_cases",
                        "--outputs",
                        str(paths["model_csv"]),
                        "--pairwise",
                        str(paths["pairwise"]),
                        "--flagged",
                        str(paths["flagged"]),
                        "--top-n",
                        str(config.qualitative_top_n),
                        "--output-suffix",
                        suffix,
                    ],
                    expected_outputs=[paths["qualitative_csv"]],
                    description=f"Qualitative cases ({mode})",
                )
            )

    baseline_mode = (
        "baseline"
        if "baseline" in config.prompt_modes
        else (config.prompt_modes[0] if config.prompt_modes else "baseline")
    )
    baseline_paths = mode_paths.get(
        baseline_mode,
        _paths_for_v2_mode(config, baseline_mode, settings) if config.prompt_modes else {},
    )

    if (
        config.post_processing.mitigation_comparison
        and "baseline" in mode_paths
        and "fairness_aware" in mode_paths
    ):
        mit_out = (
            results
            / "tables"
            / f"mitigation_comparison_{sanitize_output_token(config.experiment_name)}.csv"
        )
        mit_cmd = [
            python,
            "-m",
            "benchassist.mitigation_comparison",
            "--baseline",
            str(mode_paths["baseline"]["group_summary"]),
            "--fairness-aware",
            str(mode_paths["fairness_aware"]["group_summary"]),
        ]
        if "demographic_blind" in mode_paths:
            mit_cmd.extend(
                [
                    "--demographic-blind",
                    str(mode_paths["demographic_blind"]["group_summary"]),
                ]
            )
        mit_cmd.extend(["--output", str(mit_out)])
        plan.append(
            PlannedCommand(
                step_id="mitigation_comparison",
                command=mit_cmd,
                expected_outputs=[mit_out],
                description="Mitigation comparison across prompt modes",
            )
        )

    if config.post_processing.narrative_robustness:
        narr_suffix = sanitize_output_token(config.experiment_name)
        plan.append(
            PlannedCommand(
                step_id="narrative_robustness",
                command=[
                    python,
                    "-m",
                    "benchassist.narrative_robustness",
                    "--pairwise",
                    str(baseline_paths["pairwise"]),
                    "--validity",
                    str(validity_csv),
                    "--output-suffix",
                    narr_suffix,
                ],
                expected_outputs=[
                    results / "tables" / f"narrative_robustness_summary_{narr_suffix}.csv",
                    results / "report" / f"narrative_robustness_{narr_suffix}.md",
                ],
                description="Narrative-framing robustness (baseline pairwise)",
            )
        )

    if config.grounded.enabled:
        g_prefix = grounded_output_prefix(config)
        g_csv = results / "outputs" / f"{g_prefix}.csv"
        g_batch = [
            python,
            "-m",
            "benchassist.run_batch",
            "--provider",
            config.provider,
            "--model-name",
            config.model_name,
            "--schema-version",
            config.grounded.schema_version,
            "--prompt-mode",
            config.grounded.prompt_mode,
            "--top-k-sources",
            str(config.grounded.top_k_sources),
            "--output-prefix",
            g_prefix,
            "--repetitions",
            str(config.repetitions),
        ]
        if config.limit is not None:
            g_batch.extend(["--limit", str(config.limit)])
        if config.input_cases:
            g_batch.extend(["--input-cases", config.input_cases])

        plan.append(
            PlannedCommand(
                step_id="run_batch_grounded",
                command=g_batch,
                expected_outputs=[g_csv],
                description="V3 grounded model batch",
            )
        )

        if config.post_processing.hallucination_audit:
            hall_suffix = sanitize_output_token(
                f"{config.experiment_name}_grounded"
            )
            plan.append(
                PlannedCommand(
                    step_id="hallucination_audit",
                    command=[
                        python,
                        "-m",
                        "benchassist.hallucination_audit",
                        "--input",
                        str(g_csv),
                        "--output-suffix",
                        hall_suffix,
                    ],
                    expected_outputs=[
                        results / "tables" / f"hallucination_audit_per_output_{hall_suffix}.csv",
                        results / "report" / f"hallucination_audit_{hall_suffix}.md",
                    ],
                    description="Hallucination / grounding audit",
                )
            )

    if config.post_processing.human_review_template:
        hr_out = results / "tables" / f"human_review_template_{sanitize_output_token(config.experiment_name)}.csv"
        plan.append(
            PlannedCommand(
                step_id="human_review_template",
                command=[
                    python,
                    "-m",
                    "benchassist.human_review",
                    "generate-template",
                    "--qualitative-cases",
                    str(baseline_paths["qualitative_csv"]),
                    "--validity",
                    str(validity_csv),
                    "--output",
                    str(hr_out),
                ],
                expected_outputs=[hr_out, results / "report" / "human_review_rubric.md"],
                description="Human review template",
            )
        )

    if config.post_processing.final_report:
        plan.append(
            PlannedCommand(
                step_id="final_report",
                command=[python, "-m", "benchassist.final_report", "--auto"],
                expected_outputs=[results / "report" / "final_audit_report.md"],
                description="Final audit report (auto-discovery)",
            )
        )

    return plan


def format_dry_run_summary(
    config: ExperimentConfig,
    plan: list[PlannedCommand],
    cost: CostEstimateResult,
    *,
    n_base: int,
    n_cf: int,
) -> str:
    """Markdown summary for dry-run."""
    lines = [
        "# Experiment dry-run summary",
        "",
        f"**Experiment:** `{config.experiment_name}`",
        f"**Provider:** `{config.provider}`",
        f"**Model:** `{config.model_name}`",
        f"**Schema (V2):** `{config.schema_version}`",
        f"**Prompt modes:** {', '.join(config.prompt_modes)}",
        f"**Variant set:** `{config.variant_set}`",
        f"**Base cases:** {n_base}",
        f"**Counterfactual cases (after limit):** {n_cf}",
        f"**Repetitions:** {config.repetitions}",
        f"**Limit:** {config.limit if config.limit is not None else 'none'}",
        "",
        "## Model calls",
        "",
        f"- V2 calls (all modes): **{cost.v2_calls}**",
        f"- V3 grounded calls: **{cost.v3_calls}**" if config.grounded.enabled else "- V3 grounded: disabled",
        "",
        "## Cost estimate (approximate)",
        "",
        f"- Input tokens: **{cost.estimated_input_tokens:,}**",
        f"- Output tokens: **{cost.estimated_output_tokens:,}**",
        f"- Estimated total: **${cost.estimated_total_cost_usd:.4f} USD**",
        f"- *{cost.caution}*",
        "",
        "## Output files (sample)",
        "",
    ]
    settings = get_settings()
    for mode in config.prompt_modes:
        p = _paths_for_v2_mode(config, mode, settings)
        lines.append(f"### Mode `{mode}`")
        lines.append(f"- Model: `{p['model_csv'].name}`")
        lines.append(f"- Pairwise: `{p['pairwise'].name}`")
        lines.append("")

    if config.grounded.enabled:
        g_prefix = grounded_output_prefix(config)
        lines.append(f"### Grounded")
        lines.append(f"- Model: `{g_prefix}.csv`")
        lines.append("")

    lines.extend(["## Planned commands", ""])
    for i, step in enumerate(plan, 1):
        lines.append(f"{i}. **{step.step_id}** — {step.description}")
        lines.append(f"   ```bash")
        lines.append(f"   {' '.join(step.command)}")
        lines.append(f"   ```")
        lines.append("")

    lines.append(
        "\n**No commands were executed.** Use `--execute` to run (requires API key for Gemini)."
    )
    return "\n".join(lines)


def check_safety_before_execute(
    config: ExperimentConfig,
    plan: list[PlannedCommand],
    *,
    execute: bool,
    force: bool,
    resume: bool,
) -> list[str]:
    """Return list of fatal error messages (empty if OK)."""
    errors: list[str] = []

    if not execute:
        return errors

    if config.provider == "gemini":
        if not resolve_gemini_api_key():
            errors.append(
                "GEMINI_API_KEY or GOOGLE_API_KEY is required for provider=gemini. "
                "Set in .env or environment before --execute."
            )
    elif config.provider == "openai":
        if not get_settings().OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required for provider=openai.")

    if config.provider not in {"mock", "gemini", "openai"}:
        errors.append(f"Unknown provider: {config.provider!r}")

    if not resume and not force:
        existing: list[str] = []
        for step in plan:
            for path in step.expected_outputs:
                if path.exists() and path.stat().st_size > 0:
                    existing.append(str(path))
        if existing:
            errors.append(
                "Output files already exist. Use --resume to skip completed steps "
                "or --force to allow overwriting:\n  - "
                + "\n  - ".join(existing[:15])
                + (f"\n  ... and {len(existing) - 15} more" if len(existing) > 15 else "")
            )

    return errors


def run_command(
    command: list[str],
    log_file: Path,
    *,
    dry_run: bool = False,
    cwd: Path | None = None,
) -> tuple[str, int]:
    """Print, log, and optionally run a command. Returns (status, return_code)."""
    line = " ".join(command)
    print(line)
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} STARTED {line}\n")

    if dry_run:
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} DRY_RUN skipped\n")
        return "DRY_RUN", 0

    result = subprocess.run(
        command,
        cwd=str(cwd or _project_root()),
        capture_output=False,
    )
    status = "SUCCESS" if result.returncode == 0 else "FAILED"
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(
            f"{datetime.now(timezone.utc).isoformat()} {status} rc={result.returncode}\n"
        )
    return status, result.returncode


def should_skip_step(
    step: PlannedCommand,
    *,
    resume: bool,
    force: bool,
) -> bool:
    if force or not resume:
        return False
    if not step.expected_outputs:
        return False
    return all(p.exists() and p.stat().st_size > 0 for p in step.expected_outputs)


def write_experiment_artifacts(
    config: ExperimentConfig,
    plan: list[PlannedCommand],
    cost: CostEstimateResult,
    *,
    n_base: int,
    n_cf: int,
) -> Path:
    """Write plan, cost, and resolved config under results/experiments/."""
    exp_dir = experiment_dir(config)
    exp_dir.mkdir(parents=True, exist_ok=True)

    resolved = {
        "experiment_name": config.experiment_name,
        "provider": config.provider,
        "model_name": config.model_name,
        "schema_version": config.schema_version,
        "variant_set": config.variant_set,
        "prompt_modes": config.prompt_modes,
        "temperature": config.temperature,
        "repetitions": config.repetitions,
        "limit": config.limit,
        "grounded": {
            "enabled": config.grounded.enabled,
            "schema_version": config.grounded.schema_version,
            "prompt_mode": config.grounded.prompt_mode,
            "top_k_sources": config.grounded.top_k_sources,
        },
        "n_base_cases": n_base,
        "n_counterfactual_cases": n_cf,
        "config_path": str(config.config_path) if config.config_path else None,
    }
    (exp_dir / "experiment_config_resolved.json").write_text(
        json.dumps(resolved, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    yaml.safe_dump(resolved, (exp_dir / "experiment_config_resolved.yaml").open("w", encoding="utf-8"))

    plan_lines = [f"# Command plan: {config.experiment_name}", ""]
    for i, step in enumerate(plan, 1):
        plan_lines.append(f"## {i}. {step.step_id}")
        plan_lines.append(step.description)
        plan_lines.append("```bash")
        plan_lines.append(" ".join(step.command))
        plan_lines.append("```")
        plan_lines.append("Expected outputs:")
        for p in step.expected_outputs:
            plan_lines.append(f"- {p}")
        plan_lines.append("")
    (exp_dir / "command_plan.txt").write_text("\n".join(plan_lines), encoding="utf-8")

    (exp_dir / "cost_estimate.json").write_text(
        json.dumps(
            {
                "v2_calls": cost.v2_calls,
                "v3_calls": cost.v3_calls,
                "estimated_input_tokens": cost.estimated_input_tokens,
                "estimated_output_tokens": cost.estimated_output_tokens,
                "estimated_total_cost_usd": cost.estimated_total_cost_usd,
                "caution": cost.caution,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = format_dry_run_summary(config, plan, cost, n_base=n_base, n_cf=n_cf)
    (exp_dir / "dry_run_summary.md").write_text(summary, encoding="utf-8")

    (exp_dir / "execution_log.txt").write_text(
        f"# Execution log: {config.experiment_name}\n"
        f"Started: {datetime.now(timezone.utc).isoformat()}\n\n",
        encoding="utf-8",
    )
    return exp_dir


def run_experiment(
    config: ExperimentConfig,
    *,
    dry_run: bool = True,
    execute: bool = False,
    resume: bool = False,
    force: bool = False,
    continue_on_error: bool = False,
) -> int:
    """Plan and optionally execute the experiment."""
    n_base, n_cf = count_cases(config)
    cost = estimate_cost(config, n_counterfactual=n_cf)
    plan = build_command_plan(config)

    exp_dir = write_experiment_artifacts(config, plan, cost, n_base=n_base, n_cf=n_cf)
    log_file = exp_dir / "execution_log.txt"

    print(f"\n=== Experiment: {config.experiment_name} ===")
    print(f"Provider: {config.provider} | Model: {config.model_name}")
    print(f"Base cases: {n_base} | Counterfactual cases (effective): {n_cf}")
    print(f"V2 model calls: {cost.v2_calls} | V3 calls: {cost.v3_calls}")
    print(
        f"Estimated cost: ${cost.estimated_total_cost_usd:.4f} USD "
        f"({cost.estimated_input_tokens:,} in / {cost.estimated_output_tokens:,} out tokens)"
    )
    print(f"Artifacts: {exp_dir}\n")

    if dry_run and not execute:
        print(format_dry_run_summary(config, plan, cost, n_base=n_base, n_cf=n_cf))
        print("\n[DRY RUN] No commands executed.")
        return 0

    errors = check_safety_before_execute(
        config, plan, execute=execute, force=force, resume=resume
    )
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    if not execute:
        print("Specify --execute to run commands (default is dry-run).", file=sys.stderr)
        return 1

    for step in plan:
        if should_skip_step(step, resume=resume, force=force):
            msg = f"SKIPPED existing file(s) for step {step.step_id}"
            print(msg)
            with open(log_file, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now(timezone.utc).isoformat()} SKIPPED {step.step_id}\n")
            continue

        print(f"\n--- {step.step_id}: {step.description} ---")
        status, rc = run_command(step.command, log_file, dry_run=False)
        if status == "FAILED" and rc != 0:
            print(f"Step failed: {step.step_id} (exit {rc})", file=sys.stderr)
            if not continue_on_error:
                return rc

    print(f"\n✓ Experiment complete. Log: {log_file}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Safe experiment runner (default: dry-run only)."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to experiment YAML config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan and cost estimate without executing (default).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute commands (required for real API calls).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip steps whose expected output files already exist.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing output files.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue remaining steps after a failure.",
    )
    args = parser.parse_args(argv)

    config_path = args.config.resolve()
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 1

    config = load_experiment_config(config_path)

    # Default: dry-run unless --execute
    execute = bool(args.execute)
    dry_run = not execute if not args.dry_run else True
    if args.dry_run and args.execute:
        dry_run = False

    if not args.dry_run and not args.execute:
        dry_run = True
        execute = False

    return run_experiment(
        config,
        dry_run=dry_run,
        execute=execute,
        resume=args.resume,
        force=args.force,
        continue_on_error=args.continue_on_error,
    )


if __name__ == "__main__":
    raise SystemExit(main())
