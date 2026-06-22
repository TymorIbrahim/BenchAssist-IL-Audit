# Gemini Detention Pilot — QA Report

Generated: 2026-06-22T21:43:34.494462+00:00

**Pilot results are preliminary and are not final research findings.**

## Config summary

- Model: see run_manifest.json
- Config: `configs/gemini_detention_pilot.yaml`
- Prompt modes: see manifest

## Row counts

- Total outputs: 6
- Parse success rate: 100.0%
- Strict-eligible synthetic: 3
- Real-case qualitative: 3

## Schema validation

- Status: **PASSED**
- Valid rows: 6/6
- Hard schema errors: 0
- Canonicalization warnings: 0
- Parse errors: 0
- Metadata errors: 0

## Strict fairness confirmation

- Real-case rows excluded from strict fairness rates: **Yes**
- Strict fairness source: synthetic counterfactual only

- Flagged comparisons (pilot): 1
- Real-case review outputs: 3

## Dashboard export

Run after analysis:

```bash
python -m benchassist.vercel_export --auto --use-case detention \
  --run-dir results/gemini/detention_pilot --data-status gemini_pilot
```

## Limitations

- Pilot sample is small — do not generalize to full corpus.
- Audit signals require human legal review.
- Not proof of unlawful discrimination.

## Decision recommendation

- **ready_for_full_run_planning:** yes
- **ready_for_full_run_execution:** no (planning sprint only until full dry-run QA passes)

### Blockers

- None identified from pilot QA checks (legal review still required).

### Recommended fixes before full run

- Legal expert review of flagged pilot cases (see flagged review packet)
- Confirm cost estimate for full run via dry-run on gemini_detention_full.yaml

**Pilot results are preliminary and not final research findings.**