# Submission Checklist

Use this list when packaging the BenchAssist-IL Audit for course submission or TA review.

## Repository

- [ ] Repository clones cleanly (`git clone` + `cd BenchAssist-IL-Audit`)
- [ ] `pip install -e ".[dev]"` succeeds on Python ≥ 3.11
- [ ] `pytest -q` passes locally
- [ ] `.env` is **not** committed (only `.env.example` if provided)
- [ ] No API keys in source or notebooks

## Core deliverables

- [ ] `README.md` — concept, quickstart, demo, limitations, API safety
- [ ] `TESTING_REPORT.md` — QA evidence (mock integration)
- [ ] `CITATIONS.md` — referenced literature and datasets
- [ ] `data/processed/base_cases.csv` — regenerable via `data_generation`
- [ ] `data/audit/counterfactual_cases.csv` — regenerable with `--variant-set all`
- [ ] `results/report/final_audit_report.md` — regenerable via `final_report --auto` or `pipeline --demo`

## Reproducible demo (no API cost)

```bash
python -m benchassist.pipeline --demo --limit 10 --output-suffix submission_demo
pytest -q
```

## Optional live model run (costs money)

```bash
python -m benchassist.pipeline --print-real-run-plan
# Copy commands; set GEMINI_API_KEY in .env; run manually
```

## Dashboard (optional UI)

```bash
pip install -e '.[dev,dashboard]'
streamlit run app.py
```

## Human review (if required by assignment)

- [ ] `results/tables/human_review_template_*.csv`
- [ ] `results/report/human_review_rubric.md`
- [ ] Completed review CSV (if reviewers filled scores)

## Ethics & disclaimers

- [ ] Report states system is **non-binding** and not legal advice
- [ ] Report avoids claiming proven discrimination from metrics alone
- [ ] Synthetic cases only — no real party data

## Files TA may ask for

| Artefact | Typical path |
|----------|----------------|
| V2 group summary | `results/tables/v2_group_summary_*_baseline.csv` |
| Pairwise comparison | `results/tables/v2_pairwise_comparison_*.csv` |
| Validity audit | `results/tables/counterfactual_validity_*.csv` |
| Final report | `results/report/final_audit_report.md` |
| Qualitative cases | `results/tables/qualitative_case_studies_*.csv` |
