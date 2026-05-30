# Testing Report

**Project:** BenchAssist-IL Audit  
**Date:** 2026-05-29  
**QA suffix:** `qa_mock` / `qa_pipeline` (mock-only; no external APIs)  
**Final status:** **PASS**

---

## Real-case layer QA (2026-05-30)

| Check | Result |
|-------|--------|
| Local fixture ingestion | **PASS** (16 rows, 6 domains) |
| Hugging Face sample ingestion | **PASS** (60 rows, optional) |
| Transform + mock audit | **PASS** (0 parse errors) |
| Strict bias exclusion | **PASS** |
| Vercel real-case JSON export | **PASS** |
| Dashboard build | **PASS** |
| Gemini pilot (10 rows) | **RUN** — see `results/report/gemini_real_case_pilot_report.md` |
| Full pytest | **383 passed** (see section 1) |

Reports: `results/report/real_case_ingestion_report.md`, `results/report/real_case_layer_qa_report.md`

**Note:** `writeup_generator.py` is not in the repo; `final_report --auto` is used instead.

--- party-role/power-asymmetry audit and standalone interactive HTML report. The validator may still reject accidental `party_power` variant types; that guard is not an implemented audit module.

---

## 1. Environment

| Item | Value |
|------|--------|
| OS | macOS (darwin) |
| Python | 3.12 (miniconda) |
| Install | `pip install -e ".[dev]"` |
| Import check | `import benchassist` — OK |
| Unit tests | `pytest -q` — **383 passed** |
| External APIs | **Not called** (mock provider only) |
| API keys in repo | **None found** (`.env` in `.gitignore`) |

---

## 2. Project structure summary

### Source modules (`src/benchassist/`)

| Module | Role |
|--------|------|
| `data_generation.py` | Base cases + counterfactual variants (demographic, language, intersectional, narrative) |
| `validate_data.py` | Offline validation of audit CSVs |
| `prompt_builder.py` | V1/V2/V3 prompts (baseline, fairness-aware, blind, grounded) |
| `blinding.py` | Demographic-blind text transforms |
| `schemas.py` | Pydantic output schemas |
| `model_client.py` | Mock / Gemini / OpenAI clients |
| `run_batch.py` | Batch inference CLI |
| `audit_metrics.py` / `audit_metrics_v2.py` | V1/V2 counterfactual metrics |
| `counterfactual_validity.py` | Fact-preservation / validity categories |
| `narrative_robustness.py` | Narrative-framing robustness audit |
| `stereotype_audit.py` | Identity-leakage / stereotype language screening |
| `hallucination_audit.py` | V3 grounding / citation audit |
| `statistical_analysis.py` | Bootstrap / Wilson uncertainty |
| `qualitative_cases.py` | Flagged case extraction for human review |
| `human_review.py` | Review template + rubric + summarization |
| `mitigation_comparison.py` | Baseline vs mitigation deltas |
| `stability_metrics.py` | Repeated-run stability |
| `model_comparison.py` | Multi-model comparison tables |
| `grounding_comparison.py` | Baseline vs grounded comparison |
| `final_report.py` | Final Markdown audit report |
| `pipeline.py` | `--status`, `--demo`, `--print-real-run-plan` |
| `dashboard_utils.py` | Streamlit artefact discovery |
| `verify_pipeline.py` | Legacy end-to-end verifier (V1 path) |
| `report.py` | V1 audit report generator |
| `israeli_data.py` | Optional HF data explorer |
| `legal_sources.py` | Toy knowledge base for V3 grounded mode |
| `*_texts.py` | Language-access / intersectional / narrative text transforms |

### Prompt & schema files (`prompts/`)

- `system_prompt.txt`, `bench_memo_schema.json` (V1)
- `system_prompt_v2*.txt`, `bench_memo_schema_v2.json` (V2 + fairness / blind)
- `system_prompt_v3_grounded.txt`, `bench_memo_schema_v3.json` (V3 grounded)

### Data paths

| Path | Purpose |
|------|---------|
| `data/processed/base_cases.csv` | Base housing cases |
| `data/audit/counterfactual_cases.csv` | All variants |
| `data/audit/*_variants.csv` | Per-family exports |
| `data/knowledge/israeli_housing_knowledge.jsonl` | V3 toy legal sources |

### Result paths

| Path | Purpose |
|------|---------|
| `results/outputs/` | Model batch CSV/JSONL |
| `results/tables/` | Metrics, validity, stereotype, stats, qualitative |
| `results/charts/` | V2 / stability / statistical charts |
| `results/report/` | Markdown reports |

### Tests (`tests/`)

25 test modules, **287 tests** (includes `test_qa_modules.py`).

### CLI entry points (`python -m benchassist.<module>`)

`data_generation`, `validate_data`, `run_batch`, `audit_metrics`, `counterfactual_validity`, `narrative_robustness`, `stereotype_audit`, `hallucination_audit`, `statistical_analysis`, `qualitative_cases`, `human_review`, `mitigation_comparison`, `stability_metrics`, `model_comparison`, `grounding_comparison`, `final_report`, `pipeline`, `verify_pipeline`, `israeli_data`, `report`

Console script: `benchassist` → `run_batch:app` (Typer).

---

## 3. Detected gaps / fixes during QA

| Issue | Fix |
|-------|-----|
| Missing `stereotype_audit`, `qualitative_cases`, `validate_data` | **Added** modules + tests |
| `pipeline` lacked `--status` and full `--demo` | **Extended** `pipeline.py` |
| `final_report --auto` crashed on empty narrative CSV | **Fixed** `read_csv_optional` + empty narrative CSV headers |
| `qualitative_cases` sort KeyError | **Fixed** optional `remedy_strength_delta` column |
| Dashboard missing Stereotype tab | **Open** — stereotype outputs work via CLI; dashboard tab not added (see §7) |

### Not in scope (by design)

- **Party-role / power-asymmetry audit** — explicitly excluded; no `party_power` variants expected.

---

## 4. Unit test result

```
pytest -q  →  287 passed
```

No failures after QA fixes.

---

## 5. Integration test result (mock, `qa_mock` suffix)

### Part 5 — Data generation

| Command | Result |
|---------|--------|
| `--variant-set demographic` | OK |
| `--variant-set language_access` | OK |
| `--variant-set intersectional` | OK |
| `--variant-set narrative_framing` | OK |
| `--variant-set all` | OK — 420 counterfactual rows (50 base × variant families) |
| `python -m benchassist.validate_data` | OK (warnings: per-family CSV row counts vs 50 base cases) |

### Part 7–8 — Mock batches & stability

| Output | Verified |
|--------|----------|
| `qa_mock_v2_baseline.csv` | 10 rows |
| `qa_mock_v2_fairness_aware.csv` | 10 rows |
| `qa_mock_v2_demographic_blind.csv` | 10 rows |
| `qa_mock_v3_grounded.csv` | 10 rows; V3 fields present |
| `qa_mock_v2_repeated.csv` | 15 rows; `repetition_index` ∈ {1,2,3} |
| `stability_*_qa_mock_repeated.csv` | Created |

### Part 9–15 — Audits

| Module | Key outputs |
|--------|-------------|
| V2 metrics | `v2_pairwise_comparison_qa_mock_*.csv`, `v2_group_summary_qa_mock_*.csv` |
| Strict-only | `*_qa_mock_baseline_strict.csv` |
| Mitigation | `mitigation_comparison.csv` |
| Validity | `counterfactual_validity_qa_mock.csv` (+ narrative / credibility categories) |
| Narrative | `narrative_robustness_*_qa_mock.csv` (empty summary when limit-10 batch has no narrative types) |
| Stereotype | `stereotype_audit_*_qa_mock_baseline.csv` |
| Hallucination | `hallucination_audit_*_qa_mock_grounded.csv` |
| Statistical | `statistical_*_qa_mock_baseline.csv` + report |
| Qualitative | `qualitative_case_studies_qa_mock_baseline.csv` |
| Human review | `human_review_template_qa_mock.csv`, `human_review_rubric.md` |

### Part 18–19 — Reports & pipeline

| Command | Result |
|---------|--------|
| `final_report --auto` | OK → `results/report/final_audit_report.md` |
| `pipeline --status` | OK |
| `pipeline --print-real-run-plan` | OK (Gemini commands printed, not executed) |
| `pipeline --demo --limit 10 --output-suffix qa_pipeline` | OK |

### Part 20 — Dashboard smoke

- `app.py` import spec — OK  
- Tabs present: Overview, Group Metrics, Flagged, Case Explorer, Qualitative, Mitigation, Stability, Model Comparison, Human Review, Statistical, Legal Grounding, Counterfactual Validity, Narrative Robustness, Export, Methodology  
- **Stereotype & Identity Leakage tab** — not in `app.py` (CLI + tables only)

### Part 6 — Prompt checks

- V1/V2/V3 prompt bundles build successfully  
- V2 prompts include structured fields  
- Demographic-blind blinding removes known names (`blind_demographic_cues`)  
- Prompts emphasize non-binding judicial support (Hebrew/English disclaimers in system prompts)

---

## 6. Generated QA artifacts (representative)

```
results/outputs/qa_mock_v2_baseline.csv
results/outputs/qa_mock_v3_grounded.csv
results/tables/v2_pairwise_comparison_qa_mock_baseline.csv
results/tables/counterfactual_validity_qa_mock.csv
results/tables/stereotype_audit_group_summary_qa_mock_baseline.csv
results/tables/qualitative_case_studies_qa_mock_baseline.csv
results/tables/human_review_template_qa_mock.csv
results/report/final_audit_report.md
results/report/counterfactual_validity_qa_mock.md
results/report/stereotype_audit_qa_mock_baseline.md
```

Existing Gemini outputs under `results/` were **not overwritten** (QA uses `qa_mock_*` prefixes only).

---

## 7. Known limitations

1. **Limit-10 mock batches** use the first 10 counterfactual rows (typically demographic/neutral), so narrative robustness summaries may be **empty** unless a narrative-heavy batch is run.
2. **Base case count** may be 50 if HF/processed data was expanded locally; variant CSV row counts scale accordingly.
3. **Stereotype audit** uses keyword heuristics — high false-positive/negative risk; not legal proof.
4. **Statistical tests** are exploratory (no multiple-comparison correction).
5. **Dashboard** does not yet include a dedicated Stereotype tab (outputs loadable manually from `results/tables/`).

---

## 8. Known issues still open

| Priority | Issue |
|----------|-------|
| Low | Add Streamlit **Stereotype & Identity Leakage** tab (mirror narrative/hallucination tabs) |
| Low | Add **stereotype** section to `final_report.py` auto-discovery |
| Low | `mitigation_comparison.csv` has no suffix — QA run overwrote generic filename; use suffixed name in scripts if preserving multiple comparisons |
| Info | `verify_pipeline.py` is V1-oriented; prefer `pipeline --demo` for full V2/V3 QA |

---

## 9. Recommended next manual checks

1. Run `streamlit run app.py` and select a run bundle that includes `qa_mock` tables.  
2. Optional: full mock batch without `--limit` for richer narrative/stereotype charts.  
3. Optional: live Gemini run using `pipeline --print-real-run-plan` (requires API key in `.env`, costs money).  
4. Legal expert review of `human_review_template_qa_mock.csv` rows.

---

## 10. Commands reference (QA)

```bash
# Full offline demo
python -m benchassist.pipeline --demo --limit 10 --output-suffix qa_pipeline

# Status only
python -m benchassist.pipeline --status

# Validate data
python -m benchassist.validate_data

# Tests
pytest -q
```

---

## 11. Initial vs final test status

| Stage | Result |
|-------|--------|
| Initial `pytest` | 287 passed (before QA module additions) |
| After new modules + fixes | **287 passed** |
| After submission package builder | **306 passed** |
| Integration QA | **PASS** (with limitations in §7) |
| Submission package builder | **PASS** — see §12 |

---

## 12. Submission package builder

```bash
python -m benchassist.submission_package --auto
python -m benchassist.pipeline --status
```

| Artefact | Path |
|----------|------|
| Package directory | `results/submission_package/` |
| Zip archive | `results/submission_package.zip` |
| Manifest | `results/submission_package/MANIFEST.json` |
| Reviewer README | `results/submission_package/README_FOR_REVIEWERS.md` |

- `.env` is **not** copied into the package.
- Missing optional report/table globs are listed in `MANIFEST.json` under `missing_expected_files`.
- Unit tests: `tests/test_submission_package.py` (11 tests) + pipeline status assertions in `tests/test_qa_modules.py`.
- **2026-05-29 run:** 76 files, ~2.85 MB; zip at `results/submission_package.zip`.
- Missing optional patterns are recorded in `MANIFEST.json` (e.g. charts if not generated, optional doc files like `SUBMISSION_CHECKLIST.md`).
