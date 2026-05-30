# BenchAssist-IL Audit

**Responsible AI algorithmic audit · Concept 1: Bias in Language Models**

A reproducible audit pipeline for a toy Israeli judicial decision-support assistant. The project tests whether model outputs change when demographic or language-access cues vary but the underlying legal facts stay the same.

---

## Table of Contents

1. [Course Context](#course-context)
2. [System Under Audit](#system-under-audit)
3. [Responsible AI Issue](#responsible-ai-issue)
4. [Worldbuilding](#worldbuilding)
5. [Pipeline](#pipeline)
6. [Audit Metrics](#audit-metrics)
7. [Installation](#installation)
8. [Main Demo (Run From Scratch)](#main-demo-run-from-scratch)
9. [Optional: Live Gemini Runs](#optional-live-gemini-runs)
10. [Interactive Dashboard](#interactive-dashboard)
11. [Ethical Limitations](#ethical-limitations)
12. [Folder Structure](#folder-structure)
13. [Generated Report](#generated-report)
14. [Environment Variables](#environment-variables)
15. [Additional Commands](#additional-commands)
16. [License](#license)

---

## Course Context

This repository is the deliverable for a **Responsible AI (RAI) algorithmic audit** assignment, under **Concept 1: Bias in Language Models**.

The project does **not** train a new model. It builds a controlled evaluation harness: synthetic housing cases, demographic counterfactuals, automated metrics, a written audit report, and an optional review dashboard.

---

## System Under Audit

**BenchAssist-IL** is a toy Israeli **judicial decision-support assistant**. Given a short case summary in Hebrew, it produces a structured, **non-binding bench memo** with fields such as:

| Field | Description |
|-------|-------------|
| `case_summary` | Brief restatement of the facts |
| `legal_area` | Domain (e.g. housing) |
| `urgency` | low / medium / high |
| `recommended_direction` | e.g. grant, deny, partial |
| `recommended_action` | Suggested procedural step |
| `reasoning` | Short justification |
| `evidence_needed` | List of documents to gather |
| `confidence` | low / medium / high |
| `limitations` | Caveats and scope limits |

The system is **not** a judge, does **not** issue binding rulings, and must **not** be used as legal advice.

### Hybrid audit design: synthetic + real-case-inspired

The project uses **two dataset layers** (clearly separated in exports, reports, and dashboard):

| Layer | Purpose | Strict fairness rates? |
|-------|---------|------------------------|
| **Synthetic controlled** | Clean counterfactual fairness measurement (demographic, language, narrative variants) | **Yes** — main quantitative audit |
| **Real-case-inspired** | Realism, multi-domain coverage, reliability, stereotype/hallucination screening, qualitative review | **No** — realism/robustness signals only |

Real examples are derived from public/licensed material (e.g. [BrainboxAI/legal-training-il](https://huggingface.co/datasets/BrainboxAI/legal-training-il)). They are **not** authoritative legal advice and **do not** prove discrimination.

```bash
# Optional: ingest from local JSONL fixture or downloaded dataset
pip install datasets   # only for Hugging Face ingestion

python -m benchassist.real_case_ingestion \
  --source local_jsonl \
  --input tests/fixtures/legal_training_sample.jsonl \
  --output-dir data/real_cases \
  --max-per-domain 5

python -m benchassist.real_case_transform \
  --input data/real_cases/real_case_summaries.csv \
  --max-per-domain 5 \
  --output data/real_cases/real_case_bench_inputs.csv

python -m benchassist.run_batch \
  --provider mock \
  --schema-version v2 \
  --prompt-mode baseline \
  --input-cases data/real_cases/real_case_bench_inputs.csv \
  --output-prefix qa_real_cases_mock

python -m benchassist.real_case_audit \
  --outputs results/outputs/qa_real_cases_mock.csv \
  --output-suffix qa_real_cases_mock

python -m benchassist.vercel_export --auto
```

Hugging Face ingestion (when network + `datasets` available):

```bash
python -m benchassist.real_case_ingestion \
  --source huggingface \
  --dataset-id BrainboxAI/legal-training-il \
  --output-dir data/real_cases \
  --max-per-domain 30
```

Later Gemini pilot (manual — requires API key, not run in CI):

```bash
python -m benchassist.experiment_runner \
  --config configs/audit_experiment_real_cases_gemini_pilot.yaml \
  --execute --force
```

### Schema V2: legal-framing fields

Schema **v2** (`BenchMemoOutputV2`) extends the bench memo with categorical legal-framing fields so audits can compare substantive recommendation changes without noise from free-text paraphrasing:

| Field | Description |
|-------|-------------|
| `recommended_action_type` | Categorical action: `reject`, `request_more_evidence`, `regular_hearing`, `urgent_hearing`, `temporary_relief`, `immediate_protection` |
| `remedy_strength_score` | Integer 0–5 aligned with action type (0 = no action → 5 = immediate protection) |
| `evidence_burden_level` | `low` / `medium` / `high` — how much proof is needed before acting |
| `party_credibility_framing` | `supportive` / `neutral` / `skeptical` — memo tone toward the petitioner |
| `rights_orientation` | `low` / `medium` / `high` — emphasis on protective/rights considerations |
| `procedural_posture` | `continue_regular_process`, `expedited_review`, or `urgent_intervention` |
| `reasoning_text` | Free-text reasoning (replaces v1 `reasoning`) |
| `risk_flags` | Structured flags (e.g. `possible_urgent_harm`, `missing_evidence`) |

V1 outputs (`recommended_direction`, `recommended_action`, `reasoning`) remain supported. Use `normalize_bench_memo_output()` to map either schema to a common audit dictionary. Prompt templates: `prompts/system_prompt_v2.txt` and `prompts/bench_memo_schema_v2.json`.

**Why this matters:** The first audit iteration showed high recommendation flip rates, but free-text paraphrasing can inflate flip metrics. V2 separates categorical recommendation fields from wording, so the audit can distinguish substantive changes from harmless phrasing differences.

**Quick mock V2 example:**

```bash
python -c "
from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.prompt_builder import build_prompt
from benchassist.model_client import MockModelClient, parse_bench_memo_output_v2
case = create_counterfactual_cases(create_base_cases())[0]
messages = build_prompt(case, schema_version='v2')
raw = MockModelClient().generate(messages)
parsed, err = parse_bench_memo_output_v2(raw)
print(parsed.model_dump() if parsed else err)
"
```

---

**Demographic and language-access bias in legal language model outputs.**

Israeli court and housing disputes involve diverse parties (names, ethnicity, gender, immigration background, language proficiency). If a decision-support model treats identical legal facts differently depending on irrelevant cues, it may reinforce unfairness in clerical workflows—even when outputs are labeled “preliminary.”

**Audit question:**

> When only demographic or linguistic presentation changes, does the model’s urgency, recommended remedy, tone, or reasoning shift in ways that are not justified by the facts?

---

## Worldbuilding

The fictional **Israeli Court Administration** pilots BenchAssist-IL internally for **judicial clerks and judges** handling **housing disputes** (rent, eviction, repairs, deposits, safety).

The tool is framed as a **research prototype**: clerks paste a short case summary and receive a draft memo to speed up desk work. All outputs require human review before any procedural step is taken.

This repository audits that prototype—not a deployed national court system.

---

## Pipeline

```
┌──────────────────────┐
│ 1. Base cases        │  12 synthetic Hebrew housing summaries
│    data/processed/   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 2. Counterfactuals   │  10 variants per case (120 total)
│    data/audit/       │  names, demographics, broken Hebrew, …
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 3. Run model         │  mock (offline) or Gemini (optional)
│    results/outputs/  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 4. Compute metrics   │  compare each variant to neutral_he
│    results/tables/   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 5. Report + dashboard│  audit_report.md, charts, Streamlit UI
│    results/report/   │
└──────────────────────┘
```

| Step | What it does | Main outputs |
|------|----------------|--------------|
| 1 | Generate base cases | `data/processed/base_cases.{csv,jsonl}` |
| 2 | Generate demographic/language counterfactuals | `data/audit/counterfactual_cases.{csv,jsonl}` |
| 3 | Run model on every variant | `results/outputs/model_outputs.{csv,jsonl}` |
| 4 | Compute audit metrics | `results/tables/group_summary.csv`, `flagged_cases.csv`, … |
| 5 | Generate report (and optional dashboard) | `results/report/audit_report.md`, `results/charts/*.png` |

**Counterfactual variant types (10 per base case, demographic default):** `neutral_he`, Jewish/Arab names, Ethiopian-Israeli woman, Russian-speaking immigrant, foreign worker, single mother, elderly tenant, broken Hebrew, and related demographic cues.

### Language-access bias variants

The audit can also generate **language-access** counterfactuals that hold legal facts constant while changing linguistic register:

| Variant type | Purpose |
|--------------|---------|
| `formal_hebrew` | Clerk-like formal Hebrew |
| `simple_hebrew` | Plain Hebrew without legal jargon |
| `broken_hebrew_v2` | Non-native Hebrew (improved v2; legacy `broken_hebrew` remains in demographic set) |
| `arabic` | Same facts in simple Modern Standard Arabic |
| `translated_arabic_style_hebrew` | Hebrew with Arabic-influenced phrasing |
| `short_vague_hebrew` | Short layperson summary (tests whether less detail reduces protection) |
| `lawyer_like_hebrew` | Formal legally sophisticated Hebrew |

**Why this matters:** Access to justice depends on language ability and legal literacy. In a judge-facing system, weaker input language should not automatically produce weaker judicial protection unless legally relevant facts are actually missing. The short vague variant is an intentional edge case: less detail may justify lower confidence, but the system should request missing information rather than treat the party as less credible.

**Variants per base case:**

| `variant_set` | Demographic | Language-access | Intersectional | Total |
|---------------|-------------|-----------------|----------------|-------|
| `demographic` (default) | 10 | 0 | 0 | 10 |
| `language_access` | 0 | 7 | 0 | 7 |
| `intersectional` | 0 | 0 | 8 | 8 |
| `all` | 10 | 7 | 8 | 25 |

Regenerate with:

```bash
python -m benchassist.data_generation --variant-set all
```

Optional exports: `data/audit/demographic_variants.csv`, `data/audit/language_access_variants.csv`, `data/audit/intersectional_variants.csv`.

### Intersectional bias variants

The audit can also generate **intersectional** counterfactuals that combine demographic status, language ability, age, gender, disability, immigration status, and socioeconomic vulnerability:

| Variant type | Combined cues |
|--------------|---------------|
| `arab_woman_broken_hebrew` | Arab woman + non-native Hebrew |
| `foreign_worker_broken_hebrew` | Foreign worker + non-native Hebrew |
| `elderly_arab_tenant` | Elderly Arab tenant + neutral/formal Hebrew |
| `single_mother_low_income` | Single mother + low income |
| `ethiopian_israeli_woman_public_housing` | Ethiopian-Israeli woman + public housing |
| `disabled_tenant_broken_hebrew` | Tenant with disability + non-native Hebrew |
| `arabic_input_arab_woman` | Arab woman + Arabic input |
| `russian_speaking_elderly_immigrant` | Elderly Russian-speaking immigrant + simple Hebrew |

**Why this matters:** Harms in real legal systems often emerge at intersections of identity and vulnerability, not from a single cue in isolation. Some variants include vulnerability cues that may be legally relevant (disability, age, public housing). These should be analyzed carefully: not every output difference is automatically unfair. The audit asks whether a change in legal framing, evidentiary burden, urgency, or remedy strength is legally justified or driven by stereotype — not whether identity labels alone prove discrimination.

---

## Audit Metrics

Each variant is compared to the **`neutral_he`** baseline for the same `case_id`.

| Metric | What it measures |
|--------|------------------|
| **Recommendation flip rate** | Share of variants where urgency, `recommended_direction`, or remedy-strength proxy differs from neutral |
| **Urgency difference** | Numeric urgency score (low=1, medium=2, high=3) vs neutral |
| **Remedy strength** | 0–5 proxy from direction + action text (reject → urgent/temporary relief) |
| **Output length** | Word count in reasoning + action + limitations |
| **Skepticism score** | Count of hesitant phrases (e.g. “לא ברור”, “insufficient”) |
| **Rights/protection score** | Count of protective phrases (e.g. “סעד זמני”, “rights”) |
| **Parse error rate** | Share of runs where model JSON could not be parsed |
| **Qualitative flagged examples** | Cases flagged when urgency/remedy/skepticism/length diverge materially from neutral |

Group-level summaries appear in `results/tables/group_summary.csv`. Flagged rows are in `results/tables/flagged_cases.csv`. The markdown report includes narrative examples.

### V2 legal-framing audit metrics

V2 metrics normalize both legacy and V2 model outputs via `normalize_bench_memo_output()`, then compare structured legal-framing fields to the `neutral_he` baseline:

| Signal | What it measures |
|--------|------------------|
| **Action type flip** | Categorical `recommended_action_type` changed vs neutral |
| **Remedy weakening** | Lower `remedy_strength_score` than neutral |
| **Higher evidentiary burden** | Higher `evidence_burden_level` than neutral |
| **More skeptical credibility framing** | Shift toward `skeptical` vs neutral |
| **Weaker rights orientation** | Lower `rights_orientation` than neutral |
| **Weaker procedural posture** | Lower procedural urgency than neutral |
| **Legal framing bias flag** | Any of the weakening/hardening signals above (excluding harmless paraphrase) |

Outputs (distinct filenames — existing v1 tables are not overwritten):

- `results/tables/v2_pairwise_comparison.csv`
- `results/tables/v2_group_summary.csv`
- `results/tables/v2_flagged_cases.csv`
- Charts in `results/charts/v2_*.png`

**Why this is better than v1 flip rate:** The first metric could over-count harmless paraphrasing in free-text `recommended_direction` / `recommended_action`. V2 compares structured legal-framing fields and is therefore more interpretable for bias auditing.

```bash
python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs.csv
# or
benchassist audit-metrics --version v2 --input results/outputs/model_outputs.csv
```

### Fairness-aware prompt mitigation

The **baseline** system tests ordinary model behavior. The **fairness-aware** system gives the model explicit instructions to treat legally equivalent cases equivalently — without hiding demographic or language cues from the input.

The goal is to test whether prompt-level mitigation reduces legal-framing disparities across counterfactual variants. This is not a complete solution: a fairness prompt may reduce some biased behavior, but it can also create false confidence. Results still require quantitative and qualitative audit review. This connects to **audit-washing**: mitigation claims should be supported by measured comparison, not assumed because the prompt sounds fair.

**Prompt modes:** `baseline` (default) and `fairness_aware` (requires `schema_version=v2`).

**Output naming:** V1 baseline runs still write `model_outputs.csv`. V2 runs use separate files so baseline and fairness-aware batches do not overwrite each other:

- `results/outputs/model_outputs_v2_baseline.csv`
- `results/outputs/model_outputs_v2_fairness_aware.csv`

Run baseline V2 mock:

```bash
python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode baseline --limit 5
```

Run fairness-aware V2 mock:

```bash
python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode fairness_aware --limit 5
```

Run V2 metrics with suffixes:

```bash
python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs_v2_baseline.csv --output-suffix baseline
python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs_v2_fairness_aware.csv --output-suffix fairness_aware
```

Compare mitigation:

```bash
python -m benchassist.mitigation_comparison \
  --baseline results/tables/v2_group_summary_baseline.csv \
  --fairness-aware results/tables/v2_group_summary_fairness_aware.csv
```

Writes `results/tables/fairness_mitigation_comparison.csv` with per-variant deltas (fairness-aware minus baseline).

### Demographic-blinded mitigation

This mode **removes or neutralizes identity cues** before sending the case to the model. The goal is to test whether reducing exposure to irrelevant demographic information reduces legal-framing disparities.

Blinding is not always correct: some vulnerability cues may be legally relevant. The project therefore preserves certain cues in neutral form — for example age (`בעל דין מבוגר`), disability (`בעל דין עם מוגבלות`), single parent (`הורה יחיד`), public housing, and urgent safety harm. Broken Hebrew and Arabic input are **not** translated or “fixed”; only identity labels are neutralized.

This is a **toy implementation**, not a production anonymization system. Compare baseline, fairness-aware, and demographic-blinded modes together.

**Prompt mode:** `demographic_blind` (requires `schema_version=v2`).

Output files:

- `results/outputs/model_outputs_v2_demographic_blind.csv`

Each output row keeps the original `input_text` plus `blinded_input_text` and `blinding_metadata` for audit traceability.

```bash
python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode demographic_blind --limit 5
python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs_v2_demographic_blind.csv --output-suffix demographic_blind
python -m benchassist.mitigation_comparison \
  --baseline results/tables/v2_group_summary_baseline.csv \
  --fairness-aware results/tables/v2_group_summary_fairness_aware.csv \
  --demographic-blind results/tables/v2_group_summary_demographic_blind.csv
```

The three-way comparison writes `results/tables/mitigation_comparison.csv` with baseline, fairness-aware, and demographic-blind columns plus deltas vs baseline.

### Repeated-run stability testing

LLM outputs can vary even when the **exact same prompt** is sent multiple times. Repeated-run testing helps separate **random model instability** from **counterfactual demographic/language instability**.

- If counterfactual differences are no larger than random variation, bias claims should be stated cautiously.
- If counterfactual differences are larger or patterned by group, this strengthens the audit finding.
- This is especially important for language-model audits because output variation can be mistaken for bias.

**CLI flags:** `--repetitions N` (default 1), `--temperature`, optional `--mock-unstable` for deterministic mock variation in tests.

Run repeated mock test:

```bash
python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode baseline --limit 5 --repetitions 3 --mock-unstable
```

Run repeated Gemini test later:

```bash
python -m benchassist.run_batch --provider gemini --schema-version v2 --prompt-mode baseline --limit 50 --repetitions 3 --temperature 0.7
```

Compute stability:

```bash
python -m benchassist.stability_metrics --input results/outputs/model_outputs_v2_baseline.csv --output-suffix baseline
```

With pairwise comparison (counterfactual vs random diagnostic):

```bash
python -m benchassist.stability_metrics \
  --input results/outputs/model_outputs_v2_baseline.csv \
  --pairwise results/tables/v2_pairwise_comparison_baseline.csv \
  --output-suffix baseline
```

Outputs:

- `results/tables/stability_within_prompt.csv` (or `_<suffix>.csv`)
- `results/tables/stability_group_summary.csv`
- `results/tables/counterfactual_vs_random_instability.csv` (when `--pairwise` provided)
- Charts in `results/charts/stability_*.png`

Each output row includes `repetition_index` (starting at 1).

---

## Multi-model comparison

Bias findings are stronger when tested across more than one language model. If the same demographic or language-access pattern appears across models, it suggests a broader LLM behavior rather than a quirk of one vendor. If the pattern appears only in one model, it may be model-specific.

- **Gemini 2.5 Flash-Lite** (`gemini-2.5-flash-lite`) — main model for cost-efficient audit runs.
- **Gemini 2.5 Flash** (`gemini-2.5-flash`) — higher-quality comparison on a smaller sample.
- **Mock mode** — tests pipeline behavior only; do not use mock outputs for final bias claims.

Set `MODEL_PROVIDER=gemini` and `MODEL_NAME=gemini-2.5-flash-lite` in `.env` (never commit `.env`). API keys: `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

### Run Gemini Flash-Lite baseline

```bash
python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v2 --prompt-mode baseline --limit 50
```

### Run Gemini Flash-Lite fairness-aware

```bash
python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v2 --prompt-mode fairness_aware --limit 50
```

### Run Gemini Flash-Lite demographic-blind

```bash
python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash-lite --schema-version v2 --prompt-mode demographic_blind --limit 50
```

### Run Gemini Flash smaller comparison

```bash
python -m benchassist.run_batch --provider gemini --model-name gemini-2.5-flash --schema-version v2 --prompt-mode baseline --limit 15
```

### V2 metrics with suffixes

```bash
python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs_gemini-2.5-flash-lite_v2_baseline.csv --output-suffix gemini_flash_lite_baseline

python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs_gemini-2.5-flash_v2_baseline.csv --output-suffix gemini_flash_baseline
```

### Compare models

```bash
python -m benchassist.model_comparison \
  --summary results/tables/v2_group_summary_gemini_flash_lite_baseline.csv \
  --summary results/tables/v2_group_summary_gemini_flash_baseline.csv
```

Print a suggested run plan (does not execute commands):

```bash
python -m benchassist.model_comparison --print-run-plan
```

Outputs: `results/tables/model_comparison.csv`, `results/tables/model_comparison_pivot.csv`, and charts in `results/charts/model_comparison_*.png`.

---

## Manual human-review rubric

Automatic metrics and flagged-case lists are **screening tools only**. Human review is needed to determine whether output differences are substantively meaningful, legally justified, or potentially biased.

The rubric asks reviewers to score:

- Factual equivalence between neutral and variant inputs
- Legal justification for output differences
- Bias concern and stereotype / irrelevant assumptions
- Judicial workflow impact
- Legal accuracy and tone
- Evidence-burden fairness

Completed reviews can be summarized for the final audit report. If two reviewers are available, they should review independently and compare disagreements.

### Generate review template

```bash
python -m benchassist.human_review generate-template \
  --qualitative-cases results/tables/qualitative_case_studies_gemini_flash_lite_baseline.csv \
  --output results/tables/human_review_template.csv
```

This also writes rubric instructions to `results/report/human_review_rubric.md`.

### Summarize completed review

```bash
python -m benchassist.human_review summarize-review \
  --review results/tables/human_review_completed.csv \
  --output results/tables/human_review_summary.csv
```

Additional outputs: `results/tables/human_review_high_concern_cases.csv` and `results/report/human_review_summary.md`.

---

## Final audit report

The final report combines metrics, qualitative cases, human review, mitigation comparison, stability testing, and **audit-washing** analysis. It follows Goodman & Tréhu’s audit questions: **Why, Who, What/When, How**.

Use it as the basis for your written submission. It is **not** a legal certification and should not be framed as proof that the system is safe or unbiased.

### Generate report with auto-discovery

```bash
python -m benchassist.final_report --auto
```

### Generate report with explicit files

```bash
python -m benchassist.final_report \
  --group-summary results/tables/v2_group_summary_gemini_flash_lite_baseline.csv \
  --pairwise results/tables/v2_pairwise_comparison_gemini_flash_lite_baseline.csv \
  --flagged results/tables/v2_flagged_cases_gemini_flash_lite_baseline.csv \
  --qualitative results/report/qualitative_case_studies_gemini_flash_lite_baseline.md \
  --human-review-summary results/report/human_review_summary.md \
  --mitigation-comparison results/tables/mitigation_comparison.csv \
  --model-comparison results/tables/model_comparison.csv \
  --stability-summary results/tables/stability_group_summary_baseline.csv \
  --output results/report/final_audit_report.md
```

Saved by default to `results/report/final_audit_report.md`.

---

## Statistical uncertainty analysis

Rates and mean deltas alone do not show whether an observed gap might be noise. The statistical module adds **Wilson 95% confidence intervals** for binary V2 flags, **bootstrap 95% confidence intervals** for numeric legal-framing deltas, and **exploratory paired tests** (Wilcoxon when `scipy` is installed, otherwise a sign test) against zero. Benjamini–Hochberg FDR adjustment is applied to paired-test *p*-values.

These outputs are **exploratory audit signals** for screening and interpretation with qualitative legal review. They do **not** prove unlawful discrimination.

### Run analysis on an existing pairwise CSV

```bash
python -m benchassist.statistical_analysis \
  --pairwise results/tables/v2_pairwise_comparison_gemini_flash_lite_baseline.csv \
  --output-suffix gemini_flash_lite_baseline
```

Optional: `--bootstrap-samples 2000`, `--seed 42`, `--group-summary results/tables/v2_group_summary_<suffix>.csv`

**Outputs:**

| Artefact | Path |
|----------|------|
| Group effects + CIs | `results/tables/statistical_group_effects_<suffix>.csv` |
| Paired tests | `results/tables/statistical_pairwise_tests_<suffix>.csv` |
| Markdown report | `results/report/statistical_analysis_<suffix>.md` |
| Effect-size chart | `results/charts/statistical_effect_sizes_<suffix>.png` |
| CI chart | `results/charts/statistical_confidence_intervals_<suffix>.png` |

The Streamlit dashboard **Statistical Analysis** tab and the final audit report **Statistical Uncertainty** section pick up these files when present.

Optional scipy: `pip install -e '.[stats]'`

---

## Legal-source grounding and hallucination audit

Grounded mode supplies a **small local toy knowledge base** (`data/knowledge/israeli_housing_knowledge.jsonl`). The model must cite allowed source IDs and flag unsupported legal claims. The hallucination audit checks **invalid citations**, **unsupported claims**, and **hallucination risk** against those snippets only.

This does **not** certify legal correctness under Israeli law. It helps experts separate **fairness screening** from **general legal reliability** concerns.

### Run grounded mock batch

```bash
python -m benchassist.run_batch \
  --provider mock \
  --schema-version v3 \
  --prompt-mode grounded \
  --limit 5 \
  --top-k-sources 5
```

Outputs: `results/outputs/model_outputs_mock-benchassist_v3_grounded.csv`

### Run hallucination audit

```bash
python -m benchassist.hallucination_audit \
  --input results/outputs/model_outputs_mock-benchassist_v3_grounded.csv \
  --output-suffix mock_grounded
```

Outputs:

| Artefact | Path |
|----------|------|
| Per-output metrics | `results/tables/hallucination_audit_per_output_<suffix>.csv` |
| Group summary | `results/tables/hallucination_audit_group_summary_<suffix>.csv` |
| Markdown report | `results/report/hallucination_audit_<suffix>.md` |

### Optional grounded Gemini run (requires API key)

```bash
python -m benchassist.run_batch \
  --provider gemini \
  --model-name gemini-2.5-flash-lite \
  --schema-version v3 \
  --prompt-mode grounded \
  --top-k-sources 5
```

### Offline grounded demo (mock + audit)

```bash
python -m benchassist.pipeline --demo --limit 10
python -m benchassist.pipeline --print-real-run-plan
```

---

## Counterfactual validity audit

Counterfactual bias auditing depends on **factual equivalence**: variants should preserve the same legal facts while changing demographic or language cues. This module uses deterministic keyword heuristics to classify variants and flag pairs that may not support strict bias claims.

- **Strict demographic** variants (name-only, high preservation) support stronger bias comparisons.
- **Language-access** variants are valid but may lose detail; interpret cautiously.
- **Short-vague** variants are **access-to-justice stress tests**, not strict demographic counterfactuals.
- **Vulnerability** and **intersectional** variants may add legally relevant facts; outcomes may differ for justified reasons.
- The heuristic audit **does not replace human legal review**.

### Run validity audit

```bash
python -m benchassist.counterfactual_validity \
  --base-cases data/processed/base_cases.csv \
  --counterfactuals data/audit/counterfactual_cases.csv \
  --output-suffix current
```

Outputs:

| Artefact | Path |
|----------|------|
| Per-variant table | `results/tables/counterfactual_validity_{suffix}.csv` |
| Summary | `results/tables/counterfactual_validity_summary_{suffix}.csv` |
| Report | `results/report/counterfactual_validity_{suffix}.md` |

### Run V2 metrics with strict filtering

```bash
python -m benchassist.audit_metrics \
  --version v2 \
  --input results/outputs/model_outputs_gemini-2.5-flash-lite_v2_baseline.csv \
  --validity results/tables/counterfactual_validity_current.csv \
  --strict-only \
  --output-suffix gemini_flash_lite_baseline
```

Writes tables with `_strict` suffix (e.g. `v2_group_summary_gemini_flash_lite_baseline_strict.csv`).

---

## Narrative-framing robustness audit

The system tests whether **the same legal facts** receive different structured treatment when phrased in different narrative styles (neutral clerk summary, emotional layperson, skeptical clerk, party-sympathy framing, passive voice, rights/procedure emphasis, credibility priming).

This is relevant to **bias in language models** because LLMs may respond to tone, emotionality, skepticism, or party-favorable wording—not only explicit demographic labels. Narrative robustness is **not** the same as demographic fairness, but it matters in a judge-facing judicial workflow.

- **Strict narrative counterfactuals** (heuristic): style changes with high fact preservation.
- **Credibility-priming variants** are **stress tests**, not strict factual counterfactuals.
- **Human legal review** is required; screening metrics are not findings of discrimination.

### Generate narrative variants

```bash
python -m benchassist.data_generation --variant-set narrative_framing
```

Writes `data/audit/narrative_framing_variants.csv` plus the usual `counterfactual_cases.csv` / `.jsonl`.

### Run model on narrative variants

```bash
python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode baseline --limit 10
python -m benchassist.audit_metrics --version v2 --input results/outputs/<outputs>.csv --output-suffix narrative
```

### Run narrative robustness analysis

```bash
python -m benchassist.narrative_robustness \
  --pairwise results/tables/v2_pairwise_comparison_<suffix>.csv \
  --validity results/tables/counterfactual_validity_current.csv \
  --output-suffix <suffix>
```

Outputs:

| Artefact | Path |
|----------|------|
| Group summary | `results/tables/narrative_robustness_summary_{suffix}.csv` |
| Filtered pairwise rows | `results/tables/narrative_robustness_pairwise_{suffix}.csv` |
| Cross-pair contrasts | `results/tables/narrative_robustness_cross_pairs_{suffix}.csv` |
| Report | `results/report/narrative_robustness_{suffix}.md` |

---

## Installation

### Prerequisites

- **Python ≥ 3.11**
- **macOS / Linux / WSL** (commands below use bash)
- **No API key** required for the default demo (mock model)
- Optional: **Google Gemini API key** for live model runs

### Steps (for TAs / graders)

```bash
# 1. Clone and enter the project directory (important: not the parent folder)
git clone <repo-url>
cd BenchAssist-IL-Audit

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install the package (includes pytest; add [dashboard] for Streamlit UI)
pip install -e '.[dev,dashboard]'

# 4. Optional environment file (defaults are fine for mock demo)
cp .env.example .env
```

**Optional extras** (not required for grading):

```bash
pip install -e '.[genai]'      # Google Gemini SDK
pip install -e '.[datasets]'   # Hugging Face explorer only
```

### Verify install

```bash
python -m pytest -q
```

Expected: all tests pass (mock provider, no network).

---

## Main Demo (Run From Scratch)

**One command** runs the full pipeline offline with the deterministic mock model:

```bash
cd BenchAssist-IL-Audit
source .venv/bin/activate
pip install -e '.[datasets]'   # only needed for Hugging Face mode below
python -m benchassist.verify_pipeline
```

**Larger run using Hugging Face excerpts** (requires network on first download):

```bash
# First Gemini run (50 base cases, 1000 HF rows scanned, all legal domains)
python -m benchassist.verify_pipeline --provider gemini --data-source hf \
  --hf-target 50 --hf-fetch 1000 --hf-all-areas

# Housing only (default for mock / smaller HF pulls)
python -m benchassist.verify_pipeline --data-source hf --hf-target 100 --hf-fetch 5000

# Multiple legal domains (balanced across areas)
python -m benchassist.verify_pipeline --data-source hf --hf-target 120 --hf-fetch 8000 \
  --hf-legal-areas housing,labor,family,criminal,administrative --hf-stratify-areas

# All classifiable domains from the sample
python -m benchassist.verify_pipeline --data-source hf --hf-target 150 --hf-fetch 10000 --hf-all-areas

streamlit run app.py
```

Supported HF domain labels: `housing`, `labor`, `family`, `criminal`, `tort`, `administrative`, `commercial`, `immigration` (keyword-based classification on Hebrew text).

This builds base cases from [BrainboxAI/legal-training-il](https://huggingface.co/datasets/BrainboxAI/legal-training-il), 10× counterfactual variants per case, and fills the dashboard.

**Expected runtime:** ~10–30 seconds for synthetic (120 runs); HF mode with 100 bases (~1,000 runs) is typically a few minutes on mock.

**Expected final output (example):**

```
==================================================
  Pipeline verification complete
==================================================
  Base cases:              12
  Counterfactual cases:      120
  Model outputs:             120
  group_summary.csv:         .../results/tables/group_summary.csv
  audit_report.md:           .../results/report/audit_report.md
  Charts directory:          .../results/charts
==================================================
```

Then open the report: [`results/report/audit_report.md`](results/report/audit_report.md)

### Run stages individually (optional)

```bash
benchassist generate-housing
benchassist counterfactual-cases
python -m benchassist.run_batch --provider mock
benchassist audit
python -m benchassist.report
```

---

## Optional: Live Gemini Runs

Requires `pip install -e '.[genai]'` and a valid API key.

```bash
export MODEL_PROVIDER=gemini
export GEMINI_API_KEY=your_key_here
export MODEL_NAME=gemini-2.0-flash

python -m benchassist.run_batch --provider gemini
benchassist audit
python -m benchassist.report
```

Or inline:

```bash
MODEL_PROVIDER=gemini GEMINI_API_KEY=your_key_here \
  python -m benchassist.run_batch --provider gemini
```

Live runs need network access and may incur API cost. The course demo does **not** require Gemini.

---

## Interactive legal-expert dashboard

The dashboard is for **legal experts**, TAs, and **Responsible AI** reviewers. It reads **local CSV/Markdown/chart files only** — it does **not** call Gemini, OpenAI, or any external API.

### Launch

```bash
pip install -e '.[dashboard]'
streamlit run app.py
```

After a pipeline or experiment run, refresh the browser. The sidebar **auto-prioritizes** real Gemini runs over QA/mock when **Use latest files automatically** is checked.

### What it shows

- **Audit signal rates** by variant type (screening only — not proof of discrimination)
- **Flagged / review queue** sorted by severity (review priority, not a legal finding)
- **Case Explorer** — side-by-side neutral vs counterfactual (best for presentations)
- **Counterfactual validity**, **mitigation**, **narrative**, **stereotype**, **grounding**, **statistics**
- **Human-review template** download and **Reports & exports** (final report, submission zip)

### Recommended workflow

1. **Overview** — warnings, run metadata, headline signal rates.
2. **Main Audit Results** — charts by `variant_type`.
3. **Flagged Cases** — filter and sort; turn off *Flagged pairs only* if the queue is empty.
4. **Case Explorer** — compare structured fields and download a per-case review note CSV.
5. **Counterfactual Validity** — check which pairs support strict bias comparisons.
6. **Stereotype & Identity Leakage** and **Legal Grounding & Hallucination** — specialized screens.
7. **Human Review** — export `human_review_template*.csv`.
8. **Reports & Exports** — `final_audit_report.md`, submission package zip.
9. **Methodology & Limitations** — before writing conclusions.

### Choosing a run

Use the sidebar **Audit run** selector. Labels such as `Gemini Flash-Lite (pilot) · baseline` map to files like `v2_group_summary_gemini_flash_lite_pilot_*_v2_baseline.csv`. Open **Loaded files** to see exact paths.

### Important cautions

- Metrics are **audit signals** / **possible concerns** — not “bias proven.”
- **Human legal review** is required before any fairness or deployment claim.
- Hebrew and Arabic text are shown in scrollable fields for readability.

See `DASHBOARD_REVIEW_CHECKLIST.md` for screenshot guidance before submission.

### Vercel research dashboard (shareable)

A separate **Next.js** read-only dashboard in `web_dashboard/` is designed for team sharing on Vercel — story-driven layout, plain-language section guides, shared filters, and no backend/API keys.

**Shareable Vercel Results Dashboard** — export JSON, preview locally, deploy to Vercel.

```bash
# Export latest audit JSON
python -m benchassist.vercel_export --auto

# Run locally
cd web_dashboard
npm install
npm run dev
```

Deploy preview: `vercel` · Production: `vercel --prod`

See `web_dashboard/README.md` and `VERCEL_DEPLOYMENT_CHECKLIST.md` for full steps.

### Quick start (mock demo)

```bash
python -m benchassist.verify_pipeline --provider mock --limit 20
streamlit run app.py
```

---

## Ethical Limitations

- **Toy system** — BenchAssist-IL is a course prototype, not production court software.
- **Not legal advice** — Outputs are illustrative memos only.
- **Not an AI judge** — The model must not replace judicial decision-making.
- **Synthetic data** — All audit cases are fictional Hebrew housing summaries; they are **not** copied from real dockets or private records.
- **Human review required** — Any real-world use would need qualified legal professionals to review outputs.
- **Metrics are indicators, not proof** — Divergence across counterfactuals suggests areas to investigate; it does not by itself prove unlawful discrimination.
- **Prompt sensitivity** — System and user prompts shape behaviour; fairness findings are tied to this evaluation setup.
- **Optional external data** — The Hugging Face explorer (`benchassist.israeli_data`) is for inspiration only; check licensing before reusing any external text.

---

## Folder Structure

```
BenchAssist-IL-Audit/
├── app.py                      # Streamlit audit dashboard
├── data/
│   ├── raw/                    # Optional external samples
│   ├── processed/              # Base cases (CSV, JSONL)
│   └── audit/                  # Counterfactual variants (CSV, JSONL)
├── prompts/
│   ├── system_prompt.txt       # BenchAssist-IL system prompt (v1)
│   ├── system_prompt_v2.txt      # System prompt for BenchMemoOutputV2
│   ├── bench_memo_schema.json  # JSON output schema (v1)
│   └── bench_memo_schema_v2.json # JSON output schema (v2)
├── results/
│   ├── outputs/                # model_outputs.csv, .jsonl
│   ├── tables/                 # group_summary, flagged_cases, per_case_comparison
│   ├── charts/                 # PNG charts for the report
│   └── report/
│       └── audit_report.md     # ← main written deliverable
├── src/benchassist/            # Python package
│   ├── verify_pipeline.py      # one-command demo
│   ├── run_batch.py            # CLI & model batch
│   ├── data_generation.py      # cases & counterfactuals
│   ├── model_client.py         # mock + Gemini clients
│   ├── prompt_builder.py
│   ├── audit_metrics.py        # v1 counterfactual metrics + CLI entry
│   ├── audit_metrics_v2.py     # v2 legal-framing metrics
│   ├── report.py
│   ├── israeli_data.py         # optional HF explorer
│   ├── config.py
│   └── schemas.py
├── tests/                      # pytest suite
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Generated Report

After `python -m benchassist.verify_pipeline`, open:

**[`results/report/audit_report.md`](results/report/audit_report.md)**

The report includes dataset summary, group metrics, flagged cases, qualitative examples, charts (linked from `results/charts/`), limitations, and next steps.

---

## Environment Variables

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `mock` | `mock` (offline) or `gemini` |
| `MODEL_NAME` | `mock-benchassist` | Model ID for the provider |
| `GEMINI_API_KEY` | *(empty)* | Required when using Gemini |
| `TEMPERATURE` | `0.0` | Sampling temperature |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Safe experiment runner

Plan or run the **full audit workflow** from a YAML config. **Default is dry-run only** — no model calls, no API spend.

| Mode | Flag | Behavior |
|------|------|----------|
| Dry-run (default) | *(none)* or `--dry-run` | Print plan, cost estimate, output paths; write `results/experiments/<name>/` |
| Execute | `--execute` | Run all steps (requires API key for Gemini) |
| Resume | `--execute --resume` | Skip steps whose outputs already exist |
| Force | `--execute --force` | Overwrite existing outputs |

**Dry-run real Gemini audit:**

```bash
python -m benchassist.experiment_runner \
  --config configs/audit_experiment_gemini_flash_lite.yaml \
  --dry-run
```

**Run mock QA experiment (offline, limit 10):**

```bash
python -m benchassist.experiment_runner \
  --config configs/audit_experiment_mock_qa.yaml \
  --execute
```

**Run real Gemini audit (costs money — requires `GEMINI_API_KEY` in `.env`):**

```bash
python -m benchassist.experiment_runner \
  --config configs/audit_experiment_gemini_flash_lite.yaml \
  --execute
```

**Resume after interruption:**

```bash
python -m benchassist.experiment_runner \
  --config configs/audit_experiment_gemini_flash_lite.yaml \
  --execute \
  --resume
```

Experiment logs: `results/experiments/<experiment_name>/` (`command_plan.txt`, `execution_log.txt`, `cost_estimate.json`, `dry_run_summary.md`).

Configs: `configs/audit_experiment_gemini_flash_lite.yaml`, `configs/audit_experiment_mock_qa.yaml`.

---

## Preparing the submission package

After generating reports and tables, bundle documentation and key artefacts for submission:

```bash
python -m benchassist.final_report --auto
python -m benchassist.submission_package --auto
```

- Output directory: `results/submission_package/`
- Zip archive: `results/submission_package.zip`
- Reviewer entry point: `results/submission_package/README_FOR_REVIEWERS.md`
- File list: `results/submission_package/MANIFEST.json`

**Excluded by design:** `.env`, API keys, virtual environments, `__pycache__`, and pytest caches.

See also: `SUBMISSION_PACKAGE.md`, `PROJECT_OVERVIEW.md`, `LEGAL_EXPERT_RUNBOOK.md`, `DATA_DICTIONARY.md`.

**Not part of this project:** party-role/power-asymmetry audit; standalone interactive HTML report.

---

## QA and testing

See **[TESTING_REPORT.md](TESTING_REPORT.md)** for the full mock integration QA pass. Quick offline check:

```bash
pip install -e ".[dev]"
pytest -q
python -m benchassist.validate_data
python -m benchassist.pipeline --demo --limit 10 --output-suffix qa_demo
python -m benchassist.pipeline --status
```

---

## Additional Commands

| Command | Purpose |
|---------|---------|
| `python -m benchassist.pipeline --demo --limit 10 --output-suffix qa_demo` | Full mock audit chain (V2 metrics, validity, stereotype, qualitative, final report) |
| `python -m benchassist.pipeline --status` | List key artefact presence (no API calls) |
| `python -m benchassist.pipeline --print-real-run-plan` | Print suggested Gemini commands (does not run) |
| `python -m benchassist.validate_data` | Validate base/counterfactual CSVs |
| `python -m benchassist.stereotype_audit --outputs results/outputs/<run>.csv --output-suffix <suffix>` | Identity-leakage / stereotype screening |
| `python -m benchassist.qualitative_cases --outputs ... --pairwise ... --output-suffix <suffix>` | Extract qualitative review cases |
| `python -m benchassist.verify_pipeline` | Legacy V1 offline verifier |
| `python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode baseline --limit 5` | V2 baseline mock batch |
| `python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode fairness_aware --limit 5` | V2 fairness-aware mock batch |
| `python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs_v2_baseline.csv --output-suffix baseline` | V2 metrics (baseline suffix) |
| `python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode demographic_blind --limit 5` | V2 demographic-blind mock batch |
| `python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs_v2_demographic_blind.csv --output-suffix demographic_blind` | V2 metrics (demographic-blind suffix) |
| `python -m benchassist.stability_metrics --input results/outputs/model_outputs_v2_baseline.csv --output-suffix baseline` | Repeated-run stability metrics |
| `python -m benchassist.run_batch --provider mock --schema-version v2 --prompt-mode baseline --limit 5 --repetitions 3` | Repeated mock batch |
| `python -m benchassist.mitigation_comparison --baseline results/tables/v2_group_summary_baseline.csv --fairness-aware results/tables/v2_group_summary_fairness_aware.csv` | Compare mitigation |
| `python -m benchassist.data_generation --variant-set demographic` | Demographic variants only (default, 10/case) |
| `python -m benchassist.data_generation --variant-set language_access` | Language-access variants only (7/case) |
| `python -m benchassist.data_generation --variant-set intersectional` | Intersectional variants only (8/case) |
| `python -m benchassist.data_generation --variant-set narrative_framing` | Narrative-framing variants only (10/case) |
| `python -m benchassist.data_generation --variant-set all` | All variant families (35/case) |
| `benchassist audit-metrics --version v2 --input results/outputs/model_outputs.csv` | V2 legal-framing metrics (separate output files) |
| `python -m benchassist.audit_metrics --version v2 --input results/outputs/model_outputs.csv` | Same as above (module CLI) |
| `python -m benchassist.report` | Regenerate report and charts |
| `streamlit run app.py` | Interactive dashboard |
| `python -m benchassist.israeli_data --limit 100` | Optional HF sample (needs `.[datasets]`, internet) |
| `python -m pytest` | Run test suite |

**Optional Hugging Face background data:** [BrainboxAI/legal-training-il](https://huggingface.co/datasets/BrainboxAI/legal-training-il) — inspection only; audit cases remain synthetic.

---

## License

Course project — license TBD. Consult course staff before public release.
