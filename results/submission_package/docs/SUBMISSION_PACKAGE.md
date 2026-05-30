# Submission Package

What to submit or demonstrate for the BenchAssist-IL Audit course project.

---

## Recommended submission files

### Documentation (repository root)

- `README.md` — setup, demo commands, ethics
- `PROJECT_OVERVIEW.md` — TA/legal-friendly summary
- `CITATIONS.md` — references
- `DATA_DICTIONARY.md` — file and column reference
- `LEGAL_EXPERT_RUNBOOK.md` — human review guide
- `TESTING_REPORT.md` — QA evidence
- `SUBMISSION_CHECKLIST.md` — checklist
- `SUBMISSION_PACKAGE.md` — this file

- `REAL_CASE_DATA_CARD.md` — real-case layer purpose, limits, attribution
- `VERCEL_DEPLOYMENT_CHECKLIST.md` — dashboard deploy QA

### Reports (`results/report/`)

- `final_audit_report.md` — **primary deliverable** (includes hybrid methodology section)
- `real_case_layer_qa_report.md` — real-case offline QA summary
- `real_case_ingestion_report.md` — ingestion status (local + optional HF)
- `real_case_audit_*.md` — domain-level real-case audit (when run)
- `gemini_real_case_pilot_report.md` — optional small pilot (if run)
- `qualitative_case_studies_*.md` — example cases
- `human_review_rubric.md`
- `counterfactual_validity_*.md` (if generated)
- `stereotype_audit_*.md`, `hallucination_audit_*.md`, `statistical_analysis_*.md`, `narrative_robustness_*.md` (as available)

### Tables (`results/tables/`)

- `v2_group_summary_*.csv`
- `v2_flagged_cases_*.csv`
- `v2_pairwise_comparison_*.csv` (optional, larger)
- `human_review_template*.csv`
- `counterfactual_validity_*.csv`
- `mitigation_comparison*.csv` (if mitigation runs were done)

### Optional

- **Vercel dashboard** — `web_dashboard/` with Real Israeli Case-Inspired Audit section (export via `vercel_export --auto`)
- Screenshots of the Streamlit or Vercel dashboard
- Selected charts from `results/charts/`
- Pre-built zip: `results/submission_package.zip` (see below)

---

## Build the submission package automatically

```bash
python -m benchassist.final_report --auto
python -m benchassist.submission_package --auto
```

Outputs:

- `results/submission_package/` — curated copy for reviewers
- `results/submission_package.zip` — zip archive for upload
- `results/submission_package/README_FOR_REVIEWERS.md` — start here
- `results/submission_package/MANIFEST.json` — file list and missing optional artefacts

---

## Do **not** submit

- `.env` or any file containing **API keys**
- Virtual environments (`.venv/`, `venv/`)
- `__pycache__/`, `.pytest_cache/`, `.git/` (unless the course requires the full repo)
- Huge raw caches or duplicate experimental outputs you do not discuss
- Private or real party data (this project uses synthetic cases only)

---

## Out of scope (not part of this submission)

- Party-role / power-asymmetry audit
- Standalone interactive HTML report
