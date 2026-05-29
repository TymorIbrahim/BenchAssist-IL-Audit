"""Streamlit dashboard for reviewing BenchAssist-IL audit results."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from benchassist.audit_metrics import (
    infer_remedy_strength_score,
    output_length_words,
    skepticism_score,
    urgency_score,
)

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
OUTPUTS_PATH = RESULTS_DIR / "outputs" / "model_outputs.csv"
GROUP_SUMMARY_PATH = RESULTS_DIR / "tables" / "group_summary.csv"
FLAGGED_PATH = RESULTS_DIR / "tables" / "flagged_cases.csv"
CHARTS_DIR = RESULTS_DIR / "charts"

PIPELINE_HELP = """
### Pipeline not run yet

Generate audit artefacts with:

```bash
# 1. Run model batch (mock, no API key)
python -m benchassist.run_batch --provider mock --limit 10

# 2. Compute audit metrics
benchassist audit

# 3. (Optional) Generate report and charts
python -m benchassist.report
```

Expected files:
- `results/outputs/model_outputs.csv`
- `results/tables/group_summary.csv`
- `results/tables/flagged_cases.csv`
- `results/charts/*.png` (after report step)
"""


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None


def _safe_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _row_metrics(row: pd.Series) -> dict[str, object]:
    reasoning = _safe_str(row.get("reasoning"))
    action = _safe_str(row.get("recommended_action"))
    limitations = _safe_str(row.get("limitations"))
    direction = _safe_str(row.get("recommended_direction")) or None
    return {
        "urgency": _safe_str(row.get("urgency")) or "N/A",
        "urgency_score": urgency_score(_safe_str(row.get("urgency")) or None),
        "recommended_direction": direction or "N/A",
        "remedy_strength_score": infer_remedy_strength_score(direction, action),
        "skepticism_score": skepticism_score(
            reasoning, action, limitations, _safe_str(row.get("case_summary"))
        ),
        "output_length_words": output_length_words(reasoning, action, limitations),
    }


def _parse_error_rate(df: pd.DataFrame) -> float:
    if df is None or df.empty or "parse_error" not in df.columns:
        return 0.0
    errors = df["parse_error"].apply(lambda v: bool(_safe_str(v)))
    return float(errors.mean()) if len(errors) else 0.0


def _render_output_card(row: pd.Series, title: str) -> None:
    metrics = _row_metrics(row)
    st.subheader(title)
    st.caption(f"Variant: `{row.get('variant_type', 'N/A')}` · Cue: {row.get('demographic_cue', 'N/A')}")

    with st.expander("Input text", expanded=False):
        st.text(_safe_str(row.get("input_text")) or "_No input text_")

    st.markdown(
        f"- **Urgency:** {metrics['urgency']} (score {metrics['urgency_score']})\n"
        f"- **Direction:** {metrics['recommended_direction']}\n"
        f"- **Remedy strength:** {metrics['remedy_strength_score']}\n"
        f"- **Skepticism score:** {metrics['skepticism_score']}\n"
        f"- **Output length (words):** {metrics['output_length_words']}"
    )
    st.markdown(f"**Recommended action:** {_safe_str(row.get('recommended_action')) or '_N/A_'}")
    st.markdown(f"**Reasoning:** {_safe_str(row.get('reasoning')) or '_N/A_'}")


def _highlight_differences(neutral: pd.Series, variant: pd.Series) -> None:
    n = _row_metrics(neutral)
    v = _row_metrics(variant)

    cols = st.columns(5)
    comparisons = [
        ("Urgency score", n["urgency_score"], v["urgency_score"]),
        ("Remedy strength", n["remedy_strength_score"], v["remedy_strength_score"]),
        ("Skepticism", n["skepticism_score"], v["skepticism_score"]),
        ("Output length", n["output_length_words"], v["output_length_words"]),
        ("Direction", n["recommended_direction"], v["recommended_direction"]),
    ]

    for col, (label, n_val, v_val) in zip(cols, comparisons):
        with col:
            if label == "Direction":
                changed = str(n_val) != str(v_val)
                col.write(f"**{label}**")
                col.write(f"`{v_val}`" + (" ⚠️ changed" if changed else " ✓ same"))
            else:
                try:
                    delta = float(v_val) - float(n_val)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    delta = None
                col.metric(
                    label,
                    v_val,
                    delta=delta if delta not in (None, 0) else None,
                )


def main() -> None:
    st.set_page_config(
        page_title="BenchAssist-IL Audit Dashboard",
        page_icon="⚖️",
        layout="wide",
    )
    st.title("BenchAssist-IL Audit Dashboard")
    st.caption("Review counterfactual fairness audit results")

    model_outputs = load_csv(OUTPUTS_PATH)
    group_summary = load_csv(GROUP_SUMMARY_PATH)
    flagged_cases = load_csv(FLAGGED_PATH)

    if model_outputs is None:
        st.warning("Required outputs are missing.")
        st.markdown(PIPELINE_HELP)
        return

    # ── 1. Overview ──────────────────────────────────────────────────────
    st.header("1. Overview")
    o1, o2, o3, o4 = st.columns(4)
    case_count = model_outputs["case_id"].nunique() if "case_id" in model_outputs.columns else 0
    variant_count = len(model_outputs)
    model_name = (
        model_outputs["model_name"].dropna().iloc[0]
        if "model_name" in model_outputs.columns and model_outputs["model_name"].notna().any()
        else "unknown"
    )
    parse_rate = _parse_error_rate(model_outputs)

    o1.metric("Base cases", case_count)
    o2.metric("Variants run", variant_count)
    o3.metric("Model", model_name)
    o4.metric("Parse error rate", f"{parse_rate:.1%}")

    if group_summary is None:
        st.info("Run `benchassist audit` to generate group summary tables.")
    if flagged_cases is None or flagged_cases.empty:
        st.info("`flagged_cases.csv` is empty — no rows met automated flag thresholds.")

    st.divider()

    # ── 2. Group Summary ─────────────────────────────────────────────────
    st.header("2. Group Summary")
    if group_summary is not None and not group_summary.empty:
        st.dataframe(group_summary, use_container_width=True, hide_index=True)
    else:
        st.markdown("_Group summary not available._")

    st.divider()

    # ── 3. Charts ────────────────────────────────────────────────────────
    st.header("3. Charts")
    chart_files = sorted(CHARTS_DIR.glob("*.png")) if CHARTS_DIR.exists() else []
    if chart_files:
        chart_cols = st.columns(2)
        for index, chart_path in enumerate(chart_files):
            with chart_cols[index % 2]:
                st.image(str(chart_path), caption=chart_path.name, use_container_width=True)
    else:
        st.markdown(
            "_No charts found in `results/charts/`. "
            "Run `python -m benchassist.report` after the audit step._"
        )

    st.divider()

    # ── 4. Flagged Cases ─────────────────────────────────────────────────
    st.header("4. Flagged Cases")

    if "case_id" not in model_outputs.columns:
        st.error("model_outputs.csv is missing a `case_id` column.")
    else:
        case_ids = sorted(model_outputs["case_id"].dropna().unique().tolist())
        default_case = case_ids[0]
        if flagged_cases is not None and not flagged_cases.empty and "case_id" in flagged_cases.columns:
            flagged_ids = flagged_cases["case_id"].dropna().unique().tolist()
            if flagged_ids:
                default_case = flagged_ids[0]

        default_index = case_ids.index(default_case) if default_case in case_ids else 0
        selected_case = st.selectbox("Case ID", case_ids, index=default_index)

        case_df = model_outputs[model_outputs["case_id"] == selected_case]
        variant_types = (
            case_df[case_df["variant_type"] != "neutral_he"]["variant_type"]
            .dropna()
            .unique()
            .tolist()
        )

        if not variant_types:
            st.warning("No non-neutral variants found for this case.")
        else:
            selected_variant_type = st.selectbox("Demographic variant", variant_types)
            neutral_rows = case_df[case_df["variant_type"] == "neutral_he"]
            variant_rows = case_df[case_df["variant_type"] == selected_variant_type]

            if neutral_rows.empty:
                st.warning("No `neutral_he` row for this case.")
            elif variant_rows.empty:
                st.warning(f"No row for variant `{selected_variant_type}`.")
            else:
                neutral = neutral_rows.iloc[0]
                variant = variant_rows.iloc[0]

                st.markdown("#### Difference highlights (variant vs neutral)")
                _highlight_differences(neutral, variant)

                left, right = st.columns(2)
                with left:
                    _render_output_card(neutral, "Neutral (`neutral_he`)")
                with right:
                    _render_output_card(variant, f"Variant (`{selected_variant_type}`)")

                if flagged_cases is not None and not flagged_cases.empty:
                    flags = flagged_cases[
                        (flagged_cases["case_id"] == selected_case)
                        & (flagged_cases.get("variant_type", pd.Series(dtype=str)) == selected_variant_type)
                    ]
                    if not flags.empty and "flags" in flags.columns:
                        st.markdown(f"**Automated flags:** `{flags.iloc[0]['flags']}`")

    st.divider()

    # ── 5. Raw Outputs ───────────────────────────────────────────────────
    st.header("5. Raw Outputs")

    search = st.text_input("Search (case_id, variant_type, demographic_cue, text fields)")
    display_cols = [
        c
        for c in [
            "case_id",
            "variant_id",
            "variant_type",
            "demographic_cue",
            "urgency",
            "recommended_direction",
            "confidence",
            "parse_error",
            "model_name",
            "timestamp",
        ]
        if c in model_outputs.columns
    ]
    filtered = model_outputs.copy()

    if search.strip():
        mask = pd.Series(False, index=filtered.index)
        for col in filtered.columns:
            try:
                mask |= filtered[col].astype(str).str.contains(
                    search, case=False, na=False
                )
            except (TypeError, ValueError):
                continue
        filtered = filtered[mask]

    st.caption(f"Showing {len(filtered)} of {len(model_outputs)} rows")
    st.dataframe(
        filtered[display_cols] if display_cols else filtered,
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Full row detail (selected index)"):
        if filtered.empty:
            st.write("_No rows to display._")
        else:
            idx = st.number_input(
                "Row index",
                min_value=0,
                max_value=len(filtered) - 1,
                value=0,
                step=1,
            )
            st.json(json.loads(filtered.iloc[int(idx)].to_json()))


if __name__ == "__main__":
    main()
