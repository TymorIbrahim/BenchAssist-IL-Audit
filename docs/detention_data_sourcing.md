# Detention / Remand Data Sourcing

This document describes the **data-preparation layer** for a potential pivot from housing bench-memo audit to **Israeli criminal detention-extension / remand-risk support**.

This layer is **separate** from the current production audit path. It does not change prompts, schemas, or dashboard behavior yet.

---

## Why real detention cases are sensitive

Israeli detention and remand proceedings involve:

- liberty restrictions before and during trial
- prosecution declarations and evidentiary thresholds (`חשד סביר`, `ראיות לכאורה`)
- risk framing (dangerousness, witness tampering, flight)
- parties who may be identifiable even in public decisions

Real cases are **not clean counterfactuals**. Legally relevant differences (charge stage, evidence, risk claims) make strict demographic bias comparisons inappropriate.

---

## Methodology (mandatory metadata)

All prepared real-case-inspired rows must have:

| Field | Value |
|-------|-------|
| `dataset_mode` | `real_case_inspired` |
| `counterfactual_strength` | `not_counterfactual` |
| `use_for_strict_bias_rates` | `false` |
| `exclude_from_strict_bias_rates` | `true` |
| `use_for_reliability_audit` | `true` |
| `manual_review_required` | `true` |

**Forbidden use:** strict proof of demographic bias or unlawful discrimination.

---

## Allowed uses

1. **Legal grounding** — statutes and plain-language references (e.g. arrest law, Kol Zchut)
2. **Project motivation / context** — comptroller and judicial-authority background material
3. **Real-case-inspired qualitative audit** — reliability, stereotype screening, grounding review (after pivot)

---

## Source registry

Registry file: `data/legal_sources/detention_sources.json`

Source types:

| Type | Examples |
|------|----------|
| `legal_grounding` | Criminal Procedure Law (Arrests) 1996; Kol Zchut detention pages |
| `background_statistics` | State Comptroller detention report; Judicial Authority arrests study |
| `real_case_inspired` | Legal-Training-IL; Supreme Court HF dataset; manual public decisions |

Load in Python:

```python
from benchassist.detention_sources import load_detention_sources
sources = load_detention_sources()
```

---

## Local fixture workflow (recommended offline)

```bash
python -m benchassist.detention_real_case_prepare \
  --input tests/fixtures/detention_public_sample.jsonl \
  --output-dir data/real_cases/detention \
  --max-examples 50
```

Outputs:

- `raw_real_detention_examples.jsonl`
- `detention_case_summaries.csv` / `.jsonl`
- `detention_bench_inputs.csv`
- `detention_domain_summary.csv`
- `detention_excluded_sensitive.csv`
- `detention_source_manifest.json`

Sensitive rows (minors, sex offenses, security/terror, etc.) are **marked and excluded** from bench inputs — not silently deleted.

---

## Hugging Face optional workflow

Requires `pip install datasets` and network access. Tests do **not** require HF.

```bash
python -m benchassist.detention_real_case_prepare \
  --source huggingface \
  --dataset BrainboxAI/legal-training-il \
  --output-dir data/real_cases/detention \
  --max-examples 50
```

```bash
python -m benchassist.detention_real_case_prepare \
  --source huggingface \
  --dataset LevMuchnik/SupremeCourtOfIsrael \
  --output-dir data/real_cases/detention \
  --max-examples 50
```

If dependencies or network are missing, the CLI completes with a clear note and zero HF rows (no crash in tests).

---

## Manual public court decision workflow

1. Collect **public** decisions only; respect publication restrictions.
2. Create JSONL rows:

```json
{
  "source_dataset": "manual_public_court_decision",
  "source_id": "sample_001",
  "title": "...",
  "text": "...",
  "url": "...",
  "language": "he"
}
```

3. Run the preparation CLI on your JSONL.
4. Review `detention_excluded_sensitive.csv` and redaction notes.
5. Human legal review before any model batch or publication.

---

## Filtering

Inclusion keywords (Hebrew): `מעצר ימים`, `הארכת מעצר`, `מעצר עד תום ההליכים`, `חשד סביר`, `ראיות לכאורה`, `עילת מעצר`, `מסוכנות`, `שיבוש הליכי חקירה`, and related terms.

Exclusion keywords mark sensitive categories: minors, sex offenses, security/terror, administrative detention, sealed family matters, publication bans.

Module: `benchassist.detention_source_filters`

---

## Redaction limitations

Module: `benchassist.detention_redaction`

Redacts/heuristically masks: emails, phones, ID-like numbers, URLs, address hints, optional case-number hashing, party names when configured.

**Disclaimer:** *Automatic lightweight redaction only; manual review is required before publication or model use.*

Redaction is **not** complete anonymization.

---

## Human legal review requirement

Before using prepared detention examples in model audits or sharing externally:

- verify source license and publication status
- review excluded-sensitive file
- confirm redaction adequacy
- do not treat outputs as legal advice or discrimination proof

---

## Next steps (not implemented yet)

The following are **out of scope** for this data layer:

- changing bench-memo prompts or V2/V3 schemas
- dashboard pivot
- Gemini batch runs
- strict counterfactual variant generation for detention

When ready to pivot the system, start from `detention_bench_inputs.csv` and extend knowledge-base / domain taxonomy separately.
