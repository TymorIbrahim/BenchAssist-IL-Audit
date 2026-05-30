# Detention Pilot Corpus (Sprint 2)

Build the first real Israeli detention/remand **pilot corpus** from public legal sources for internal legal-expert review.

---

## Policy

- **Internal mode:** full public legal text preserved with **no redaction**
- **Access control required** if exported to Vercel — do not rely on URL secrecy
- **Real-case rows excluded** from strict synthetic fairness rates
- **Legal-expert approval** required before model runs or dashboard deployment

---

## Source plan

| Priority | Source | Method |
|----------|--------|--------|
| 1 | `BrainboxAI/legal-training-il` | Hugging Face (optional) |
| 2 | `LevMuchnik/SupremeCourtOfIsrael` | Hugging Face (optional) |
| 3 | `data/manual_sources/detention_manual_public_cases.jsonl` | Local JSONL |
| 4 | Background/grounding in `data/legal_sources/detention_sources.json` | Reference only |

Do **not** scrape Net HaMishpat or paid databases automatically.

---

## Commands

### Step 1 — Ingest candidates

**Local manual cases:**
```bash
python -m benchassist.detention_source_ingest \
  --source local_jsonl \
  --input data/manual_sources/detention_manual_public_cases.jsonl \
  --output data/real_cases/detention/source_candidates_local.jsonl \
  --max-examples 200
```

**Hugging Face (optional, graceful if unavailable):**
```bash
python -m benchassist.detention_source_ingest \
  --source huggingface \
  --dataset BrainboxAI/legal-training-il \
  --output data/real_cases/detention/source_candidates_brainboxai.jsonl \
  --max-examples 200

python -m benchassist.detention_source_ingest \
  --source huggingface \
  --dataset LevMuchnik/SupremeCourtOfIsrael \
  --output data/real_cases/detention/source_candidates_supreme_court.jsonl \
  --max-examples 200
```

For general legal HF datasets, scan more rows and keep only detention/remand matches:

```bash
python -m benchassist.detention_source_ingest \
  --source huggingface \
  --dataset BrainboxAI/legal-training-il \
  --output data/real_cases/detention/source_candidates_brainboxai.jsonl \
  --max-examples 200 \
  --scan-limit 25000 \
  --filter-detention \
  --min-detention-score 1
```

If HF loading fails, a `*.failure_manifest.json` is written next to the output path and the CLI exits gracefully (no crash).

**Note:** `LevMuchnik/SupremeCourtOfIsrael` is blocked from automatic HF ingest (large parquet download). Add manually curated public Supreme Court decisions to `data/manual_sources/detention_manual_public_cases.jsonl` instead.

### Step 2 — Build pilot corpus

```bash
python -m benchassist.detention_pilot_corpus \
  --candidates \
    data/real_cases/detention/source_candidates_brainboxai.jsonl \
    data/real_cases/detention/source_candidates_supreme_court.jsonl \
    data/real_cases/detention/source_candidates_local.jsonl \
  --output-dir data/real_cases/detention/pilot_corpus \
  --target-size 80 \
  --min-relevance-score 2 \
  --data-mode full_internal
```

### Step 3 — Review quality report

```bash
open data/real_cases/detention/pilot_corpus/detention_pilot_quality_report.md
open data/real_cases/detention/pilot_corpus/detention_pilot_sensitive_review.csv
```

---

## Adding manual public decisions

1. Collect **public** court decisions only (respect publication bans).
2. Add JSONL rows to `data/manual_sources/detention_manual_public_cases.jsonl`:

```json
{
  "source_dataset": "manual_public_court_decision",
  "source_id": "unique_id",
  "title": "...",
  "text": "...",
  "url": "https://...",
  "language": "he",
  "publication_status": "public"
}
```

3. Re-run ingestion and pilot corpus build.

---

## Expert review workflow

Each pilot row includes:

| Field | Default |
|-------|---------|
| `expert_review_status` | `not_reviewed` |
| `expert_approved_for_model_input` | `false` |
| `expert_approved_for_dashboard` | `false` |
| `expert_approved_for_submission_excerpt` | `false` |

Law professors should:

1. Review `detention_pilot_sensitive_review.csv` first
2. Approve/reject rows in summaries CSV
3. Only then allow model-input or dashboard use

---

## Real-case limitations

- Not a counterfactual fairness dataset
- Must **not** be used for strict demographic bias rates
- Legally relevant differences between cases make causal bias claims inappropriate
- Not legal advice; not certified legal correctness

---

## Vercel export

When pilot full-text exists, `vercel_export --auto` includes:

- `detention_pilot_examples_fulltext.json`
- `detention_pilot_quality_report.json`
- `detention_pilot_source_manifest.json`
- `data_access_policy.json`

A warning is printed:

> Full unredacted legal text is being exported for internal expert review. Deploy only behind access control. Do not rely on URL secrecy.

---

## See also

- [detention_data_sourcing_and_handling.md](detention_data_sourcing_and_handling.md)
