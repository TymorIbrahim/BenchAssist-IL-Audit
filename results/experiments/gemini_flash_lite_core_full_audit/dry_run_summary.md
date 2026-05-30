# Experiment dry-run summary

**Experiment:** `gemini_flash_lite_core_full_audit`
**Provider:** `gemini`
**Model:** `gemini-2.5-flash-lite`
**Schema (V2):** `v2`
**Prompt modes:** baseline, fairness_aware, demographic_blind
**Variant set:** `core`
**Base cases:** 12
**Counterfactual cases (after limit):** 144
**Repetitions:** 1
**Limit:** none

## Model calls

- V2 calls (all modes): **432**
- V3 grounded calls: **144**

## Cost estimate (approximate)

- Input tokens: **835,200**
- Output tokens: **309,600**
- Estimated total: **$0.2074 USD**
- *Approximate token counts; actual billing may differ.*

## Output files (sample)

### Mode `baseline`
- Model: `gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv`
- Pairwise: `v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv`

### Mode `fairness_aware`
- Model: `gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv`
- Pairwise: `v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv`

### Mode `demographic_blind`
- Model: `gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv`
- Pairwise: `v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv`

### Grounded
- Model: `gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v3_grounded.csv`

## Planned commands

1. **data_generation** — Generate counterfactual cases
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.data_generation --variant-set core
   ```

2. **ensure_base_cases** — Ensure base_cases.csv exists under data/processed
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -c from benchassist.data_generation import ensure_base_case_files; ensure_base_case_files()
   ```

3. **counterfactual_validity** — Counterfactual validity audit
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.counterfactual_validity --base-cases /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/data/processed/base_cases.csv --counterfactuals /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/data/audit/counterfactual_cases.csv --output-suffix gemini_flash_lite_core_full_audit
   ```

4. **run_batch_baseline** — V2 model batch (baseline)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v2 --prompt-mode baseline --output-prefix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline --repetitions 1 --temperature 0.0
   ```

5. **audit_metrics_baseline** — V2 audit metrics (baseline)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.audit_metrics --version v2 --input /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline --validity /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/counterfactual_validity_gemini_flash_lite_core_full_audit.csv
   ```

6. **stereotype_audit_baseline** — Stereotype audit (baseline)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.stereotype_audit --outputs /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline
   ```

7. **statistical_analysis_baseline** — Statistical analysis (baseline)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.statistical_analysis --pairwise /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline --bootstrap-samples 2000 --seed 42
   ```

8. **qualitative_cases_baseline** — Qualitative cases (baseline)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.qualitative_cases --outputs /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --pairwise /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --flagged /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_flagged_cases_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --top-n 10 --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline
   ```

9. **run_batch_fairness_aware** — V2 model batch (fairness_aware)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v2 --prompt-mode fairness_aware --output-prefix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware --repetitions 1 --temperature 0.0
   ```

10. **audit_metrics_fairness_aware** — V2 audit metrics (fairness_aware)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.audit_metrics --version v2 --input /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware --validity /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/counterfactual_validity_gemini_flash_lite_core_full_audit.csv
   ```

11. **stereotype_audit_fairness_aware** — Stereotype audit (fairness_aware)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.stereotype_audit --outputs /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware
   ```

12. **statistical_analysis_fairness_aware** — Statistical analysis (fairness_aware)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.statistical_analysis --pairwise /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware --bootstrap-samples 2000 --seed 42
   ```

13. **qualitative_cases_fairness_aware** — Qualitative cases (fairness_aware)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.qualitative_cases --outputs /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv --pairwise /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv --flagged /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_flagged_cases_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv --top-n 10 --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware
   ```

14. **run_batch_demographic_blind** — V2 model batch (demographic_blind)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v2 --prompt-mode demographic_blind --output-prefix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind --repetitions 1 --temperature 0.0
   ```

15. **audit_metrics_demographic_blind** — V2 audit metrics (demographic_blind)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.audit_metrics --version v2 --input /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind --validity /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/counterfactual_validity_gemini_flash_lite_core_full_audit.csv
   ```

16. **stereotype_audit_demographic_blind** — Stereotype audit (demographic_blind)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.stereotype_audit --outputs /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind
   ```

17. **statistical_analysis_demographic_blind** — Statistical analysis (demographic_blind)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.statistical_analysis --pairwise /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind --bootstrap-samples 2000 --seed 42
   ```

18. **qualitative_cases_demographic_blind** — Qualitative cases (demographic_blind)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.qualitative_cases --outputs /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv --pairwise /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv --flagged /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_flagged_cases_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv --top-n 10 --output-suffix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind
   ```

19. **mitigation_comparison** — Mitigation comparison across prompt modes
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.mitigation_comparison --baseline /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_group_summary_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --fairness-aware /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_group_summary_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv --demographic-blind /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_group_summary_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_demographic_blind.csv --output /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/mitigation_comparison_gemini_flash_lite_core_full_audit.csv
   ```

20. **narrative_robustness** — Narrative-framing robustness (baseline pairwise)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.narrative_robustness --pairwise /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --validity /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/counterfactual_validity_gemini_flash_lite_core_full_audit.csv --output-suffix gemini_flash_lite_core_full_audit
   ```

21. **run_batch_grounded** — V3 grounded model batch
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v3 --prompt-mode grounded --top-k-sources 5 --output-prefix gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v3_grounded --repetitions 1
   ```

22. **hallucination_audit** — Hallucination / grounding audit
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.hallucination_audit --input /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/outputs/gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v3_grounded.csv --output-suffix gemini_flash_lite_core_full_audit_grounded
   ```

23. **human_review_template** — Human review template
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.human_review generate-template --qualitative-cases /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/qualitative_case_studies_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_baseline.csv --validity /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/counterfactual_validity_gemini_flash_lite_core_full_audit.csv --output /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/human_review_template_gemini_flash_lite_core_full_audit.csv
   ```

24. **final_report** — Final audit report (auto-discovery)
   ```bash
   /Users/tymoribrahim/miniconda3/bin/python -m benchassist.final_report --auto
   ```


**No commands were executed.** Use `--execute` to run (requires API key for Gemini).