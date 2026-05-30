"""Interactive Streamlit dashboard for BenchAssist-IL audit results."""

from __future__ import annotations

try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit(
        "Streamlit is required for the dashboard. Install with:\n"
        "  pip install -e '.[dashboard]'\n"
        "Then run:\n"
        "  streamlit run app.py"
    ) from exc

import pandas as pd

from benchassist.dashboard_utils import (
    GROUNDING_AUDIT_HELP,
    METRIC_GLOSSARY,
    METHODOLOGY_CARDS,
    NARRATIVE_ROBUSTNESS_HELP,
    RISK_FLAG_COLUMNS,
    STATISTICAL_CI_HELP,
    STEREOTYPE_AUDIT_HELP,
    SUBMISSION_CHECKLIST,
    VALIDITY_AUDIT_HELP,
    ExpertFilters,
    add_severity_columns,
    aggregate_group_summary,
    build_case_pair_options,
    build_difference_comparison_table,
    build_loaded_paths_map,
    build_review_note_row,
    case_comparison_data,
    compute_overview_metrics,
    compute_parse_error_rate,
    csv_download_bytes,
    discover_audit_artifacts,
    experiment_token_from_run_label,
    extract_run_metadata,
    filter_dataframe,
    filter_expert_dataframe,
    format_display_value,
    format_rate_display,
    friendly_run_label,
    glossary_markdown,
    latest_file,
    list_hallucination_suffixes,
    list_narrative_robustness_suffixes,
    list_statistical_suffixes,
    list_validity_suffixes,
    load_csv_optional,
    make_bar_chart,
    merge_validity_into_dataframe,
    methodology_export_markdown,
    mitigation_delta_label,
    multiselect_options,
    pick_hallucination_paths,
    pick_mitigation_for_run,
    pick_narrative_robustness_paths,
    pick_stereotype_paths_for_run,
    pick_statistical_paths,
    pick_validity_paths,
    render_empty_state,
    review_note_csv_bytes,
    review_table_dataframe,
    safe_read_markdown,
    search_cases_dataframe,
    severity_priority_label,
    severity_score,
    sort_flagged_dataframe,
    sort_runs_by_priority,
    strongest_signal_summary,
    summarize_statistical_signals,
)
from benchassist.dashboard_utils import _coerce_bool, _format_evidence, _safe_str

INTERPRETATION_BOX = (
    "This dashboard surfaces **potential disparities and instability** in generated "
    "legal framing. It does **not** prove unlawful discrimination. Flagged cases require "
    "**human legal review** before any substantive fairness claim."
)

PIPELINE_HELP = """
**Run the pipeline or metrics first**, then refresh this page.

```bash
python -m benchassist.verify_pipeline --provider mock --limit 20
```

Expected artefacts under `results/tables/`, `results/outputs/`, and `results/charts/`.
"""

LEGAL_REVIEW_QUESTIONS = [
    "Are the facts truly equivalent between neutral and variant inputs?",
    "Is the output difference legally justified given the variant text?",
    "Did the model demand more evidence from the variant party?",
    "Did the model frame the variant party as less credible?",
    "Could language quality (not legal substance) have affected the recommendation?",
    "Would this memo influence a clerk or judge's framing of the case?",
    "Should this pair be included in the final written report?",
]

HOW_TO_USE = """
1. **Overview** — run metadata and headline audit signal rates (screening only).
2. **Main Audit Results** — rates by variant type with charts.
3. **Flagged Cases** — priority-sorted pairs for human review.
4. **Case Explorer** — side-by-side neutral vs variant (best for presentations).
5. **Counterfactual Validity** — which pairs support strict bias comparisons.
6. **Mitigation / Narrative / Stereotype / Grounding / Statistics** — specialized audits.
7. **Qualitative Review** and **Human Review** — expert workflow.
8. **Reports & Exports** — Markdown reports and CSV downloads.
"""

WARNING_BADGES = (
    ("Not legal advice", "Outputs are illustrative audit artefacts only."),
    ("Not an AI judge", "BenchAssist-IL is non-binding decision support."),
    ("Synthetic audit setting", "Cases are controlled counterfactuals, not real dockets."),
    ("Human legal review required", "Metrics are screening signals, not proof of discrimination."),
)


def _download_csv_button(df: pd.DataFrame, label: str, filename: str, key: str = "") -> None:
    if df.empty:
        return
    st.download_button(
        label=label,
        data=csv_download_bytes(df),
        file_name=filename,
        mime="text/csv",
        key=key or filename,
    )


def _download_text_button(content: str, label: str, filename: str, key: str) -> None:
    st.download_button(
        label=label,
        data=content.encode("utf-8"),
        file_name=filename,
        mime="text/markdown",
        key=key,
    )


def _render_project_intro() -> None:
    st.markdown(
        "BenchAssist-IL is a **toy, non-binding** judicial decision-support assistant "
        "for **Israeli housing / landlord–tenant** disputes. This dashboard reviews "
        "**legal-framing** differences across counterfactual variants — not final judicial outcomes."
    )


def _render_warning_badges() -> None:
    cols = st.columns(len(WARNING_BADGES))
    for col, (title, detail) in zip(cols, WARNING_BADGES):
        with col:
            st.warning(f"**{title}**\n\n{detail}")


def _render_executive_summary() -> None:
    st.markdown("### Review workflow")
    st.markdown(HOW_TO_USE)
    with st.expander("Metric glossary (quick reference)", expanded=False):
        st.markdown(glossary_markdown()[:6000])


def _render_run_metadata(meta: dict[str, str]) -> None:
    st.markdown("### Run metadata")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Model", meta.get("model_name", "—"))
    c2.metric("Provider", meta.get("provider", "—"))
    c3.metric("Prompt mode", meta.get("prompt_mode", "—"))
    c4.metric("Schema", meta.get("schema_version", "—"))
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Model outputs", meta.get("n_outputs", "—"))
    c6.metric("Base cases", meta.get("n_case_ids", "—"))
    c7.metric("Variant types", meta.get("n_variant_types", "—"))
    c8.metric("Parse error rate", meta.get("parse_error_rate", "—"))


def _render_metric_cards(metrics: dict) -> None:
    st.markdown("### Headline audit signal rates")
    st.caption("Screening metrics only — not proof of bias or unlawful discrimination.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Counterfactual pairs", metrics.get("n_pairs") or 0)
    c2.metric("Flagged cases (automated)", metrics.get("n_flagged") or 0)
    c3.metric(
        "Legal framing signal rate",
        format_rate_display(metrics.get("legal_framing_bias_flag_rate")),
    )
    c4.metric(
        "Action type flip rate",
        format_rate_display(metrics.get("action_type_flip_rate")),
    )
    c5, c6, c7 = st.columns(3)
    c5.metric(
        "Remedy weaker rate",
        format_rate_display(metrics.get("remedy_weaker_rate")),
    )
    c6.metric(
        "Evidence burden higher rate",
        format_rate_display(metrics.get("evidence_burden_higher_rate")),
    )
    c7.metric(
        "Credibility more skeptical rate",
        format_rate_display(metrics.get("credibility_more_skeptical_rate")),
    )
    c8, _, _ = st.columns(3)
    c8.metric(
        "Rights orientation weaker rate",
        format_rate_display(metrics.get("rights_orientation_weaker_rate")),
    )


def _render_case_card(row: pd.Series | None, title: str) -> None:
    st.markdown(f"#### {title}")
    if row is None:
        st.info("Not available for this selection.")
        return
    st.caption("Input")
    st.text(_safe_str(row.get("input_text")) or _safe_str(row.get("blinded_input_text")) or "Not available")
    if "case_summary" in row.index:
        with st.expander("Case summary", expanded=False):
            st.text(_safe_str(row.get("case_summary")) or "Not available")
    st.caption("Structured output")
    fields = [
        ("Urgency", "urgency"),
        ("Recommended action type", "recommended_action_type"),
        ("Remedy strength score", "remedy_strength_score"),
        ("Evidence burden level", "evidence_burden_level"),
        ("Credibility framing", "party_credibility_framing"),
        ("Rights orientation", "rights_orientation"),
        ("Procedural posture", "procedural_posture"),
        ("Confidence", "confidence"),
    ]
    for label, key in fields:
        if key in row.index:
            st.markdown(f"**{label}:** {format_display_value(row.get(key))}")
    with st.expander("Reasoning", expanded=False):
        st.text(_safe_str(row.get("reasoning_text")) or _safe_str(row.get("reasoning")) or "Not available")
    with st.expander("Evidence needed", expanded=False):
        st.text(_format_evidence(row.get("evidence_needed")))
    with st.expander("Limitations", expanded=False):
        st.text(_safe_str(row.get("limitations")) or "Not available")


def _plot_metric_bars(group_df: pd.DataFrame, metric: str, title: str) -> None:
    if group_df.empty or metric not in group_df.columns:
        st.caption(f"_{metric} not available._")
        return
    fig = make_bar_chart(group_df, "variant_type", metric, title)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(group_df.set_index("variant_type")[metric])


def main() -> None:
    st.set_page_config(
        page_title="BenchAssist-IL Audit Dashboard",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("BenchAssist-IL Audit")
    st.caption("Responsible AI review dashboard · local files only · no live API calls")

    artifacts = discover_audit_artifacts()
    if not artifacts.runs:
        st.warning("No audit run artefacts found.")
        st.markdown(PIPELINE_HELP)
        return

    runs = sort_runs_by_priority(artifacts.runs)
    default_run = runs[0]

    with st.sidebar:
        st.header("BenchAssist-IL Audit")
        use_latest = st.checkbox(
            "Use latest files automatically",
            value=True,
            help="Prefer newest Gemini real runs over QA/mock when selecting defaults.",
        )
        run_options = {friendly_run_label(r.label): r for r in runs}
        default_label = friendly_run_label(default_run.label)
        selected_friendly = st.selectbox(
            "Audit run",
            list(run_options.keys()),
            index=list(run_options.keys()).index(default_label)
            if default_label in run_options
            else 0,
        )
        run = run_options[selected_friendly]
        exp_token = experiment_token_from_run_label(run.label)
        st.caption(f"Run key: `{run.label}`")
        if use_latest:
            st.caption("Auto-priority: Gemini real > pilot > QA/mock")

        group_df = load_csv_optional(run.group_summary)
        pairwise_df = load_csv_optional(run.pairwise)
        flagged_df = load_csv_optional(run.flagged)
        outputs_df = load_csv_optional(run.outputs)
        qualitative_df = (
            load_csv_optional(run.qualitative)
            if run.qualitative and run.qualitative.suffix == ".csv"
            else pd.DataFrame()
        )

        st.divider()
        st.subheader("Search")
        search_query = st.text_input(
            "Search cases",
            placeholder="case_id, variant, cue, input, reasoning…",
        )

        st.subheader("Variant filters")
        base_filter_df = pairwise_df if not pairwise_df.empty else flagged_df
        variant_types = st.multiselect(
            "Variant type", multiselect_options(base_filter_df, "variant_type")
        )
        demographic_cues = st.multiselect(
            "Demographic cue", multiselect_options(base_filter_df, "demographic_cue")
        )
        languages = st.multiselect(
            "Language", multiselect_options(base_filter_df, "language")
        )

        st.subheader("Review priority")
        review_priorities = st.multiselect(
            "Show priority bands",
            ["Low", "Medium", "High", "Very high"],
            default=[],
            help="Severity indicates review priority, not discrimination.",
        )

        st.subheader("Legal-expert filters")
        expert = ExpertFilters(
            review_priorities=review_priorities or None,
            only_remedy_weaker=st.checkbox("Only weaker remedy"),
            only_evidence_burden_higher=st.checkbox("Only higher evidence burden"),
            only_credibility_skeptical=st.checkbox("Only more skeptical credibility"),
            only_language_access=st.checkbox("Only language-access variants"),
            only_intersectional=st.checkbox("Only intersectional variants"),
            only_arabic=st.checkbox("Only Arabic inputs"),
            only_non_native_hebrew=st.checkbox("Only non-native Hebrew inputs"),
        )

        st.subheader("Risk flags (show only if)")
        risk_flags: dict[str, bool] = {}
        for col in RISK_FLAG_COLUMNS:
            if col in base_filter_df.columns:
                risk_flags[col] = st.checkbox(col.replace("_", " "), value=False)

        sort_key = st.selectbox(
            "Sort flagged cases by",
            [
                s
                for s in (
                    "severity_score",
                    "remedy_strength_delta",
                    "evidence_burden_delta",
                    "credibility_skepticism_delta",
                )
                if s in flagged_df.columns or s == "severity_score"
            ]
            or ["severity_score"],
        )
        flagged_only = st.checkbox(
            "Flagged pairs only",
            value=False,
            help="When no automated flags exist, turn off to review all variant pairs.",
        )
        st.divider()
        with st.expander("Glossary", expanded=False):
            for key, parts in list(METRIC_GLOSSARY.items())[:8]:
                st.markdown(f"**{key}** — {parts['measure']}")

    val_paths_sidebar = pick_validity_paths(artifacts, exp_token)
    validity_sidebar_df = load_csv_optional(val_paths_sidebar.get("per_variant"))
    validity_categories = st.multiselect(
        "Validity category",
        multiselect_options(validity_sidebar_df, "validity_category"),
    )

    stereotype_paths = pick_stereotype_paths_for_run(artifacts, run.label)

    filters = {
        "variant_types": variant_types or None,
        "demographic_cues": demographic_cues or None,
        "languages": languages or None,
        "risk_flags": risk_flags,
    }
    filtered_pairwise = filter_expert_dataframe(
        filter_dataframe(pairwise_df, **filters), expert
    )
    filtered_flagged = filter_expert_dataframe(
        filter_dataframe(flagged_df, **filters), expert
    )
    if validity_categories and not validity_sidebar_df.empty:
        filtered_pairwise = merge_validity_into_dataframe(
            filtered_pairwise, validity_sidebar_df
        )
        filtered_flagged = merge_validity_into_dataframe(
            filtered_flagged, validity_sidebar_df
        )
        if "validity_category" in filtered_pairwise.columns:
            filtered_pairwise = filtered_pairwise[
                filtered_pairwise["validity_category"].isin(validity_categories)
            ]
        if "validity_category" in filtered_flagged.columns:
            filtered_flagged = filtered_flagged[
                filtered_flagged["validity_category"].isin(validity_categories)
            ]

    review_source = review_table_dataframe(
        filtered_flagged, filtered_pairwise, flagged_only=flagged_only
    )
    if search_query.strip():
        filtered_pairwise = search_cases_dataframe(
            filtered_pairwise, search_query, outputs_df=outputs_df
        )
        filtered_flagged = search_cases_dataframe(
            filtered_flagged, search_query, outputs_df=outputs_df
        )

    filtered_group = aggregate_group_summary(group_df)
    if variant_types and "variant_type" in filtered_group.columns:
        filtered_group = filtered_group[filtered_group["variant_type"].isin(variant_types)]

    run_meta = extract_run_metadata(run, outputs_df, pairwise_df, group_df)
    metrics = compute_overview_metrics(filtered_pairwise, filtered_group, review_source)

    loaded_paths = build_loaded_paths_map(
        run,
        {
            "validity": val_paths_sidebar.get("per_variant"),
            "stereotype_group": stereotype_paths.get("group_summary"),
            "mitigation": pick_mitigation_for_run(artifacts, run.label),
            "final_report": latest_file(artifacts.final_report),
        },
    )
    hr_candidates = [
        p for p in artifacts.human_review_template if exp_token in p.stem
    ]
    template_df = load_csv_optional(
        latest_file(hr_candidates) or latest_file(artifacts.human_review_template)
    )
    stereotype_group_df = load_csv_optional(stereotype_paths.get("group_summary"))
    stereotype_flagged_df = load_csv_optional(stereotype_paths.get("flagged_examples"))
    stereotype_per_df = load_csv_optional(stereotype_paths.get("per_output"))

    with st.sidebar:
        with st.expander("Loaded files", expanded=False):
            for name, path in loaded_paths.items():
                st.markdown(f"- **{name}:** `{path}`")

    tabs = st.tabs(
        [
            "Overview",
            "Main Audit Results",
            "Flagged Cases",
            "Case Explorer",
            "Counterfactual Validity",
            "Mitigation Comparison",
            "Narrative Robustness",
            "Stereotype & Identity Leakage",
            "Legal Grounding & Hallucination",
            "Statistical Uncertainty",
            "Qualitative Review",
            "Human Review",
            "Reports & Exports",
            "Methodology & Limitations",
        ]
    )

    with tabs[0]:
        _render_project_intro()
        _render_warning_badges()
        st.divider()
        _render_run_metadata(run_meta)
        st.divider()
        _render_metric_cards(metrics)
        st.info(INTERPRETATION_BOX)
        _render_executive_summary()
        if artifacts.final_report:
            st.markdown(
                f"Written report: `results/report/{latest_file(artifacts.final_report).name}`"
            )
        pilot_rep = latest_file(artifacts.gemini_pilot_report)
        if pilot_rep:
            st.markdown(f"Pilot run report: `{pilot_rep}`")

    with tabs[1]:
        st.subheader("Main audit results by variant type")
        st.markdown(
            "Rates compare each counterfactual variant to the neutral Hebrew baseline for the same case. "
            "**High rates are screening signals** — confirm with validity categories and human review."
        )
        with st.expander("Metric glossary", expanded=False):
            for key, parts in METRIC_GLOSSARY.items():
                st.markdown(f"**`{key}`** — {parts['measure']} *({parts['caution']})*")
        if filtered_group.empty:
            st.markdown(
                render_empty_state(
                    "v2_group_summary",
                    "python -m benchassist.audit_metrics --version v2 --input <outputs.csv> --output-suffix <suffix>",
                )
            )
        else:
            top_n = st.slider("Top variant types per chart", 5, 25, 15, key="main_top_n")
            for metric, title in [
                ("legal_framing_bias_flag_rate", "Audit signal: legal framing flag rate"),
                ("action_type_flip_rate", "Audit signal: action type flip rate"),
                ("remedy_weaker_rate", "Audit signal: remedy weaker rate"),
                ("evidence_burden_higher_rate", "Audit signal: evidence burden higher rate"),
                ("credibility_more_skeptical_rate", "Audit signal: credibility more skeptical rate"),
                ("rights_orientation_weaker_rate", "Audit signal: rights orientation weaker rate"),
            ]:
                fig = make_bar_chart(
                    filtered_group, "variant_type", metric, title, top_n=top_n
                )
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    _plot_metric_bars(filtered_group, metric, title)
            with st.expander("Full group summary table", expanded=False):
                st.dataframe(filtered_group, use_container_width=True, hide_index=True)
            _download_csv_button(
                filtered_group, "Download group summary CSV", "group_summary_filtered.csv"
            )

    with tabs[2]:
        st.subheader("Flagged cases & review queue")
        st.caption(
            "Sorted by review priority. Severity guides review order — **not** a finding of discrimination."
        )
        if review_source.empty:
            st.markdown(
                render_empty_state(
                    "v2_flagged_cases / pairwise",
                    "python -m benchassist.audit_metrics --version v2 --input <outputs.csv> --output-suffix <suffix>",
                )
            )
        else:
            display_flagged = add_severity_columns(
                sort_flagged_dataframe(review_source, sort_key)
            )
            if "strongest_signal" not in display_flagged.columns:
                display_flagged = display_flagged.copy()
                display_flagged["strongest_signal"] = display_flagged.apply(
                    strongest_signal_summary, axis=1
                )
            show_cols = [
                c
                for c in (
                    "severity_score",
                    "review_priority",
                    "case_id",
                    "variant_id",
                    "variant_type",
                    "demographic_cue",
                    "validity_category",
                    "strongest_signal",
                    "legal_framing_bias_flag",
                    "remedy_weaker",
                    "evidence_burden_higher",
                    "credibility_more_skeptical",
                    "action_type_flip",
                )
                if c in display_flagged.columns
            ]
            st.dataframe(display_flagged[show_cols], use_container_width=True, hide_index=True)
            _download_csv_button(
                display_flagged, "Download review queue CSV", "flagged_cases_filtered.csv"
            )
            if not display_flagged.empty:
                st.markdown("#### Selected case preview")
                preview = display_flagged.iloc[0]
                st.markdown(
                    f"**{preview.get('case_id')} · {preview.get('variant_type')}** — "
                    f"{preview.get('strongest_signal', '')}"
                )
                if "input_text" in preview.index:
                    st.text_area(
                        "Variant input (preview)",
                        _safe_str(preview.get("input_text")),
                        height=120,
                        disabled=True,
                    )

    with tabs[3]:
        st.subheader("Case explorer")
        st.caption(
            "Side-by-side review for legal experts. Terms: **Flagged**, **Potential concern**, "
            "**Requires human review** — not automatic findings of discrimination."
        )
        explorer_source = filtered_pairwise if not filtered_pairwise.empty else filtered_flagged
        if explorer_source.empty and outputs_df.empty:
            st.info("Load pairwise comparison or model outputs to explore cases.")
        else:
            pair_options = build_case_pair_options(explorer_source)
            if not pair_options:
                st.warning("No non-neutral variant pairs available.")
            else:
                labels = [p[0] for p in pair_options]
                selected_label = st.selectbox(
                    "Case pair (sorted by review priority)",
                    labels,
                    key="case_pair_select",
                )
                selected_case = selected_variant = ""
                for label, case_id, variant_type in pair_options:
                    if label == selected_label:
                        selected_case, selected_variant = case_id, variant_type
                        break

                neutral_row, variant_row, pairwise_row = case_comparison_data(
                    outputs_df, filtered_pairwise, selected_case, selected_variant
                )
                if pairwise_row is not None:
                    sc = severity_score(pairwise_row)
                    st.markdown(
                        f"**Review priority:** {severity_priority_label(sc)} "
                        f"(severity score {sc} — screening urgency only)"
                    )
                    st.markdown(f"**Strongest signal:** {strongest_signal_summary(pairwise_row)}")

                if not validity_sidebar_df.empty and selected_variant:
                    vrow = validity_sidebar_df[
                        validity_sidebar_df["variant_type"] == selected_variant
                    ]
                    if not vrow.empty:
                        st.caption(
                            f"Validity: **{vrow.iloc[0].get('validity_category', '—')}** · "
                            f"Direct bias eligible: "
                            f"{format_display_value(vrow.iloc[0].get('direct_bias_analysis_eligible'))}"
                        )
                if not stereotype_per_df.empty and "variant_id" in stereotype_per_df.columns:
                    srow = stereotype_per_df[
                        stereotype_per_df["variant_id"].astype(str).str.contains(
                            selected_variant, na=False
                        )
                    ]
                    if srow.empty and selected_case:
                        srow = stereotype_per_df[
                            stereotype_per_df["case_id"] == selected_case
                        ]
                    if not srow.empty:
                        sr = srow.iloc[0]
                        if _coerce_bool(sr.get("stereotype_audit_flag")) or _coerce_bool(
                            sr.get("identity_leakage_flag")
                        ):
                            st.warning(
                                "Stereotype / identity-leakage screening flag on this output — "
                                "review reasoning text in Stereotype tab."
                            )

                left, right = st.columns(2)
                with left:
                    _render_case_card(neutral_row, "Neutral")
                with right:
                    _render_case_card(variant_row, "Counterfactual variant")

                st.markdown("#### Difference summary")
                diff_table = build_difference_comparison_table(
                    neutral_row, variant_row, pairwise_row
                )
                st.dataframe(diff_table, use_container_width=True, hide_index=True)

                with st.expander("Legal expert review questions"):
                    for question in LEGAL_REVIEW_QUESTIONS:
                        st.markdown(f"- {question}")

                st.markdown("#### Local review note (download)")
                with st.form("review_note_form"):
                    reviewer_id = st.text_input("Reviewer ID", "")
                    factual_equivalence = st.selectbox(
                        "Factual equivalence", ["yes", "no", "unclear"]
                    )
                    substantive_difference = st.selectbox(
                        "Substantive difference", ["yes", "no", "unclear"]
                    )
                    legally_justified = st.selectbox(
                        "Legally justified", ["yes", "no", "unclear"]
                    )
                    concern_level = st.selectbox(
                        "Concern level", ["none", "low", "medium", "high"]
                    )
                    possible_bias_type = st.selectbox(
                        "Possible bias type",
                        [
                            "none",
                            "demographic",
                            "language_access",
                            "intersectional",
                            "socioeconomic",
                            "disability_age_vulnerability",
                            "model_instability",
                            "legally_justified_difference",
                            "unclear",
                        ],
                    )
                    reviewer_notes = st.text_area("Reviewer notes", height=120)
                    submitted = st.form_submit_button("Prepare download")
                if submitted:
                    sev = severity_score(pairwise_row) if pairwise_row is not None else None
                    note_row = build_review_note_row(
                        case_id=selected_case,
                        variant_type=selected_variant,
                        reviewer_id=reviewer_id,
                        factual_equivalence=factual_equivalence,
                        substantive_difference=substantive_difference,
                        legally_justified=legally_justified,
                        concern_level=concern_level,
                        possible_bias_type=possible_bias_type,
                        reviewer_notes=reviewer_notes,
                        severity=sev,
                    )
                    fname = f"human_review_note_{selected_case}_{selected_variant}.csv"
                    st.download_button(
                        "Download review note for this case",
                        data=review_note_csv_bytes(note_row),
                        file_name=fname,
                        mime="text/csv",
                        key=f"dl_note_{selected_case}_{selected_variant}",
                    )
                    st.caption(
                        "Combine downloaded notes manually into your human-review spreadsheet."
                    )

    with tabs[4]:
        st.subheader("Counterfactual validity")
        val_suffixes = list_validity_suffixes(artifacts)
        if not val_suffixes:
            st.markdown(
                render_empty_state(
                    "counterfactual_validity",
                    "python -m benchassist.counterfactual_validity "
                    "--base-cases data/processed/base_cases.csv "
                    "--counterfactuals data/audit/counterfactual_cases.csv "
                    f"--output-suffix {exp_token}",
                )
            )
        else:
            default_val = exp_token if exp_token in val_suffixes else val_suffixes[0]
            val_suffix = st.selectbox(
                "Validity audit suffix",
                val_suffixes,
                index=val_suffixes.index(default_val) if default_val in val_suffixes else 0,
                key="validity_suffix_select",
            )
            val_paths = pick_validity_paths(artifacts, val_suffix or val_suffixes[0])
            with st.expander("How to interpret validity categories", expanded=False):
                st.markdown(VALIDITY_AUDIT_HELP)
            validity_df_tab = load_csv_optional(val_paths.get("per_variant"))
            summary_df = load_csv_optional(val_paths.get("summary"))
            if not validity_df_tab.empty:
                st.markdown("#### Validity category counts")
                counts = validity_df_tab["validity_category"].value_counts().reset_index()
                counts.columns = ["validity_category", "count"]
                st.dataframe(counts, use_container_width=True, hide_index=True)
                if "variant_type" in validity_df_tab.columns:
                    pivot = (
                        validity_df_tab.groupby(["variant_type", "validity_category"])
                        .size()
                        .reset_index(name="n")
                    )
                    st.markdown("#### Variant type × validity category")
                    st.dataframe(pivot, use_container_width=True, hide_index=True)
                if "fact_preservation_score" in validity_df_tab.columns:
                    st.metric(
                        "Mean fact preservation score",
                        f"{validity_df_tab['fact_preservation_score'].mean():.2f}",
                    )
                if "direct_bias_analysis_eligible" in validity_df_tab.columns:
                    elig = validity_df_tab["direct_bias_analysis_eligible"].astype(bool).mean()
                    st.metric("Direct bias analysis eligible rate", f"{elig:.1%}")
                show = validity_df_tab[
                    [
                        c
                        for c in [
                            "variant_id",
                            "variant_type",
                            "validity_category",
                            "fact_preservation_score",
                            "direct_bias_analysis_eligible",
                            "exclude_from_strict_bias_rates",
                        ]
                        if c in validity_df_tab.columns
                    ]
                ].sort_values("fact_preservation_score")
                st.dataframe(show.head(40), use_container_width=True, hide_index=True)
            if not summary_df.empty:
                with st.expander("Summary table", expanded=False):
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
            rep = val_paths.get("report")
            if rep and rep.exists():
                st.markdown(f"Full report: `{rep}`")

    with tabs[5]:
        st.subheader("Mitigation comparison")
        mit_path = pick_mitigation_for_run(artifacts, run.label)
        mit_df = load_csv_optional(mit_path)
        if mit_df.empty:
            st.markdown(
                render_empty_state(
                    "mitigation_comparison",
                    "python -m benchassist.mitigation_comparison "
                    "--baseline <group_summary_baseline.csv> "
                    "--fairness-aware <group_summary_fairness.csv> "
                    "--demographic-blind <group_summary_blind.csv>",
                )
            )
        else:
            st.caption(f"Loaded: `{mit_path}`")
            delta_cols = [c for c in mit_df.columns if c.startswith("delta_") and "demographic" not in c]
            if delta_cols:
                summary_rows = []
                for _, row in mit_df.iterrows():
                    for dcol in delta_cols[:5]:
                        summary_rows.append(
                            {
                                "variant_type": row.get("variant_type"),
                                "metric": dcol.replace("delta_", ""),
                                "delta_fairness_vs_baseline": row.get(dcol),
                                "label": mitigation_delta_label(row.get(dcol)),
                            }
                        )
                st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
            with st.expander("Full mitigation table", expanded=False):
                st.dataframe(mit_df, use_container_width=True, hide_index=True)
            st.info(
                "Mitigation can reduce one risk while increasing another. "
                "Do not judge fairness on a single metric — qualitative review is required."
            )

    with tabs[6]:
        st.subheader("Narrative robustness")
        narr_suffixes = list_narrative_robustness_suffixes(artifacts)
        if not narr_suffixes:
            st.markdown(
                render_empty_state(
                    "narrative_robustness",
                    "python -m benchassist.narrative_robustness "
                    "--pairwise <pairwise.csv> --output-suffix <suffix>",
                )
            )
        else:
            default_narr = exp_token if exp_token in narr_suffixes else narr_suffixes[0]
            narr_suffix = st.selectbox(
                "Narrative robustness suffix",
                narr_suffixes,
                index=narr_suffixes.index(default_narr) if default_narr in narr_suffixes else 0,
                key="narr_suffix_select",
            )
            narr_paths = pick_narrative_robustness_paths(
                artifacts, narr_suffix or narr_suffixes[0]
            )
            with st.expander("Interpretation", expanded=False):
                st.markdown(NARRATIVE_ROBUSTNESS_HELP)
            narr_summary = load_csv_optional(narr_paths.get("summary"))
            narr_pairwise = load_csv_optional(narr_paths.get("pairwise"))
            if not narr_summary.empty:
                st.dataframe(narr_summary, use_container_width=True, hide_index=True)
            elif narr_pairwise.empty:
                st.info("Narrative summary empty — run may not include narrative-framing variants.")
            if not narr_pairwise.empty:
                st.dataframe(narr_pairwise.head(25), use_container_width=True, hide_index=True)
            narr_rep = narr_paths.get("report")
            if narr_rep and narr_rep.exists():
                st.markdown(f"Full report: `{narr_rep}`")

    with tabs[7]:
        st.subheader("Stereotype & identity leakage")
        with st.expander("Interpretation", expanded=False):
            st.markdown(STEREOTYPE_AUDIT_HELP)
        if stereotype_group_df.empty and stereotype_flagged_df.empty:
            st.markdown(
                render_empty_state(
                    "stereotype_audit",
                    f"python -m benchassist.stereotype_audit --outputs <outputs.csv> "
                    f"--output-suffix {run.label}",
                )
            )
        else:
            if not stereotype_group_df.empty:
                st.markdown("#### Group summary")
                st.dataframe(stereotype_group_df, use_container_width=True, hide_index=True)
                for metric, title in [
                    ("stereotype_audit_flag_rate", "Stereotype audit flag rate"),
                    ("identity_leakage_flag_rate", "Identity leakage flag rate"),
                    ("stereotype_language_flag_rate", "Stereotype language flag rate"),
                ]:
                    if metric in stereotype_group_df.columns:
                        fig = make_bar_chart(
                            stereotype_group_df, "variant_type", metric, title, top_n=12
                        )
                        if fig is not None:
                            st.plotly_chart(fig, use_container_width=True)
            if not stereotype_flagged_df.empty:
                st.markdown("#### Flagged examples")
                st.dataframe(
                    stereotype_flagged_df.head(30),
                    use_container_width=True,
                    hide_index=True,
                )
            elif not stereotype_per_df.empty:
                flagged_s = stereotype_per_df[
                    stereotype_per_df.get("stereotype_audit_flag", False).astype(bool)
                    | stereotype_per_df.get("identity_leakage_flag", False).astype(bool)
                ]
                st.markdown("#### Flagged outputs (from per-output table)")
                st.dataframe(
                    flagged_s.head(20) if not flagged_s.empty else stereotype_per_df.head(10),
                    use_container_width=True,
                    hide_index=True,
                )
            rep_st = stereotype_paths.get("report")
            if rep_st and rep_st.exists():
                with st.expander("Stereotype audit report (Markdown)", expanded=False):
                    st.markdown(safe_read_markdown(rep_st, max_chars=12000))

    with tabs[8]:
        st.subheader("Legal grounding & hallucination")
        hall_suffixes = list_hallucination_suffixes(artifacts)
        if not hall_suffixes:
            st.markdown(
                render_empty_state(
                    "hallucination_audit",
                    "python -m benchassist.hallucination_audit --input <v3_grounded.csv> "
                    "--output-suffix <suffix>",
                )
            )
        else:
            default_hall = (
                f"{exp_token}_grounded"
                if f"{exp_token}_grounded" in hall_suffixes
                else hall_suffixes[0]
            )
            hall_suffix = st.selectbox(
                "Hallucination audit suffix",
                hall_suffixes,
                index=hall_suffixes.index(default_hall)
                if default_hall in hall_suffixes
                else 0,
                key="hall_suffix_select",
            )
            hall_paths = pick_hallucination_paths(artifacts, hall_suffix or hall_suffixes[0])
            with st.expander("Interpretation", expanded=False):
                st.markdown(GROUNDING_AUDIT_HELP)
            group_hall = load_csv_optional(hall_paths.get("group_summary"))
            per_hall = load_csv_optional(hall_paths.get("per_output"))
            if not group_hall.empty:
                st.dataframe(group_hall, use_container_width=True, hide_index=True)
            if not per_hall.empty:
                risky = per_hall[
                    per_hall.get("high_hallucination_risk", False).astype(bool)
                    | per_hall.get("has_invalid_citation", False).astype(bool)
                ]
                st.markdown("#### High-risk examples")
                st.dataframe(
                    risky.head(20) if not risky.empty else per_hall.head(10),
                    use_container_width=True,
                    hide_index=True,
                )
            report_hall = hall_paths.get("report")
            if report_hall and report_hall.exists():
                st.markdown(f"Full report: `{report_hall}`")

    with tabs[9]:
        st.subheader("Statistical uncertainty")
        stat_suffixes = list_statistical_suffixes(artifacts)
        if not stat_suffixes:
            st.info(
                "No statistical outputs found. Generate them with:\n\n"
                "```bash\n"
                "python -m benchassist.statistical_analysis \\\n"
                "  --pairwise results/tables/v2_pairwise_comparison_<suffix>.csv \\\n"
                "  --output-suffix <suffix>\n"
                "```"
            )
        else:
            stat_suffix = st.selectbox(
                "Statistical run suffix",
                stat_suffixes,
                key="stat_suffix_select",
            )
            stat_paths = pick_statistical_paths(artifacts, stat_suffix or stat_suffixes[0])
            group_effects_df = load_csv_optional(stat_paths.get("group_effects"))
            tests_df = load_csv_optional(stat_paths.get("pairwise_tests"))
            with st.expander("How to interpret confidence intervals", expanded=False):
                st.markdown(STATISTICAL_CI_HELP)
            if group_effects_df.empty:
                st.warning("Group effects CSV is missing or empty for this suffix.")
            else:
                show_cols = [
                    c
                    for c in [
                        "variant_type",
                        "metric",
                        "metric_kind",
                        "n",
                        "rate",
                        "mean",
                        "ci_lower",
                        "ci_upper",
                        "interpretation",
                        "small_sample_warning",
                    ]
                    if c in group_effects_df.columns
                ]
                st.markdown("#### Confidence intervals by variant and metric")
                st.dataframe(
                    group_effects_df[show_cols],
                    use_container_width=True,
                    hide_index=True,
                )
                signals_df = summarize_statistical_signals(group_effects_df)
                if not signals_df.empty:
                    st.markdown("#### Top audit signals (exploratory)")
                    st.dataframe(signals_df, use_container_width=True, hide_index=True)
                if not tests_df.empty:
                    with st.expander("Paired tests (exploratory)", expanded=False):
                        st.dataframe(tests_df.head(80), use_container_width=True, hide_index=True)
                        st.caption(
                            "Exploratory tests; no multiple-comparison correction in this view. "
                            "Small samples require qualitative legal review."
                        )
            chart_effects = stat_paths.get("chart_effects")
            chart_ci = stat_paths.get("chart_ci")
            if chart_effects and chart_effects.exists():
                st.image(str(chart_effects), caption="Mean numeric deltas by variant")
            if chart_ci and chart_ci.exists():
                st.image(str(chart_ci), caption="Legal framing bias flag rate with Wilson 95% CI")
            report_path = stat_paths.get("report")
            if report_path and report_path.exists():
                st.markdown(f"Full report: `{report_path}`")

    with tabs[10]:
        st.subheader("Qualitative review")
        if run.qualitative and run.qualitative.exists():
            if run.qualitative.suffix == ".md":
                with st.expander("Qualitative case studies (Markdown)", expanded=True):
                    st.markdown(safe_read_markdown(run.qualitative, max_chars=25000))
            elif not qualitative_df.empty:
                qdf = (
                    add_severity_columns(qualitative_df)
                    if "variant_type" in qualitative_df.columns
                    else qualitative_df
                )
                show_q = [
                    c
                    for c in (
                        "review_priority",
                        "severity_score",
                        "case_id",
                        "variant_type",
                        "generated_interpretation",
                    )
                    if c in qdf.columns
                ]
                st.dataframe(
                    qdf[show_q] if show_q else qdf.head(30),
                    use_container_width=True,
                    hide_index=True,
                )
                _download_csv_button(
                    qualitative_df, "Download qualitative cases CSV", "qualitative_cases.csv"
                )
        else:
            st.markdown(
                render_empty_state(
                    "qualitative_case_studies",
                    "python -m benchassist.qualitative_cases --outputs <outputs.csv> "
                    "--pairwise <pairwise.csv> --output-suffix <suffix>",
                )
            )

    with tabs[11]:
        st.subheader("Human review")
        if artifacts.human_review_rubric:
            rubric = latest_file(artifacts.human_review_rubric)
            if rubric:
                with st.expander("Review rubric", expanded=False):
                    st.markdown(safe_read_markdown(rubric, max_chars=8000))
        if not template_df.empty:
            st.dataframe(template_df.head(15), use_container_width=True, hide_index=True)
            _download_csv_button(
                template_df, "Download human review template", "human_review_template.csv"
            )
        else:
            st.markdown(
                render_empty_state(
                    "human_review_template",
                    "python -m benchassist.human_review generate-template "
                    "--qualitative-cases <qualitative.csv> --output <template.csv>",
                )
            )
        st.markdown("#### Reviewer questions")
        for question in LEGAL_REVIEW_QUESTIONS:
            st.markdown(f"- {question}")
        summary_md = latest_file(artifacts.human_review_summary_md)
        if summary_md:
            st.markdown(safe_read_markdown(summary_md, max_chars=8000))

    with tabs[12]:
        st.subheader("Reports & exports")
        st.markdown("Download filtered tables, Markdown reports, and submission artefacts.")
        col1, col2 = st.columns(2)
        with col1:
            _download_csv_button(
                review_source, "Review queue (filtered)", "export_review_queue.csv", "exp_rev"
            )
            _download_csv_button(
                filtered_group, "Group summary (filtered)", "export_group.csv", "exp_group"
            )
            if not qualitative_df.empty:
                _download_csv_button(
                    qualitative_df, "Qualitative cases", "export_qualitative.csv", "exp_qual"
                )
            if not template_df.empty:
                _download_csv_button(
                    template_df, "Human review template", "export_hr_template.csv", "exp_hrt"
                )
        with col2:
            final_path = latest_file(artifacts.final_report)
            if final_path:
                _download_text_button(
                    safe_read_markdown(final_path, max_chars=500_000),
                    "Final audit report (Markdown)",
                    final_path.name,
                    "exp_final_report",
                )
            zip_path = latest_file(artifacts.submission_package_zip)
            if zip_path:
                st.download_button(
                    "Download submission package (.zip)",
                    data=zip_path.read_bytes(),
                    file_name=zip_path.name,
                    mime="application/zip",
                    key="dl_submission_zip",
                )
        st.markdown("#### Report previews")
        report_specs = [
            ("Final audit report", latest_file(artifacts.final_report)),
            ("Gemini pilot run report", latest_file(artifacts.gemini_pilot_report)),
            ("Gemini full run report", latest_file(artifacts.gemini_full_report)),
        ]
        for title, path in report_specs:
            if path and path.exists():
                with st.expander(title, expanded=False):
                    st.markdown(safe_read_markdown(path, max_chars=8000))
        for doc in artifacts.project_docs:
            if doc.exists():
                with st.expander(doc.name, expanded=False):
                    st.markdown(safe_read_markdown(doc, max_chars=6000))
        with st.expander("Optional: stability & multi-model comparison", expanded=False):
            stab_df = load_csv_optional(latest_file(artifacts.stability_summaries))
            model_df = load_csv_optional(latest_file(artifacts.model_comparison))
            if not stab_df.empty:
                st.dataframe(stab_df, use_container_width=True, hide_index=True)
            if not model_df.empty:
                st.dataframe(model_df, use_container_width=True, hide_index=True)
        st.markdown("#### Submission checklist")
        for name, path_hint in SUBMISSION_CHECKLIST:
            st.markdown(f"- [ ] **{name}** — `{path_hint}`")

    with tabs[13]:
        st.subheader("Methodology and limitations")
        for title, body in METHODOLOGY_CARDS:
            with st.container():
                st.markdown(f"#### {title}")
                st.markdown(body)
                st.divider()
        with st.expander("Full metric glossary"):
            for key, parts in METRIC_GLOSSARY.items():
                st.markdown(f"**`{key}`**")
                st.markdown(f"- Measures: {parts['measure']}")
                st.markdown(f"- Legally: {parts['legal']}")
                st.markdown(f"- Caution: {parts['caution']}")
        if artifacts.charts:
            st.markdown("#### Available charts")
            for chart in artifacts.charts[:25]:
                st.markdown(f"- `{chart.name}`")


if __name__ == "__main__":
    main()
