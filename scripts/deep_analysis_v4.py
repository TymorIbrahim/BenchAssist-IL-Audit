"""Enhanced deep statistical analysis for v4 run.

Improvements over v1:
  1. Baseline-only tests (avoids dilution from masking)
  2. Bonferroni & Benjamini-Hochberg corrections
  3. One-sided tests (testing overcorrection direction)  
  4. Bootstrap 95% confidence intervals for effect sizes
  5. Control stability verification (M vs F controls)
  6. Ethnicity × Gender interaction analysis (Kruskal-Wallis)
  7. Case severity stratification
  8. Comprehensive summary JSON for dashboard

Outputs to web_dashboard/public/data/:
  - detention_statistical_tests.json
  - detention_full_metric_summary.json
  - detention_cross_prompt_mode_summary.json
"""
import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy import stats as scipy_stats

DATA_DIR = Path("web_dashboard/public/data")
OUTPUTS_PATH = Path("rachel_data/llm_outputs.json")
CONTROLS = {"Control_AshkM", "Control_AshkF"}


def _safe_json(obj, **kwargs):
    """Serialize to JSON, replacing NaN/Infinity with null."""
    import re
    text = json.dumps(obj, **kwargs)
    text = re.sub(r'\bNaN\b', 'null', text)
    text = re.sub(r'\b-?Infinity\b', 'null', text)
    return text


def load_data():
    data = json.loads(OUTPUTS_PATH.read_text())
    results = [r for r in data["results"]
               if r.get("llm_output") and not r["llm_output"].get("parse_error")]
    comparisons = json.loads((DATA_DIR / "detention_pairwise_comparison.json").read_text())
    return results, comparisons


def cohens_d(group1, group2):
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def interpret_d(d):
    ad = abs(d)
    if ad < 0.2: return "negligible"
    if ad < 0.5: return "small"
    if ad < 0.8: return "medium"
    return "large"


def bootstrap_ci(values, n_bootstrap=5000, ci=0.95):
    """Bootstrap confidence interval for the mean."""
    if len(values) < 3:
        return {"lower": float(np.mean(values)), "upper": float(np.mean(values))}
    rng = np.random.default_rng(42)
    means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(values, size=len(values), replace=True)
        means.append(np.mean(sample))
    alpha = (1 - ci) / 2
    return {
        "lower": round(float(np.percentile(means, alpha * 100)), 4),
        "upper": round(float(np.percentile(means, (1 - alpha) * 100)), 4),
    }


def benjamini_hochberg(p_values, alpha=0.05):
    """Apply Benjamini-Hochberg FDR correction.
    Returns list of (original_index, p_value, adjusted_p, significant)."""
    n = len(p_values)
    sorted_pairs = sorted(enumerate(p_values), key=lambda x: x[1])
    results = [None] * n
    prev_adj = 0
    for rank, (idx, p) in enumerate(sorted_pairs, 1):
        adj_p = min(p * n / rank, 1.0)
        adj_p = max(adj_p, prev_adj)  # monotonicity
        prev_adj = adj_p
        results[idx] = (idx, p, round(adj_p, 6), adj_p < alpha)
    return results


def run_statistical_tests(comparisons, mode="masked"):
    """Enhanced per-profile tests with corrections and CIs.
    
    The masked mode is the system under audit. Baseline is the reference.
    """
    # Group deltas for the specified mode
    deltas_by_variant = defaultdict(lambda: {"dl": [], "days": []})
    for c in comparisons:
        if c.get("prompt_mode") != mode:
            continue
        vtype = c["variant_type"]
        if vtype in CONTROLS:
            continue
        deltas_by_variant[vtype]["dl"].append(c.get("dangerousness_level_delta", 0))
        deltas_by_variant[vtype]["days"].append(c.get("detention_days_delta", 0))

    variants = sorted(deltas_by_variant.keys())
    tests = []
    dl_pvals, days_pvals = [], []

    for vtype in variants:
        dl_vals = deltas_by_variant[vtype]["dl"]
        days_vals = deltas_by_variant[vtype]["days"]
        zeros = [0] * len(dl_vals)
        n = len(dl_vals)

        dl_mean = float(np.mean(dl_vals))
        dl_std = float(np.std(dl_vals, ddof=1)) if n > 1 else 0
        days_mean = float(np.mean(days_vals))
        days_std = float(np.std(days_vals, ddof=1)) if n > 1 else 0

        # Two-sided Mann-Whitney U
        try:
            dl_stat, dl_p = scipy_stats.mannwhitneyu(dl_vals, zeros, alternative="two-sided")
        except ValueError:
            dl_stat, dl_p = 0, 1.0
        try:
            days_stat, days_p = scipy_stats.mannwhitneyu(days_vals, zeros, alternative="two-sided")
        except ValueError:
            days_stat, days_p = 0, 1.0

        # One-sided test (H1: variant delta < 0, i.e. protective overcorrection)
        try:
            _, dl_p_one = scipy_stats.mannwhitneyu(dl_vals, zeros, alternative="less")
        except ValueError:
            dl_p_one = 1.0
        try:
            _, days_p_one = scipy_stats.mannwhitneyu(days_vals, zeros, alternative="less")
        except ValueError:
            days_p_one = 1.0

        # Wilcoxon signed-rank (paired test)
        try:
            if any(v != 0 for v in dl_vals):
                _, dl_wilcoxon_p = scipy_stats.wilcoxon(dl_vals, alternative="two-sided")
            else:
                dl_wilcoxon_p = 1.0
        except ValueError:
            dl_wilcoxon_p = 1.0
        try:
            if any(v != 0 for v in days_vals):
                _, days_wilcoxon_p = scipy_stats.wilcoxon(days_vals, alternative="two-sided")
            else:
                days_wilcoxon_p = 1.0
        except ValueError:
            days_wilcoxon_p = 1.0

        dl_d = cohens_d(dl_vals, zeros)
        days_d = cohens_d(days_vals, zeros)

        # Bootstrap CIs
        dl_ci = bootstrap_ci(dl_vals)
        days_ci = bootstrap_ci(days_vals)

        dl_pvals.append(float(dl_p))
        days_pvals.append(float(days_p))

        tests.append({
            "variant_type": vtype,
            "n": n,
            "dangerousness": {
                "mean_delta": round(dl_mean, 3),
                "std_delta": round(dl_std, 3),
                "ci_95": dl_ci,
                "mann_whitney_u": round(float(dl_stat), 2),
                "mann_whitney_p": round(float(dl_p), 4),
                "mann_whitney_p_one_sided": round(float(dl_p_one), 4),
                "wilcoxon_p": round(float(dl_wilcoxon_p), 4),
                "cohens_d": round(float(dl_d), 3),
                "effect_size": interpret_d(dl_d),
                "significant_005": float(dl_p) < 0.05,
            },
            "detention_days": {
                "mean_delta": round(days_mean, 3),
                "std_delta": round(days_std, 3),
                "ci_95": days_ci,
                "mann_whitney_u": round(float(days_stat), 2),
                "mann_whitney_p": round(float(days_p), 4),
                "mann_whitney_p_one_sided": round(float(days_p_one), 4),
                "wilcoxon_p": round(float(days_wilcoxon_p), 4),
                "cohens_d": round(float(days_d), 3),
                "effect_size": interpret_d(days_d),
                "significant_005": float(days_p) < 0.05,
            },
        })

    # Apply corrections
    n_tests = len(variants)
    bonferroni_threshold = 0.05 / n_tests
    dl_bh = benjamini_hochberg(dl_pvals)
    days_bh = benjamini_hochberg(days_pvals)

    for i, t in enumerate(tests):
        t["dangerousness"]["bonferroni_significant"] = t["dangerousness"]["mann_whitney_p"] < bonferroni_threshold
        t["dangerousness"]["bh_adjusted_p"] = dl_bh[i][2]
        t["dangerousness"]["bh_significant"] = dl_bh[i][3]
        t["detention_days"]["bonferroni_significant"] = t["detention_days"]["mann_whitney_p"] < bonferroni_threshold
        t["detention_days"]["bh_adjusted_p"] = days_bh[i][2]
        t["detention_days"]["bh_significant"] = days_bh[i][3]

    # Global summary
    corrections = {
        "n_tests": n_tests,
        "bonferroni_threshold": round(bonferroni_threshold, 4),
        "n_significant_uncorrected_dl": sum(1 for t in tests if t["dangerousness"]["significant_005"]),
        "n_significant_bonferroni_dl": sum(1 for t in tests if t["dangerousness"]["bonferroni_significant"]),
        "n_significant_bh_dl": sum(1 for t in tests if t["dangerousness"]["bh_significant"]),
        "n_significant_uncorrected_days": sum(1 for t in tests if t["detention_days"]["significant_005"]),
        "n_significant_bonferroni_days": sum(1 for t in tests if t["detention_days"]["bonferroni_significant"]),
        "n_significant_bh_days": sum(1 for t in tests if t["detention_days"]["bh_significant"]),
        "note": "Baseline-only comparisons. Two-sided Mann-Whitney U test against H0: delta=0."
    }

    return tests, corrections


def run_control_stability(results):
    """Compare Control_AshkM vs Control_AshkF outputs."""
    ctrl_m_dl, ctrl_f_dl = [], []
    ctrl_m_days, ctrl_f_days = [], []
    for r in results:
        if r.get("prompt_mode") != "Baseline":
            continue
        cond = r.get("counterfactual_condition", "")
        out = r.get("llm_output", {})
        dl = out.get("Dangerousness_Level")
        dd = out.get("Recommended_Detention_Days")
        if cond == "Control_AshkM":
            if dl is not None: ctrl_m_dl.append(dl)
            if dd is not None: ctrl_m_days.append(dd)
        elif cond == "Control_AshkF":
            if dl is not None: ctrl_f_dl.append(dl)
            if dd is not None: ctrl_f_days.append(dd)

    result = {
        "control_male": {
            "n": len(ctrl_m_dl),
            "mean_dl": round(float(np.mean(ctrl_m_dl)), 3) if ctrl_m_dl else None,
            "std_dl": round(float(np.std(ctrl_m_dl, ddof=1)), 3) if len(ctrl_m_dl) > 1 else None,
            "mean_days": round(float(np.mean(ctrl_m_days)), 3) if ctrl_m_days else None,
        },
        "control_female": {
            "n": len(ctrl_f_dl),
            "mean_dl": round(float(np.mean(ctrl_f_dl)), 3) if ctrl_f_dl else None,
            "std_dl": round(float(np.std(ctrl_f_dl, ddof=1)), 3) if len(ctrl_f_dl) > 1 else None,
            "mean_days": round(float(np.mean(ctrl_f_days)), 3) if ctrl_f_days else None,
        },
    }

    if ctrl_m_dl and ctrl_f_dl:
        try:
            stat, p = scipy_stats.mannwhitneyu(ctrl_m_dl, ctrl_f_dl, alternative="two-sided")
            result["dl_comparison"] = {
                "mann_whitney_p": round(float(p), 4),
                "significant": float(p) < 0.05,
                "delta": round(float(np.mean(ctrl_f_dl) - np.mean(ctrl_m_dl)), 3),
            }
        except ValueError:
            result["dl_comparison"] = {"mann_whitney_p": 1.0, "significant": False, "delta": 0}

    if ctrl_m_days and ctrl_f_days:
        try:
            stat, p = scipy_stats.mannwhitneyu(ctrl_m_days, ctrl_f_days, alternative="two-sided")
            result["days_comparison"] = {
                "mann_whitney_p": round(float(p), 4),
                "significant": float(p) < 0.05,
                "delta": round(float(np.mean(ctrl_f_days) - np.mean(ctrl_m_days)), 3),
            }
        except ValueError:
            result["days_comparison"] = {"mann_whitney_p": 1.0, "significant": False, "delta": 0}

    return result


def run_ethnicity_analysis(results):
    """Group results by ethnicity (averaging across genders)."""
    ETHNICITY_MAP = {
        "Control_AshkM": "Ashkenazi", "Control_AshkF": "Ashkenazi",
        "Mizrahi_M": "Mizrahi", "Mizrahi_F": "Mizrahi",
        "Arab_M": "Arab", "Arab_F": "Arab",
        "Bedouin_M": "Bedouin", "Bedouin_F": "Bedouin",
        "Ethiopian_M": "Ethiopian", "Ethiopian_F": "Ethiopian",
        "Russian_M": "Russian", "Russian_F": "Russian",
        "Palestinian_M": "Palestinian", "Palestinian_F": "Palestinian",
        "Haredi_M": "Haredi", "Haredi_F": "Haredi",
        "Druze_M": "Druze", "Druze_F": "Druze",
        "AsylumSeeker_M": "Asylum Seeker", "AsylumSeeker_F": "Asylum Seeker",
    }

    analysis = {}
    for mode in ["Baseline", "Masked"]:
        eth_dl, eth_days = defaultdict(list), defaultdict(list)
        for r in results:
            if r.get("prompt_mode") != mode:
                continue
            p = r.get("counterfactual_condition", "?")
            eth = ETHNICITY_MAP.get(p, "Unknown")
            out = r["llm_output"]
            dl = out.get("Dangerousness_Level")
            dd = out.get("Recommended_Detention_Days")
            if dl is not None: eth_dl[eth].append(dl)
            if dd is not None: eth_days[eth].append(dd)

        ctrl_dl_mean = float(np.mean(eth_dl.get("Ashkenazi", [0])))
        ctrl_days_mean = float(np.mean(eth_days.get("Ashkenazi", [0])))

        mode_data = []
        for eth in ["Ashkenazi", "Mizrahi", "Russian", "Haredi", "Druze",
                     "Arab", "Bedouin", "Ethiopian", "Palestinian", "Asylum Seeker"]:
            if eth not in eth_dl:
                continue
            dl_vals = eth_dl[eth]
            days_vals = eth_days[eth]

            # Statistical test vs control
            ctrl_dl_vals = eth_dl.get("Ashkenazi", [])
            try:
                _, p_dl = scipy_stats.mannwhitneyu(dl_vals, ctrl_dl_vals, alternative="two-sided") if eth != "Ashkenazi" and ctrl_dl_vals else (0, 1.0)
            except ValueError:
                p_dl = 1.0

            mode_data.append({
                "ethnicity": eth,
                "n": len(dl_vals),
                "mean_dangerousness": round(float(np.mean(dl_vals)), 2),
                "delta_dangerousness": round(float(np.mean(dl_vals) - ctrl_dl_mean), 3),
                "ci_95_dl": bootstrap_ci(dl_vals),
                "mean_detention_days": round(float(np.mean(days_vals)), 2),
                "delta_detention_days": round(float(np.mean(days_vals) - ctrl_days_mean), 3),
                "ci_95_days": bootstrap_ci(days_vals),
                "p_vs_control": round(float(p_dl), 4) if eth != "Ashkenazi" else None,
            })
        analysis[mode.lower()] = mode_data

    # Kruskal-Wallis test across all ethnicities (baseline only)
    eth_groups_dl = []
    for mode_entry in analysis.get("baseline", []):
        eth = mode_entry["ethnicity"]
        if eth == "Ashkenazi":
            continue
        eth_dl_vals = [r["llm_output"]["Dangerousness_Level"]
                       for r in results
                       if r.get("prompt_mode") == "Baseline"
                       and ETHNICITY_MAP.get(r.get("counterfactual_condition", "")) == eth
                       and r["llm_output"].get("Dangerousness_Level") is not None]
        if eth_dl_vals:
            eth_groups_dl.append(eth_dl_vals)

    kruskal_result = {"applicable": False}
    if len(eth_groups_dl) >= 2:
        try:
            stat, p = scipy_stats.kruskal(*eth_groups_dl)
            kruskal_result = {
                "applicable": True,
                "test": "Kruskal-Wallis H",
                "statistic": round(float(stat), 3),
                "p_value": round(float(p), 4),
                "significant": float(p) < 0.05,
                "n_groups": len(eth_groups_dl),
                "interpretation": "Significant difference in DL across ethnicities" if p < 0.05 else "No significant difference in DL across ethnicities",
            }
        except ValueError:
            pass

    return analysis, kruskal_result


def run_gender_analysis(results):
    """Gender analysis with enhanced stats."""
    analysis = {}
    for mode in ["Baseline", "Masked"]:
        male_dl, female_dl = [], []
        male_days, female_days = [], []
        for r in results:
            if r.get("prompt_mode") != mode:
                continue
            p = r.get("counterfactual_condition", "?")
            out = r["llm_output"]
            dl = out.get("Dangerousness_Level")
            dd = out.get("Recommended_Detention_Days")
            if p.endswith("_M"):
                if dl is not None: male_dl.append(dl)
                if dd is not None: male_days.append(dd)
            elif p.endswith("_F"):
                if dl is not None: female_dl.append(dl)
                if dd is not None: female_days.append(dd)

        try:
            _, dl_p = scipy_stats.mannwhitneyu(male_dl, female_dl, alternative="two-sided")
        except ValueError:
            dl_p = 1.0
        try:
            _, days_p = scipy_stats.mannwhitneyu(male_days, female_days, alternative="two-sided")
        except ValueError:
            days_p = 1.0

        dl_d = cohens_d(female_dl, male_dl) if male_dl and female_dl else 0

        analysis[mode.lower()] = {
            "male": {
                "n": len(male_dl),
                "mean_dangerousness": round(float(np.mean(male_dl)), 3) if male_dl else 0,
                "ci_95_dl": bootstrap_ci(male_dl) if male_dl else None,
                "mean_detention_days": round(float(np.mean(male_days)), 3) if male_days else 0,
            },
            "female": {
                "n": len(female_dl),
                "mean_dangerousness": round(float(np.mean(female_dl)), 3) if female_dl else 0,
                "ci_95_dl": bootstrap_ci(female_dl) if female_dl else None,
                "mean_detention_days": round(float(np.mean(female_days)), 3) if female_days else 0,
            },
            "delta_dangerousness": round(float(np.mean(female_dl) - np.mean(male_dl)), 3) if male_dl and female_dl else 0,
            "delta_detention_days": round(float(np.mean(female_days) - np.mean(male_days)), 3) if male_days and female_days else 0,
            "dangerousness_p_value": round(float(dl_p), 4),
            "detention_days_p_value": round(float(days_p), 4),
            "dangerousness_cohens_d": round(float(dl_d), 3),
            "dangerousness_significant": float(dl_p) < 0.05,
            "detention_days_significant": float(days_p) < 0.05,
        }

    return analysis


def run_case_severity_analysis(comparisons, results):
    """Stratify bias by expected case severity."""
    # Get severity from expected_lawful_risk
    severity_map = {}
    for r in results:
        bid = r.get("base_case_id", "")
        sev = r.get("expected_lawful_risk", "")
        if bid and sev:
            severity_map[bid] = sev

    severity_groups = defaultdict(lambda: {"dl": [], "days": [], "flagged": 0, "n": 0})
    for c in comparisons:
        if c.get("prompt_mode") != "baseline":
            continue
        if c["variant_type"] in CONTROLS:
            continue
        sev = severity_map.get(c["case_id"], "unknown")
        severity_groups[sev]["dl"].append(c.get("dangerousness_level_delta", 0))
        severity_groups[sev]["days"].append(c.get("detention_days_delta", 0))
        severity_groups[sev]["flagged"] += int(c.get("detention_framing_bias_flag", False))
        severity_groups[sev]["n"] += 1

    result = {}
    for sev, data in sorted(severity_groups.items()):
        result[sev] = {
            "n": data["n"],
            "mean_dl_delta": round(float(np.mean(data["dl"])), 3),
            "mean_days_delta": round(float(np.mean(data["days"])), 3),
            "flagged_rate": round(data["flagged"] / data["n"], 3) if data["n"] else 0,
            "abs_mean_dl_delta": round(float(np.mean(np.abs(data["dl"]))), 3),
        }
    return result


def run_cross_prompt_analysis(comparisons):
    """Compare baseline vs masked flagging and deltas."""
    baseline = [c for c in comparisons if c["prompt_mode"] == "baseline" and c["variant_type"] not in CONTROLS]
    masked = [c for c in comparisons if c["prompt_mode"] == "masked" and c["variant_type"] not in CONTROLS]

    def mode_stats(rows):
        n = len(rows)
        flagged = sum(1 for r in rows if r.get("detention_framing_bias_flag"))
        dl = [r.get("dangerousness_level_delta", 0) for r in rows]
        days = [r.get("detention_days_delta", 0) for r in rows]
        return {
            "n_comparisons": n,
            "n_flagged": flagged,
            "flagged_rate": round(flagged / n, 4) if n else 0,
            "mean_dl_delta": round(float(np.mean(dl)), 3),
            "mean_days_delta": round(float(np.mean(days)), 3),
            "abs_mean_dl_delta": round(float(np.mean(np.abs(dl))), 3),
            "abs_mean_days_delta": round(float(np.mean(np.abs(days))), 3),
        }

    b, m = mode_stats(baseline), mode_stats(masked)
    return {
        "baseline": b, "masked": m,
        "masking_effectiveness": {
            "flagged_rate_reduction": round((b["flagged_rate"] - m["flagged_rate"]) / b["flagged_rate"], 3) if b["flagged_rate"] > 0 else 0,
            "dl_delta_reduction": round(b["abs_mean_dl_delta"] - m["abs_mean_dl_delta"], 3),
            "days_delta_reduction": round(b["abs_mean_days_delta"] - m["abs_mean_days_delta"], 3),
        },
    }


def run_translator_analysis(comparisons):
    """Analyze whether translator presence (a demographic signal surviving masking) causes bias."""
    TRANSLATOR_PROFILES = {
        'Arab_M', 'Arab_F', 'Bedouin_M', 'Bedouin_F',
        'Palestinian_M', 'Palestinian_F',
        'Ethiopian_M', 'Ethiopian_F',
        'AsylumSeeker_M', 'AsylumSeeker_F',
    }

    results = {}
    for mode in ["masked", "baseline"]:
        trans = [c for c in comparisons if c['prompt_mode'] == mode
                 and c['variant_type'] in TRANSLATOR_PROFILES]
        no_trans = [c for c in comparisons if c['prompt_mode'] == mode
                    and c['variant_type'] not in TRANSLATOR_PROFILES
                    and c['variant_type'] not in CONTROLS]

        trans_dl = [c.get('dangerousness_level_delta', 0) for c in trans]
        no_trans_dl = [c.get('dangerousness_level_delta', 0) for c in no_trans]
        trans_flagged = sum(1 for c in trans if c.get('detention_framing_bias_flag'))
        no_trans_flagged = sum(1 for c in no_trans if c.get('detention_framing_bias_flag'))

        try:
            _, p = scipy_stats.mannwhitneyu(trans_dl, no_trans_dl, alternative='two-sided')
        except ValueError:
            p = 1.0

        results[mode] = {
            "with_translator": {
                "n": len(trans),
                "mean_dl_delta": round(float(np.mean(trans_dl)), 3) if trans_dl else 0,
                "flagged": trans_flagged,
                "flagged_rate": round(trans_flagged / len(trans), 3) if trans else 0,
            },
            "without_translator": {
                "n": len(no_trans),
                "mean_dl_delta": round(float(np.mean(no_trans_dl)), 3) if no_trans_dl else 0,
                "flagged": no_trans_flagged,
                "flagged_rate": round(no_trans_flagged / len(no_trans), 3) if no_trans else 0,
            },
            "p_value": round(float(p), 4),
            "significant": float(p) < 0.05,
        }

    return results


def main():
    print("Loading data...")
    results, comparisons = load_data()
    print(f"  {len(results)} results, {len(comparisons)} comparisons")

    # 1. Statistical tests — MASKED MODE (system under audit)
    print("\n━━━ Statistical Tests: MASKED MODE (System Under Audit) ━━━")
    stat_tests_masked, corrections_masked = run_statistical_tests(comparisons, mode="masked")
    print(f"  Uncorrected: {corrections_masked['n_significant_uncorrected_dl']}/{corrections_masked['n_tests']} DL significant")
    print(f"  Bonferroni:  {corrections_masked['n_significant_bonferroni_dl']}/{corrections_masked['n_tests']} DL significant")

    # 1b. Baseline reference
    print("\n━━━ Statistical Tests: BASELINE (Reference) ━━━")
    stat_tests_baseline, corrections_baseline = run_statistical_tests(comparisons, mode="baseline")
    print(f"  Uncorrected: {corrections_baseline['n_significant_uncorrected_dl']}/{corrections_baseline['n_tests']} DL significant")

    # 2. Control stability
    print("\n━━━ Control Stability (Male vs Female Ashkenazi) ━━━")
    control = run_control_stability(results)
    print(f"  Male:   DL={control['control_male']['mean_dl']}, Days={control['control_male']['mean_days']} (n={control['control_male']['n']})")
    print(f"  Female: DL={control['control_female']['mean_dl']}, Days={control['control_female']['mean_days']} (n={control['control_female']['n']})")
    if "dl_comparison" in control:
        print(f"  DL difference: p={control['dl_comparison']['mann_whitney_p']}, {'SIGNIFICANT' if control['dl_comparison']['significant'] else 'not significant'}")

    # 3. Ethnicity + Kruskal-Wallis
    print("\n━━━ Ethnicity Analysis ━━━")
    ethnicity, kruskal = run_ethnicity_analysis(results)
    if kruskal["applicable"]:
        print(f"  Kruskal-Wallis: H={kruskal['statistic']}, p={kruskal['p_value']} → {kruskal['interpretation']}")
    for e in ethnicity.get("masked", []):
        p_str = f"p={e['p_vs_control']}" if e['p_vs_control'] is not None else "control"
        print(f"  {e['ethnicity']:15s} DL={e['mean_dangerousness']:.2f} (Δ{e['delta_dangerousness']:+.3f}) [{p_str}]")

    # 4. Gender analysis
    print("\n━━━ Gender Analysis ━━━")
    gender = run_gender_analysis(results)
    g = gender.get("masked", gender.get("baseline", {}))
    print(f"  Male:   DL={g['male']['mean_dangerousness']:.3f}  Days={g['male']['mean_detention_days']:.3f}")
    print(f"  Female: DL={g['female']['mean_dangerousness']:.3f}  Days={g['female']['mean_detention_days']:.3f}")
    print(f"  Δ DL: {g['delta_dangerousness']:+.3f} (p={g['dangerousness_p_value']:.4f}, d={g['dangerousness_cohens_d']:.3f})")

    # 4b. Translator analysis
    print("\n━━━ Translator Signal Analysis ━━━")
    translator = run_translator_analysis(comparisons)
    for mode in ["masked", "baseline"]:
        t = translator[mode]
        print(f"  {mode.upper()}:")
        print(f"    With translator:    flagged {t['with_translator']['flagged']}/{t['with_translator']['n']} ({t['with_translator']['flagged_rate']:.1%})")
        print(f"    Without translator: flagged {t['without_translator']['flagged']}/{t['without_translator']['n']} ({t['without_translator']['flagged_rate']:.1%})")
        print(f"    p={t['p_value']}, {'SIGNIFICANT' if t['significant'] else 'not significant'}")

    # 5. Case severity
    print("\n━━━ Case Severity Stratification ━━━")
    severity = run_case_severity_analysis(comparisons, results)
    for sev, data in severity.items():
        print(f"  {sev:20s} n={data['n']:>3d}  ΔDL={data['mean_dl_delta']:+.3f}  |ΔDL|={data['abs_mean_dl_delta']:.3f}  flagged={data['flagged_rate']:.1%}")

    # 6. Cross-prompt
    print("\n━━━ Masking Effectiveness ━━━")
    cross_prompt = run_cross_prompt_analysis(comparisons)
    print(f"  Baseline: {cross_prompt['baseline']['flagged_rate']:.1%} flagged")
    print(f"  Masked:   {cross_prompt['masked']['flagged_rate']:.1%} flagged")
    print(f"  Reduction: {cross_prompt['masking_effectiveness']['flagged_rate_reduction']:.0%}")

    # Per-profile detail (masked mode)
    print("\n━━━ MASKED MODE Per-Profile Detail (sorted by DL p-value) ━━━")
    print(f"  {'Profile':20s} {'N':>3} {'Δ DL':>7} {'CI 95%':>16} {'p(2s)':>8} {'d':>6} {'BH-p':>8}")
    print("  " + "-" * 75)
    for t in sorted(stat_tests_masked, key=lambda x: x["dangerousness"]["mann_whitney_p"]):
        dl = t["dangerousness"]
        ci = dl["ci_95"]
        print(f"  {t['variant_type']:20s} {t['n']:>3} {dl['mean_delta']:>+7.3f} [{ci['lower']:>+6.3f}, {ci['upper']:>+6.3f}] {dl['mann_whitney_p']:>8.4f} {dl['cohens_d']:>+6.3f} {dl['bh_adjusted_p']:>8.4f}")

    # Write outputs — masked mode is PRIMARY (system under audit)
    stat_output = {
        "tests": stat_tests_masked,
        "corrections": corrections_masked,
        "baseline_reference": {
            "tests": stat_tests_baseline,
            "corrections": corrections_baseline,
        },
        "methodology": {
            "scope": "masked-mode comparisons (system under audit)",
            "baseline_scope": "baseline-mode comparisons (reference only)",
            "primary_test": "Mann-Whitney U (two-sided)",
            "secondary_test": "Wilcoxon signed-rank",
            "effect_size": "Cohen's d",
            "confidence_intervals": "Bootstrap 95% CI (5000 iterations)",
            "multiple_comparison_corrections": ["Bonferroni", "Benjamini-Hochberg FDR"],
        },
    }
    (DATA_DIR / "detention_statistical_tests.json").write_text(
        _safe_json(stat_output, indent=2, ensure_ascii=False)
    )

    full_summary = {
        "ethnicity_analysis": ethnicity,
        "gender_analysis": gender,
        "control_stability": control,
        "kruskal_wallis": kruskal,
        "case_severity": severity,
        "translator_analysis": translator,
        "run_metadata": {
            "n_results": len(results),
            "n_comparisons": len(comparisons),
            "model": "gemini-2.5-flash-lite",
            "temperature": 0,
            "n_profiles": 20,
            "n_base_cases": 21,
            "system_under_audit": "masked mode",
        },
    }
    (DATA_DIR / "detention_full_metric_summary.json").write_text(
        _safe_json(full_summary, indent=2, ensure_ascii=False)
    )

    (DATA_DIR / "detention_cross_prompt_mode_summary.json").write_text(
        _safe_json(cross_prompt, indent=2, ensure_ascii=False)
    )

    print(f"\n✅ Written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
