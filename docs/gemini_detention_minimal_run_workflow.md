# Gemini Detention — Minimal Dangerousness Run Workflow

Canonical workflow for the **current BenchAssist-IL concept**:

- **Schema:** `detention_minimal_dangerousness_v2` (`case_summary`, `dangerousness_level`, `reasoning_text`)
- **Flagging:** dangerousness level change only ([detention_flagging_policy.md](detention_flagging_policy.md))
- **Corpus:** slim synthetic variants + address-proxy bucket (separate from strict rates)
- **Prompt modes:** baseline, fairness_aware, demographic_blind
- **Dashboard:** 7-tab slim audit (`data_status: gemini_minimal_address`)

Legacy **expanded full** / **full schema** configs remain for historical runs but are **not** the target for new Gemini execution.

---

## 0. Prerequisites

- Pilot QA passed (`results/report/gemini_detention_pilot_qa_report.md`)
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` set (never print the value)
- Synthetic CSV: `data/synthetic/detention_core_cases_with_address.csv`

Regenerate corpus (10 bases, slim + address):

```bash
make detention-regen-corpus
```

---

## 1. Preflight (required — no API calls)

```bash
make detention-preflight
# or:
python -m benchassist.detention_run_preflight \
  --config configs/gemini_detention_expanded_minimal_address.yaml
```

**Produces:**

- Corpus validation
- `results/gemini/detention_expanded_minimal_address/dry_run_manifest.json`
- `results/report/gemini_detention_expanded_minimal_address_run_plan.md`
- `results/report/gemini_detention_expanded_minimal_address_run_checklist.md`
- `results/report/gemini_detention_expanded_minimal_address_preflight_go_no_go.md`

Proceed only when **`READY_FOR_MINIMAL_ADDRESS_GEMINI_RUN: YES`**.

For a **brand-new** output directory, use `make detention-preflight-new` (fails if `output_dir` already has outputs).  
To re-validate an in-progress or completed run directory, use `make detention-preflight` (passes `--resume`).

---

## 2. Execute Gemini run

Use a **fresh** `output_dir` in the YAML if you need a clean run (or `--resume` for partial completion).

```bash
python -m benchassist.detention_gemini_full \
  --config configs/gemini_detention_expanded_minimal_address.yaml \
  --resume
```

**Outputs:** `parsed_outputs.jsonl` (with `exact_prompt_logged`), `run_manifest.json`, request logs.

Monitor parse-error rate; runner stops early if above configured threshold (10%).

---

## 3. Post-run (analysis + dashboard)

```bash
make detention-post-run
# Public demo export (no full case text in review JSON):
python -m benchassist.detention_post_run \
  --config configs/gemini_detention_expanded_minimal_address.yaml \
  --demo-redact-case-text
```

**Produces:**

- `analysis/detention_pairwise_comparison.csv`, flagged cases, cross-prompt tables
- `web_dashboard/public/data/` export + validation

---

## 4. Dashboard QA

```bash
make dashboard-qa
cd web_dashboard && npm run test:e2e
```

Checklist: [WEB_DASHBOARD_QA_CHECKLIST.md](../WEB_DASHBOARD_QA_CHECKLIST.md)

---

## Config reference

| Field | Value |
|-------|--------|
| Config | `configs/gemini_detention_expanded_minimal_address.yaml` |
| Model | `gemini-2.5-flash-lite` |
| Requests | rows × 3 prompt modes |
| Strict pairwise | neutral vs non-neutral (strict-eligible only) |
| Address proxy | separate `detention_address_proxy_pairwise_comparison.csv` |

---

## What we do **not** claim

- Flagged cases are **audit signals** for legal expert review
- Not proof of unlawful discrimination or “bias proven”
- Address strings are proxy-cautious stress tests, not individual identity proof
