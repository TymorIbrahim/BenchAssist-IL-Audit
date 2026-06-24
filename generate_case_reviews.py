"""Generate individual case review JSON files for the Case Explorer page.

Reads pairwise comparisons and LLM outputs, creates one review JSON per comparison,
and updates the case review index with file paths.
"""
import json
import sys
from pathlib import Path


def find_latest_outputs():
    """Find the latest LLM outputs file."""
    candidates = [
        "rachel_data/llm_outputs.json",
        "rachel_data/llm_outputs_v4.json",
        "rachel_data/llm_outputs_v3.json",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    print("ERROR: No LLM outputs file found", file=sys.stderr)
    sys.exit(1)


def main():
    outputs_path = find_latest_outputs()
    print(f"Using outputs: {outputs_path}")

    data = json.loads(open(outputs_path).read())
    all_results = data["results"]

    comparisons_path = Path("web_dashboard/public/data/detention_pairwise_comparison.json")
    if not comparisons_path.exists():
        print("ERROR: No pairwise comparisons found. Run analysis first.", file=sys.stderr)
        sys.exit(1)

    comparisons = json.loads(comparisons_path.read_text())
    print(f"Loaded {len(comparisons)} pairwise comparisons")

    out_dir = Path("web_dashboard/public/data/case_reviews")
    out_dir.mkdir(exist_ok=True, parents=True)

    # Index results by record_id
    res_by_id = {r["record_id"]: r for r in all_results}

    generated = 0
    skipped = 0

    for c in comparisons:
        ctrl_id = c.get("control_record_id", "")
        var_id_val = c.get("variant_record_id", "")

        # Skip if we can't find the records
        if ctrl_id not in res_by_id or var_id_val not in res_by_id:
            skipped += 1
            continue

        review_id = f"{c['case_id']}_{c['variant_type']}_{c['prompt_mode']}"
        ctrl = res_by_id[ctrl_id]
        var = res_by_id[var_id_val]

        ctrl_out = ctrl.get("llm_output") or {}
        var_out = var.get("llm_output") or {}

        # Extract explanation text
        ctrl_explanation = ctrl_out.get("Explanation", "") or ctrl_out.get("Rationale", "") or ""
        var_explanation = var_out.get("Explanation", "") or var_out.get("Rationale", "") or ""

        # Extract dangerousness
        ctrl_danger = ctrl_out.get("Dangerousness_Level") or c.get("control_risk", "")
        var_danger = var_out.get("Dangerousness_Level") or c.get("variant_risk", "")

        # Extract detention days
        ctrl_detention = ctrl_out.get("Recommended_Detention_Days")
        var_detention = var_out.get("Recommended_Detention_Days")

        # Extract recommendation
        ctrl_rec = ctrl_out.get("Recommendation", "")
        var_rec = var_out.get("Recommendation", "")

        # Build flag reasons
        flag_reasons = []
        if c.get("dangerousness_escalation_flag"):
            flag_reasons.append("Dangerousness escalation")
        if c.get("dangerousness_deescalation_flag"):
            flag_reasons.append("Dangerousness de-escalation")
        if c.get("detention_days_changed_flag"):
            flag_reasons.append(f"Detention days changed ({c.get('detention_days_delta', 0):+.0f})")
        if c.get("recommendation_changed_flag"):
            flag_reasons.append(f"Recommendation changed ({c.get('control_recommendation', '')} → {c.get('variant_recommendation', '')})")
        if c.get("identity_leakage_flag"):
            flag_reasons.append("Identity leakage detected")

        is_flagged = c.get("detention_framing_bias_flag", False)

        record = {
            "review_record_id": review_id,
            "base_case_id": c["case_id"],
            "base_case_title": f"Case {c['case_id']}",
            "variant_id": c.get("variant_id", var_id_val),
            "variant_type": c["variant_type"],
            "prompt_mode": c["prompt_mode"],
            "is_flagged": is_flagged,
            "review_priority": "high" if c.get("dangerousness_escalation_flag") else ("medium" if c.get("risk_changed") else "low"),
            "flag_reasons": flag_reasons,
            "base_case": {
                "full_case_text": ctrl.get("case_input_text", ""),
                "prompt_input": ctrl.get("case_input_text", ""),
            },
            "variant_case": {
                "full_case_text": var.get("case_input_text", ""),
                "prompt_input": var.get("case_input_text", ""),
                "variant_label": c["variant_type"],
            },
            "neutral_output": {
                "dangerousness_level": ctrl_danger,
                "recommended_detention_days": ctrl_detention,
                "case_summary": ctrl_rec,
                "reasoning_text": ctrl_explanation,
            },
            "variant_output": {
                "dangerousness_level": var_danger,
                "recommended_detention_days": var_detention,
                "case_summary": var_rec,
                "reasoning_text": var_explanation,
            },
            "diff": {
                "dangerousness_shift": "escalation" if c.get("dangerousness_escalation_flag") else ("deescalation" if c.get("dangerousness_deescalation_flag") else "unchanged"),
                "diff_summary": "; ".join(flag_reasons) if flag_reasons else "No material difference",
                "semantic_divergence_score": c.get("semantic_divergence_score"),
                "detention_days_delta": c.get("detention_days_delta", 0),
            },
            "review_guidance": {
                "why_flagged": "; ".join(flag_reasons) if is_flagged else "",
            },
        }

        out_path = out_dir / f"{review_id}.json"
        out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        generated += 1

    # Update the case review index
    index_path = Path("web_dashboard/public/data/detention_case_review_index.json")
    if index_path.exists():
        index = json.loads(index_path.read_text())
        if "records_index" in index:
            for rec in index["records_index"]:
                rec["record_path"] = f"case_reviews/{rec['review_record_id']}.json"
            index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False))

    print(f"Generated {generated} case review files, skipped {skipped}")


if __name__ == "__main__":
    main()
