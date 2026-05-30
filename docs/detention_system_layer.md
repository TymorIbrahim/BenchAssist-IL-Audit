# Detention / Remand System Layer

Pivot from housing to Israeli detention-extension / remand-risk decision support (toy, non-binding, audit-only).

## Use-case selection

```bash
# Housing (default — unchanged)
python -m benchassist.vercel_export --auto

# Detention/remand
python -m benchassist.vercel_export --auto --use-case detention
```

## Generate synthetic counterfactual dataset

```bash
python -m benchassist.detention_data_generation --variant-set core
```

Output: `data/audit/detention/detention_counterfactual_cases.{csv,jsonl}`

## Schema & prompts

- Schema: `src/benchassist/detention_schema.py`
- Prompts: `src/benchassist/detention_prompting.py` (modes: baseline, fairness_aware, demographic_blind, grounded)

## Real-case pilot (expert-approved)

Approved pilot corpus: `data/real_cases/detention/pilot_corpus/`

Real-case rows are **excluded** from strict synthetic fairness rates.

## Strict fairness filtering

Strict metrics include only rows where:
- `dataset_mode = synthetic_counterfactual`
- `use_for_strict_bias_rates = true`
- `exclude_from_strict_bias_rates != true`
- `counterfactual_strength = strict`

Narrative/proxy variants (skeptical_police_framing, defense_framing, low_income_neighborhood_proxy, intersectional) are excluded.

## Next steps (no Gemini yet)

```bash
python -m pytest
python -m benchassist.detention_data_generation --variant-set core
python -m benchassist.vercel_export --auto --use-case detention
# Mock/local batch with --input-cases data/audit/detention/detention_counterfactual_cases.csv
```
