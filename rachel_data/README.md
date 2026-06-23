# Running the Rachel Audit Pipeline

This README explains how to run the pipeline to process the 60-case Excel dataset, call the Gemini LLM, compute all audit metrics, and view the results in the Next.js dashboard.

## 1. Prerequisites

You need a valid Gemini API key. Set it in your environment:

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your-api-key"
```

**Mac/Linux:**
```bash
export GEMINI_API_KEY="your-api-key"
```

Alternatively, you can add it to a `.env` file in the root of the project:
```
GEMINI_API_KEY=your-api-key
```

## 2. Generate LLM Outputs (Runner)

Run the LLM runner script to generate risk assessments for all 60 cases using Gemini:

```bash
python -m benchassist.rachel_llm_runner
```

This script will:
- Read `rachel_data/benchassist_synthetic_detention_audit_dataset_final.xlsx`
- Call the Gemini API for each case (respecting the Baseline and Masked prompts)
- Save the raw JSON outputs to `rachel_data/llm_outputs.json`

*(Note: If the script is interrupted, running it again will resume from where it left off.)*

## 3. Generate Dashboard JSONs (Analysis)

Once the LLM outputs are generated, run the analysis pipeline to compute all metrics (CCR, DIR, etc.) and generate the JSON files required by the dashboard:

```bash
python -m benchassist.rachel_analysis
```

This script will:
- Read the outputs from `rachel_data/llm_outputs.json`
- Compute the 40 pairwise comparisons and evaluate them for Bias Flags (Risk Level changes, Identity Leakage, Hallucinations, Semantic Divergence)
- Output all the processed JSON files into `web_dashboard/public/data/`

## 4. Run the Dashboard

Navigate to the dashboard directory and start the local development server:

```bash
cd web_dashboard
npm run dev
```

Open `http://localhost:3000` in your browser. The dashboard is now fully wired up to exclusively show the 60 cases from your experiment, with accurate calculations for Counterfactual Consistency Rate (CCR), Disparate Impact Ratio (DIR), and Reasoning Flaws.
