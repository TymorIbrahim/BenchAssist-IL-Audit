import json
from pathlib import Path

def main():
    data = json.loads(open("rachel_data/llm_outputs.json").read())
    all_results = data["results"]
    comparisons = json.loads(open("web_dashboard/public/data/detention_pairwise_comparison.json").read())

    out_dir = Path("web_dashboard/public/data/case_reviews")
    out_dir.mkdir(exist_ok=True, parents=True)

    res_by_id = {r["record_id"]: r for r in all_results}

    for c in comparisons:
        review_id = f"{c['case_id']}_{c['variant_id']}_{c['prompt_mode']}"
        ctrl = res_by_id[c["control_record_id"]]
        var = res_by_id[c["variant_record_id"]]
        
        ctrl_out = ctrl.get("llm_output") or {}
        var_out = var.get("llm_output") or {}
        
        record = {
            "review_record_id": review_id,
            "base_case_id": c["case_id"],
            "base_case_title": f"Case {c['case_id']}",
            "variant_id": c["variant_id"],
            "variant_type": c["variant_type"],
            "prompt_mode": c["prompt_mode"],
            "is_flagged": c["detention_framing_bias_flag"],
            "review_priority": "high" if c.get("dangerousness_escalation_flag") else ("medium" if c.get("risk_changed") else "low"),
            "base_case": {
                "full_case_text": ctrl.get("case_input_text", ""),
                "prompt_input": ctrl.get("case_input_text", "")
            },
            "variant_case": {
                "full_case_text": var.get("case_input_text", ""),
                "prompt_input": var.get("case_input_text", ""),
                "variant_label": c["variant_type"]
            },
            "neutral_output": {
                "dangerousness_level": c.get("control_risk", ""),
                "case_summary": ctrl_out.get("Recommendation", ""),
                "reasoning_text": ctrl_out.get("Rationale", "") or ctrl_out.get("raw_response", "")
            },
            "variant_output": {
                "dangerousness_level": c.get("variant_risk", ""),
                "case_summary": var_out.get("Recommendation", ""),
                "reasoning_text": var_out.get("Rationale", "") or var_out.get("raw_response", "")
            },
            "diff": {
                "dangerousness_shift": "escalation" if c.get("dangerousness_escalation_flag") else ("deescalation" if c.get("dangerousness_deescalation_flag") else "unchanged"),
                "diff_summary": "Leaked identity" if c.get("identity_leakage_flag") else ("Hallucinated reasoning" if c.get("unsupported_dangerousness_inference_flag") else ""),
                "semantic_divergence_score": c.get("semantic_divergence_score")
            },
            "review_guidance": {
                "why_flagged": "Flagged for bias" if c.get("detention_framing_bias_flag") else ""
            }
        }
        
        out_path = out_dir / f"{review_id}.json"
        out_path.write_text(json.dumps(record, indent=2))

    index_path = Path("web_dashboard/public/data/detention_case_review_index.json")
    index = json.loads(index_path.read_text())
    for rec in index["records_index"]:
        rec["record_path"] = f"case_reviews/{rec['review_record_id']}.json"
    index_path.write_text(json.dumps(index, indent=2))
    print("Generated case_reviews and updated index!")

if __name__ == "__main__":
    main()
