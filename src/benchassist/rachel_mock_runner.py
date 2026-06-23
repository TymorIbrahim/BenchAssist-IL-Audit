"""Generate mock LLM outputs for UI testing."""

import json
from pathlib import Path
from benchassist.rachel_llm_runner import load_cases, _DEFAULT_EXCEL, _DEFAULT_OUTPUT

def run_mock():
    cases = load_cases(_DEFAULT_EXCEL)
    results = []
    for c in cases:
        # Mock structured output
        # If expected is High, sometimes make it Medium to trigger changes
        risk = c["expected_lawful_risk"]
        
        # Introduce some variations for name proxy to show bias
        if c["counterfactual_condition"] == "Name_Proxy" and c["prompt_mode"] == "Baseline":
            if risk == "Low": risk = "Medium"
            elif risk == "Medium": risk = "High"
            
        rec = "Release" if risk == "Low" else "Extend detention"
        
        leakage = "No"
        if c["counterfactual_condition"] == "Name_Proxy" and c["prompt_mode"] == "Baseline":
            leakage = "Yes"
            rationale = f"Given the suspect's name {c['suspect_name']}, there is risk."
        else:
            rationale = f"Based on the facts, the risk is {risk}."
            
        llm_out = {
            "Risk_Level": risk.capitalize(),
            "Recommendation": rec,
            "Legal_Grounds": "Mock grounds",
            "Confidence_1_5": 4,
            "Rationale": rationale,
            "Any_Proxy_Reliance": leakage,
            "parse_error": False,
        }
        
        results.append({
            **c,
            "llm_output": llm_out,
            "error": None
        })
        
    payload = {
        "generated_at": "2026-06-23T12:00:00Z",
        "model": "mock-gemini",
        "n_results": len(results),
        "n_success": len(results),
        "n_errors": 0,
        "results": results,
    }
    _DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _DEFAULT_OUTPUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(results)} mock outputs to {_DEFAULT_OUTPUT}")

if __name__ == "__main__":
    run_mock()
