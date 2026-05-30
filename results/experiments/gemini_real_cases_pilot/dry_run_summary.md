# Experiment dry-run summary

**Experiment:** `gemini_real_cases_pilot`
**Provider:** `gemini`
**Model:** `gemini-2.5-flash-lite`
**Schema (V2):** `v2`
**Prompt modes:** baseline
**Variant set:** `all`
**Base cases:** 12
**Counterfactual cases (after limit):** 20
**Repetitions:** 1
**Limit:** 20

## Model calls

- V2 calls (all modes): **20**
- V3 grounded: disabled

## Cost estimate (approximate)

- Input tokens: **24,000**
- Output tokens: **10,000**
- Estimated total: **$0.0064 USD**
- *Pilot only — requires GEMINI_API_KEY. Not for CI.*

## Output files (sample)

### Mode `baseline`
- Model: `gemini_real_cases_pilot.csv`
- Pairwise: `v2_pairwise_comparison_gemini_real_cases_pilot.csv`

## Planned commands

1. **data_generation** — Generate counterfactual cases
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.data_generation --variant-set all
   ```

2. **ensure_base_cases** — Ensure base_cases.csv exists under data/processed
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -c from benchassist.data_generation import ensure_base_case_files; ensure_base_case_files()
   ```

3. **run_batch_baseline** — V2 model batch (baseline)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v2 --prompt-mode baseline --output-prefix gemini_real_cases_pilot --repetitions 1 --temperature 0.0 --limit 20 --input-cases data/real_cases/real_case_bench_inputs.csv
   ```


**No commands were executed.** Use `--execute` to run (requires API key for Gemini).