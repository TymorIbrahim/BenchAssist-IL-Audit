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

---

## Responsible AI Issue

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

**Counterfactual variant types (10 per base case):** `neutral_he`, Jewish/Arab names, Ethiopian-Israeli woman, Russian-speaking immigrant, foreign worker, single mother, elderly tenant, broken Hebrew, and related demographic cues.

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

# 3. Install the package (includes pytest, streamlit, etc.)
pip install -e '.[dev]'

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

## Interactive Dashboard

After the pipeline has produced `results/outputs/model_outputs.csv`:

```bash
streamlit run app.py
```

Sections: overview, group summary table, charts, side-by-side flagged-case comparison, searchable raw outputs. If files are missing, the app shows instructions to run `verify_pipeline` first.

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
│   ├── system_prompt.txt       # BenchAssist-IL system prompt
│   └── bench_memo_schema.json  # JSON output schema
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
│   ├── audit_metrics.py
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

## Additional Commands

| Command | Purpose |
|---------|---------|
| `python -m benchassist.verify_pipeline` | Full offline demo (recommended) |
| `python -m benchassist.run_batch --provider mock --limit 5` | Quick batch (5 cases) |
| `benchassist audit` | Recompute metrics from existing outputs |
| `python -m benchassist.report` | Regenerate report and charts |
| `streamlit run app.py` | Interactive dashboard |
| `python -m benchassist.israeli_data --limit 100` | Optional HF sample (needs `.[datasets]`, internet) |
| `python -m pytest` | Run test suite |

**Optional Hugging Face background data:** [BrainboxAI/legal-training-il](https://huggingface.co/datasets/BrainboxAI/legal-training-il) — inspection only; audit cases remain synthetic.

---

## License

Course project — license TBD. Consult course staff before public release.
