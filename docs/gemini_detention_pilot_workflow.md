# Gemini Detention Pilot Workflow

Safe dry-run and tiny pilot workflow for **BenchAssist-IL Detention Audit**.

## Prerequisites

- [ ] Legal-expert approval of detention pilot corpus
- [ ] Synthetic data generated: `data/synthetic/detention_core_cases.csv`
- [ ] Real-case bench inputs: `data/real_cases/detention/pilot_corpus/detention_pilot_bench_inputs.csv`
- [ ] Python environment with project dependencies installed
- [ ] Optional for pilot only: `pip install google-genai`

## Environment setup (do not print the key)

Set one of:

```bash
export GEMINI_API_KEY="your-key-here"
# or
export GOOGLE_API_KEY="your-key-here"
```

Or add to `.env` at project root (**never commit `.env`**).

Verify presence without exposing the value:

```bash
python -c "from benchassist.config import resolve_gemini_api_key, get_settings; print('present' if resolve_gemini_api_key(get_settings()) else 'missing')"
```

## Step 1 — Dry-run (required, no API calls)

```bash
python -m benchassist.detention_gemini_plan \
  --config configs/gemini_detention_pilot.yaml \
  --dry-run
```

**Produces:**

- `results/gemini/detention_pilot/dry_run_manifest.json`
- `results/gemini/detention_pilot/pilot_selected_inputs.jsonl`
- `results/report/gemini_detention_pilot_dry_run_report.md`

Review the report. All checks must pass before pilot.

## Step 2 — Pilot run (tiny sample only)

**Only after dry-run passes and you explicitly approve API spend:**

```bash
python -m benchassist.detention_gemini_pilot \
  --config configs/gemini_detention_pilot.yaml \
  --resume
```

Default pilot plan: **2 base scenarios × 4 variants + 3 real cases × 3 prompt modes = 33 requests**.

**Produces:**

- `raw_responses.jsonl` — raw Gemini text
- `parsed_outputs.jsonl` — parsed + validated rows (append/resume safe)
- `parse_errors.jsonl` — failures
- `request_log_safe.jsonl` — metadata without secrets
- `run_manifest.json`

### Resume after interruption

```bash
python -m benchassist.detention_gemini_pilot \
  --config configs/gemini_detention_pilot.yaml \
  --resume
```

Existing successful rows are skipped. No `--force` overwrite.

## Step 3 — Pilot analysis

```bash
python -m benchassist.detention_pilot_analysis \
  --outputs results/gemini/detention_pilot/parsed_outputs.jsonl \
  --output-dir results/gemini/detention_pilot/analysis
```

**Produces:**

- `detention_pairwise_comparison.csv`
- `detention_group_summary.csv`
- `detention_flagged_cases.csv`
- `detention_real_case_review_outputs.csv`
- `detention_pilot_metric_summary.json`
- `detention_pilot_analysis_report.md`
- `results/report/gemini_detention_pilot_qa_report.md`

Strict fairness metrics use **synthetic controlled rows only**. Real cases are excluded.

## Step 4 — Dashboard export (local, not deploy)

```bash
python -m benchassist.vercel_export \
  --auto \
  --use-case detention \
  --run-dir results/gemini/detention_pilot \
  --data-status gemini_pilot
```

Preview:

```bash
cd web_dashboard && npm run dev
```

If full-text real cases are exported, the tool prints:

> Full unredacted legal text is being exported for internal expert review. Deploy only behind access control. Do not rely on URL secrecy.

## Inspecting parse errors

```bash
cat results/gemini/detention_pilot/parse_errors.jsonl | python -m json.tool
```

High parse error rate blocks early if above 20% (pilot config).

## Full run template (do NOT run yet)

Plan only:

```bash
python -m benchassist.detention_gemini_plan \
  --config configs/gemini_detention_full.yaml \
  --dry-run
```

Execute full run **only** when `gemini_detention_pilot_qa_report.md` recommends `ready_for_full_run: yes`.

## Methodology reminders

- Synthetic counterfactuals → strict fairness audit signals
- Real Israeli public legal text → realism / reliability / qualitative review only
- Metrics are **audit signals** — not proof of unlawful discrimination
- Pilot results are **preliminary** — not final research findings
- Dashboard with full text requires **access control** — URL secrecy is not enough

## Safety defaults

| Setting | Value |
|---------|-------|
| `overwrite_existing` | false |
| `dry_run_required` | true |
| `print_api_key` | false |
| `real_cases_in_strict_rates` | false |
| Model | gemini-2.5-flash-lite |
