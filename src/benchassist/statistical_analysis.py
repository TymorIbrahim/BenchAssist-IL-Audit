"""Statistical uncertainty analysis for V2 pairwise audit metrics."""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from benchassist.config import get_settings

BINARY_FLAGS: tuple[str, ...] = (
    "action_type_flip",
    "legal_framing_bias_flag",
    "urgency_weaker",
    "remedy_weaker",
    "evidence_burden_higher",
    "credibility_more_skeptical",
    "rights_orientation_weaker",
    "procedural_posture_weaker",
)

NUMERIC_DELTAS: tuple[str, ...] = (
    "urgency_delta",
    "remedy_strength_delta",
    "evidence_burden_delta",
    "credibility_skepticism_delta",
    "rights_orientation_delta",
    "procedural_posture_delta",
)

CAUTION_DEFAULT = (
    "Exploratory test; no multiple-comparison correction; "
    "small sample possible; requires qualitative legal review"
)


def _coerce_bool(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def wilson_interval(
    successes: int,
    n: int,
    z: float = 1.96,
) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% when z=1.96)."""
    if n <= 0:
        return float("nan"), float("nan")
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    margin = (
        z
        * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))
        / denom
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def _median(values: list[float]) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _std_sample(values: list[float]) -> float:
    if len(values) < 2:
        return float("nan")
    m = _mean(values)
    var = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


def bootstrap_ci(
    values: list[float],
    *,
    n_resamples: int = 2000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float, float, str]:
    """Return (mean, ci_lower, ci_upper, small_sample_warning)."""
    clean = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if not clean:
        return float("nan"), float("nan"), float("nan"), "empty sample"
    mean_val = _mean(clean)
    if len(clean) < 2:
        return mean_val, mean_val, mean_val, "n<2; CI set to point estimate"
    rng = random.Random(seed)
    n = len(clean)
    boot_means: list[float] = []
    for _ in range(n_resamples):
        sample = [clean[rng.randrange(n)] for _ in range(n)]
        boot_means.append(_mean(sample))
    boot_means.sort()
    lower_idx = int((alpha / 2) * n_resamples)
    upper_idx = int((1 - alpha / 2) * n_resamples) - 1
    lower_idx = max(0, min(lower_idx, n_resamples - 1))
    upper_idx = max(0, min(upper_idx, n_resamples - 1))
    return mean_val, boot_means[lower_idx], boot_means[upper_idx], ""


def _ci_excludes_zero(lower: float, upper: float) -> bool:
    if any(math.isnan(x) for x in (lower, upper)):
        return False
    return lower > 0 or upper < 0


def interpret_numeric_delta(metric: str, mean_val: float, ci_lower: float, ci_upper: float) -> str:
    if math.isnan(mean_val):
        return "Not available"
    directional = {
        "remedy_strength_delta": "weaker remedy",
        "urgency_delta": "lower urgency",
        "evidence_burden_delta": "higher evidentiary burden",
        "credibility_skepticism_delta": "more skeptical credibility framing",
        "rights_orientation_delta": "weaker rights orientation",
        "procedural_posture_delta": "weaker procedural posture",
    }
    label = directional.get(metric, "directional shift")
    if _ci_excludes_zero(ci_lower, ci_upper):
        return f"Statistically detectable {label} signal (audit screening; not proof of bias)"
    if abs(mean_val) < 1e-9:
        return "No clear directional signal"
    return "Uncertain / compatible with noise; requires review"


def interpret_binary_rate(rate: float, ci_lower: float, ci_upper: float) -> str:
    if math.isnan(rate):
        return "Not available"
    if not math.isnan(ci_lower) and ci_lower > 0.10:
        return "Non-trivial flagged rate requiring review (audit signal)"
    if rate > 0.10:
        return "Elevated flagged rate; interpret with qualitative review"
    return "Low flagged rate in this group"


def compute_binary_group_stats(
    df: pd.DataFrame,
    metric: str,
) -> list[dict[str, Any]]:
    if df.empty or metric not in df.columns:
        return []
    work = df[df["variant_type"].astype(str) != "neutral_he"].copy()
    if work.empty:
        return []
    rows: list[dict[str, Any]] = []
    group_cols = ["variant_type", "demographic_cue"] if "demographic_cue" in work.columns else ["variant_type"]
    for keys, group in work.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        flags = group[metric].apply(_coerce_bool)
        n = len(flags)
        count_true = int(flags.sum())
        rate = count_true / n if n else float("nan")
        ci_lo, ci_hi = wilson_interval(count_true, n)
        warning = "n<2" if n < 2 else ""
        rows.append(
            {
                "variant_type": keys[0],
                "demographic_cue": keys[1] if len(keys) > 1 else "",
                "metric": metric,
                "metric_kind": "binary",
                "n": n,
                "count_true": count_true,
                "rate": round(rate, 4) if not math.isnan(rate) else float("nan"),
                "mean": float("nan"),
                "median": float("nan"),
                "std": float("nan"),
                "ci_lower": round(ci_lo, 4) if not math.isnan(ci_lo) else float("nan"),
                "ci_upper": round(ci_hi, 4) if not math.isnan(ci_hi) else float("nan"),
                "ci_method": "wilson_95",
                "small_sample_warning": warning,
                "interpretation": interpret_binary_rate(rate, ci_lo, ci_hi),
            }
        )
    return rows


def compute_numeric_group_stats(
    df: pd.DataFrame,
    metric: str,
    *,
    bootstrap_samples: int = 2000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    if df.empty or metric not in df.columns:
        return []
    work = df[df["variant_type"].astype(str) != "neutral_he"].copy()
    if work.empty:
        return []
    rows: list[dict[str, Any]] = []
    group_cols = ["variant_type", "demographic_cue"] if "demographic_cue" in work.columns else ["variant_type"]
    for keys, group in work.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        values = pd.to_numeric(group[metric], errors="coerce").dropna().tolist()
        n = len(values)
        mean_val, ci_lo, ci_hi, warning = bootstrap_ci(
            values, n_resamples=bootstrap_samples, seed=seed
        )
        rows.append(
            {
                "variant_type": keys[0],
                "demographic_cue": keys[1] if len(keys) > 1 else "",
                "metric": metric,
                "metric_kind": "numeric",
                "n": n,
                "count_true": float("nan"),
                "rate": float("nan"),
                "mean": round(mean_val, 4) if not math.isnan(mean_val) else float("nan"),
                "median": round(_median(values), 4) if values else float("nan"),
                "std": round(_std_sample(values), 4) if n >= 2 else float("nan"),
                "ci_lower": round(ci_lo, 4) if not math.isnan(ci_lo) else float("nan"),
                "ci_upper": round(ci_hi, 4) if not math.isnan(ci_hi) else float("nan"),
                "ci_method": "bootstrap_95",
                "small_sample_warning": warning,
                "interpretation": interpret_numeric_delta(metric, mean_val, ci_lo, ci_hi),
            }
        )
    return rows


def _binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    total = 0.0
    for i in range(k + 1):
        total += math.comb(n, i) * (p**i) * ((1 - p) ** (n - i))
    return total


def sign_test_p_value(positive: int, negative: int) -> float:
    """Two-sided sign test p-value for non-zero paired deltas."""
    n = positive + negative
    if n == 0:
        return float("nan")
    k = min(positive, negative)
    # two-sided: 2 * P(X <= k)
    p_one = _binom_cdf(k, n, 0.5)
    p_val = min(1.0, 2.0 * p_one)
    return p_val


def paired_test_against_zero(
    values: list[float],
    *,
    test_name_preference: str = "auto",
) -> tuple[str, float]:
    """Test whether deltas differ from zero; returns (test_name, p_value)."""
    clean = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if len(clean) < 2:
        return "insufficient_n", float("nan")
    non_zero = [v for v in clean if abs(v) > 1e-12]
    if len(non_zero) < 2:
        return "insufficient_nonzero", float("nan")

    try:
        from scipy import stats  # type: ignore[import-untyped]

        if test_name_preference != "sign_test":
            stat, p_val = stats.wilcoxon(non_zero, alternative="two-sided")
            if not math.isnan(p_val):
                return "wilcoxon", float(p_val)
    except ImportError:
        pass
    except Exception:
        pass

    positive = sum(1 for v in non_zero if v > 0)
    negative = sum(1 for v in non_zero if v < 0)
    return "sign_test", sign_test_p_value(positive, negative)


def compute_pairwise_tests(
    df: pd.DataFrame,
    *,
    bootstrap_samples: int = 2000,
    seed: int = 42,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = df[df["variant_type"].astype(str) != "neutral_he"].copy()
    rows: list[dict[str, Any]] = []
    group_cols = ["variant_type", "demographic_cue"] if "demographic_cue" in work.columns else ["variant_type"]
    for metric in NUMERIC_DELTAS:
        if metric not in work.columns:
            continue
        for keys, group in work.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            values = pd.to_numeric(group[metric], errors="coerce").dropna().tolist()
            test_name, p_value = paired_test_against_zero(values)
            rows.append(
                {
                    "variant_type": keys[0],
                    "demographic_cue": keys[1] if len(keys) > 1 else "",
                    "metric": metric,
                    "n": len(values),
                    "mean_delta": round(_mean(values), 4) if values else float("nan"),
                    "median_delta": round(_median(values), 4) if values else float("nan"),
                    "test_name": test_name,
                    "p_value": round(p_value, 6) if not math.isnan(p_value) else float("nan"),
                    "caution": CAUTION_DEFAULT,
                }
            )
    result = pd.DataFrame(rows)
    return apply_benjamini_hochberg(result)


def apply_benjamini_hochberg(tests_df: pd.DataFrame) -> pd.DataFrame:
    """Add FDR-adjusted p-values (Benjamini-Hochberg)."""
    if tests_df.empty or "p_value" not in tests_df.columns:
        return tests_df
    out = tests_df.copy()
    valid = out["p_value"].notna()
    m = int(valid.sum())
    if m == 0:
        out["p_value_fdr_bh"] = float("nan")
        out["significant_at_0_05"] = False
        out["significant_fdr_0_10"] = False
        return out

    p_series = out.loc[valid, "p_value"]
    order = p_series.sort_values().index.tolist()
    fdr_values: dict[int, float] = {}
    prev = 1.0
    for pos in range(len(order) - 1, -1, -1):
        idx = order[pos]
        rank = pos + 1
        raw = float(p_series.loc[idx]) * m / rank
        adj = min(prev, raw)
        prev = adj
        fdr_values[idx] = adj

    out["p_value_fdr_bh"] = float("nan")
    for idx, val in fdr_values.items():
        out.at[idx, "p_value_fdr_bh"] = round(val, 6)

    out["significant_at_0_05"] = out["p_value"].apply(
        lambda p: bool(p < 0.05) if pd.notna(p) else False
    )
    out["significant_fdr_0_10"] = out["p_value_fdr_bh"].apply(
        lambda p: bool(p < 0.10) if pd.notna(p) else False
    )
    return out


def build_group_effects_table(
    pairwise_df: pd.DataFrame,
    *,
    bootstrap_samples: int = 2000,
    seed: int = 42,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for metric in BINARY_FLAGS:
        rows.extend(compute_binary_group_stats(pairwise_df, metric))
    for metric in NUMERIC_DELTAS:
        rows.extend(
            compute_numeric_group_stats(
                pairwise_df, metric, bootstrap_samples=bootstrap_samples, seed=seed
            )
        )
    return pd.DataFrame(rows)


def _top_signals(group_effects: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Top variant/metric rows for report highlights."""
    signals: dict[str, pd.DataFrame] = {}
    if group_effects.empty:
        return signals
    numeric = group_effects[group_effects["metric_kind"] == "numeric"]
    binary = group_effects[group_effects["metric_kind"] == "binary"]

    def top_numeric(metric: str, ascending: bool) -> pd.DataFrame:
        sub = numeric[numeric["metric"] == metric].copy()
        if sub.empty:
            return sub
        return sub.sort_values("mean", ascending=ascending).head(5)

    signals["legal_framing_bias_flag"] = (
        binary[binary["metric"] == "legal_framing_bias_flag"]
        .sort_values("rate", ascending=False)
        .head(5)
    )
    signals["remedy_strength_delta"] = top_numeric("remedy_strength_delta", ascending=True)
    signals["evidence_burden_delta"] = top_numeric("evidence_burden_delta", ascending=False)
    signals["credibility_skepticism_delta"] = top_numeric(
        "credibility_skepticism_delta", ascending=False
    )
    signals["rights_orientation_delta"] = top_numeric("rights_orientation_delta", ascending=True)
    return signals


def generate_statistical_report(
    pairwise_df: pd.DataFrame,
    group_effects: pd.DataFrame,
    pairwise_tests: pd.DataFrame,
    *,
    pairwise_path: Path,
    output_suffix: str,
) -> str:
    n_pairs = len(pairwise_df)
    variant_types = (
        pairwise_df["variant_type"].nunique()
        if "variant_type" in pairwise_df.columns
        else 0
    )
    lines = [
        "# Statistical Uncertainty Analysis",
        "",
        "## 1. Purpose",
        "",
        "Rates and averages alone do not show whether observed legal-framing differences "
        "could plausibly arise from noise—especially with small synthetic samples. This "
        "analysis adds **Wilson confidence intervals** for binary audit flags and "
        "**bootstrap confidence intervals** for numeric legal-framing deltas, plus "
        "exploratory paired tests against zero.",
        "",
        "These results are **audit screening signals**. They do **not** prove unlawful "
        "discrimination or model unfairness.",
        "",
        "## 2. Data",
        "",
        f"- **Pairwise comparisons:** {n_pairs}",
        f"- **Variant types (including neutral):** {variant_types}",
        f"- **Source file:** `{pairwise_path}`",
        f"- **Output suffix:** `{output_suffix}`",
        "",
        "## 3. Binary flag rates with confidence intervals",
        "",
        "Wilson 95% intervals summarize how often each flag occurs within variant groups.",
        "",
    ]
    binary = group_effects[group_effects["metric_kind"] == "binary"]
    for metric in (
        "legal_framing_bias_flag",
        "action_type_flip",
        "remedy_weaker",
        "evidence_burden_higher",
        "credibility_more_skeptical",
    ):
        sub = binary[binary["metric"] == metric].sort_values("rate", ascending=False).head(5)
        lines.append(f"### `{metric}` (top groups)")
        if sub.empty:
            lines.append("_No data._\n")
        else:
            for _, row in sub.iterrows():
                lines.append(
                    f"- **{row['variant_type']}** ({row.get('demographic_cue', '')}): "
                    f"rate={row['rate']}, CI=[{row['ci_lower']}, {row['ci_upper']}] — "
                    f"{row['interpretation']}"
                )
        lines.append("")

    lines.extend(
        [
            "## 4. Numeric delta effects",
            "",
            "Bootstrap 95% CIs summarize mean shifts relative to the neutral baseline "
            "(variant minus neutral).",
            "",
        ]
    )
    numeric = group_effects[group_effects["metric_kind"] == "numeric"]
    for metric in NUMERIC_DELTAS[:4]:
        sub = numeric[numeric["metric"] == metric].copy()
        sub["abs_mean"] = sub["mean"].abs()
        sub = sub.sort_values("abs_mean", ascending=False).head(3)
        lines.append(f"### `{metric}`")
        if sub.empty:
            lines.append("_No data._\n")
        else:
            for _, row in sub.iterrows():
                lines.append(
                    f"- **{row['variant_type']}**: mean={row['mean']}, "
                    f"CI=[{row['ci_lower']}, {row['ci_upper']}] — {row['interpretation']}"
                )
        lines.append("")

    lines.extend(["## 5. Paired tests", ""])
    if pairwise_tests.empty:
        lines.append("_No paired tests computed._\n")
    else:
        sig = pairwise_tests[pairwise_tests["significant_at_0_05"] == True]  # noqa: E712
        lines.append(
            f"- Tests run: {len(pairwise_tests)} variant/metric combinations.\n"
            f"- Significant at p<0.05 (uncorrected): {len(sig)}.\n"
            f"- FDR (Benjamini–Hochberg) adjusted p-values included as `p_value_fdr_bh`.\n"
        )
        top_p = pairwise_tests.sort_values("p_value").head(5)
        for _, row in top_p.iterrows():
            lines.append(
                f"- **{row['variant_type']}** / `{row['metric']}`: "
                f"{row['test_name']}, p={row['p_value']}, FDR={row.get('p_value_fdr_bh', 'n/a')}"
            )
        lines.append("")

    lines.extend(["## 6. Main audit signals (exploratory)", ""])
    signals = _top_signals(group_effects)
    for name, frame in signals.items():
        lines.append(f"### Top signals: `{name}`")
        if frame.empty:
            lines.append("_None._\n")
            continue
        for _, row in frame.iterrows():
            if row.get("metric_kind") == "binary":
                lines.append(
                    f"- {row['variant_type']}: rate={row.get('rate')} "
                    f"(CI {row.get('ci_lower')}–{row.get('ci_upper')})"
                )
            else:
                lines.append(
                    f"- {row['variant_type']}: mean={row.get('mean')} "
                    f"(CI {row.get('ci_lower')}–{row.get('ci_upper')})"
                )
        lines.append("")

    lines.extend(
        [
            "## 7. Multiple comparisons and exploratory analysis",
            "",
            "- The audit tests **many variant types** and **many metrics** simultaneously.",
            "- Some apparent findings may occur **by chance** without multiple-comparison correction "
            "in every summary table (FDR adjustment is provided for paired tests).",
            "- Statistical results are **screening signals** requiring qualitative legal review.",
            "- Replication across models, prompt modes, and runs is recommended.",
            "",
            "## 8. Interpretation caution",
            "",
            "- This does **not** prove unlawful discrimination.",
            "- Synthetic counterfactuals may not perfectly preserve legal equivalence.",
            "- Multiple comparisons can create false positives.",
            "- Statistical findings require **qualitative legal review**.",
            "- LLM behavior may change across API versions, temperatures, and prompts.",
            "",
        ]
    )
    return "\n".join(lines)


def _plot_effect_sizes(
    group_effects: pd.DataFrame,
    output_path: Path,
    *,
    top_n: int = 15,
) -> None:
    numeric = group_effects[group_effects["metric_kind"] == "numeric"]
    metrics = [
        "remedy_strength_delta",
        "evidence_burden_delta",
        "credibility_skepticism_delta",
        "rights_orientation_delta",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes_flat = axes.flatten()
    for ax, metric in zip(axes_flat, metrics, strict=True):
        sub = numeric[numeric["metric"] == metric].copy()
        if sub.empty:
            ax.set_title(metric)
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            continue
        sub["abs_mean"] = sub["mean"].abs()
        sub = sub.sort_values("abs_mean", ascending=False).head(top_n)
        ax.bar(range(len(sub)), sub["mean"].tolist())
        ax.set_title(metric.replace("_", " "))
        ax.set_xticks(range(len(sub)))
        ax.set_xticklabels(sub["variant_type"].tolist(), rotation=45, ha="right", fontsize=7)
        ax.axhline(0, color="black", linewidth=0.8)
    fig.suptitle("Mean numeric deltas by variant type (vs neutral)")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_confidence_intervals(
    group_effects: pd.DataFrame,
    output_path: Path,
    *,
    top_n: int = 15,
) -> None:
    binary = group_effects[
        (group_effects["metric_kind"] == "binary")
        & (group_effects["metric"] == "legal_framing_bias_flag")
    ].copy()
    if binary.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "No legal_framing_bias_flag data", ha="center")
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        return
    binary = binary.sort_values("rate", ascending=False).head(top_n)
    x = range(len(binary))
    rates = binary["rate"].tolist()
    yerr_lower = [r - lo for r, lo in zip(rates, binary["ci_lower"], strict=False)]
    yerr_upper = [hi - r for r, hi in zip(rates, binary["ci_upper"], strict=False)]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.errorbar(
        list(x),
        rates,
        yerr=[yerr_lower, yerr_upper],
        fmt="o",
        capsize=3,
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(binary["variant_type"].tolist(), rotation=45, ha="right")
    ax.set_ylabel("legal_framing_bias_flag rate")
    ax.set_title("Wilson 95% CI: legal framing bias flag rate by variant")
    ax.set_ylim(0, min(1.05, max(rates) + 0.15 if rates else 1))
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def resolve_output_paths(
    suffix: str,
    *,
    results_dir: Path | None = None,
) -> dict[str, Path]:
    root = results_dir or get_settings().RESULTS_DIR
    clean = suffix.strip().replace("/", "-")
    return {
        "group_effects": root / "tables" / f"statistical_group_effects_{clean}.csv",
        "pairwise_tests": root / "tables" / f"statistical_pairwise_tests_{clean}.csv",
        "report": root / "report" / f"statistical_analysis_{clean}.md",
        "chart_effects": root / "charts" / f"statistical_effect_sizes_{clean}.png",
        "chart_ci": root / "charts" / f"statistical_confidence_intervals_{clean}.png",
    }


def run_statistical_analysis(
    pairwise_path: Path,
    *,
    group_summary_path: Path | None = None,
    output_suffix: str = "baseline",
    bootstrap_samples: int = 2000,
    seed: int = 42,
    results_dir: Path | None = None,
) -> dict[str, Any]:
    """Run full statistical uncertainty pipeline and write artefacts."""
    _ = group_summary_path  # reserved for future cross-checks
    pairwise_df = pd.read_csv(pairwise_path)
    paths = resolve_output_paths(output_suffix, results_dir=results_dir)

    group_effects = build_group_effects_table(
        pairwise_df, bootstrap_samples=bootstrap_samples, seed=seed
    )
    pairwise_tests = compute_pairwise_tests(
        pairwise_df, bootstrap_samples=bootstrap_samples, seed=seed
    )

    paths["group_effects"].parent.mkdir(parents=True, exist_ok=True)
    paths["report"].parent.mkdir(parents=True, exist_ok=True)
    group_effects.to_csv(paths["group_effects"], index=False, encoding="utf-8-sig")
    pairwise_tests.to_csv(paths["pairwise_tests"], index=False, encoding="utf-8-sig")

    report_md = generate_statistical_report(
        pairwise_df,
        group_effects,
        pairwise_tests,
        pairwise_path=pairwise_path,
        output_suffix=output_suffix,
    )
    paths["report"].write_text(report_md, encoding="utf-8")

    _plot_effect_sizes(group_effects, paths["chart_effects"])
    _plot_confidence_intervals(group_effects, paths["chart_ci"])

    return {
        "pairwise_path": pairwise_path,
        "paths": paths,
        "group_effects": group_effects,
        "pairwise_tests": pairwise_tests,
        "report_path": paths["report"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Statistical uncertainty analysis for V2 pairwise metrics."
    )
    parser.add_argument(
        "--pairwise",
        type=Path,
        required=True,
        help="V2 pairwise comparison CSV.",
    )
    parser.add_argument(
        "--group-summary",
        type=Path,
        default=None,
        help="Optional V2 group summary CSV.",
    )
    parser.add_argument(
        "--output-suffix",
        type=str,
        default="baseline",
        help="Suffix for output filenames.",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=2000,
        help="Bootstrap resamples for numeric CIs.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    args = parser.parse_args(argv)

    result = run_statistical_analysis(
        args.pairwise,
        group_summary_path=args.group_summary,
        output_suffix=args.output_suffix,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    print(f"Pairwise input: {result['pairwise_path']}")
    for key, path in result["paths"].items():
        print(f"  → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
