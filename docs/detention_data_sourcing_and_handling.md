# Detention / Remand Data Sourcing and Handling

This document describes the **data-preparation layer** for a potential pivot from housing bench-memo audit to **Israeli criminal detention-extension / remand-risk support**.

The project is conducted **in collaboration with legal experts and law professors**. Real Israeli legal material is intended for **internal expert review only**.

This layer does **not** change prompts, output schemas, or dashboard behavior yet.

---

## Collaboration and internal review policy

Legal experts need to see **full public legal material without redaction** in the internal research environment. Therefore:

- **`full_internal` mode** preserves source text exactly (`no_redaction_applied=true`).
- **`redaction_policy`** = `no_redaction_internal_expert_review`.
- **`data_visibility`** = `internal_full_text`.

Redaction is **not** applied silently in internal mode.

---

## Why URL secrecy is not enough

Even when material is publicly available:

- A Vercel URL is **not** access control.
- Search engines, link sharing, and screenshots can expose content.
- Public legal text may still implicate privacy, minors, or publication bans.

If the dashboard exports full unredacted text, treat deployment as **internal/restricted** and require authentication (e.g. Vercel password protection, SSO, or private network).

See `web_dashboard/data_access_policy.json`.

---

## Internal dashboard vs public/submission export

| Mode | Full text | Intended audience |
|------|-----------|-------------------|
| `full_internal` | Yes, unredacted | Legal experts / law professors (access-controlled) |
| `public_summary` | No — excerpts + references only | Course submission / demo if approved |

**Public data ≠ unrestricted redistribution.** Always verify license and publication status.

---

## Methodology (mandatory metadata)

All real-case-inspired rows include:

| Field | Value |
|-------|-------|
| `dataset_mode` | `real_case_inspired` |
| `counterfactual_strength` | `not_counterfactual` |
| `use_for_strict_bias_rates` | `false` |
| `exclude_from_strict_bias_rates` | `true` |
| `use_for_reliability_audit` | `true` |
| `manual_review_required` | `true` |
| `data_visibility` | `internal_full_text` (internal mode) |

Real detention/remand cases are **not** strict counterfactuals.

---

## Allowed uses

1. **Legal grounding** — statute and Kol Zchut references
2. **Project motivation** — comptroller / judicial-authority background
3. **Qualitative reliability audit** — after system pivot, with expert review
4. **Internal expert dashboard** — full text for professors and legal reviewers

---

## Forbidden uses

- Strict proof of demographic bias or unlawful discrimination
- Automated legal advice or remand recommendations without human review
- Unrestricted public redistribution of full case text
- Model inputs from **sensitive-flagged** rows without explicit legal approval
- Treating “public” as “safe to publish anywhere”

---

## Sensitive-content handling

Keywords flag minors, sex offenses, security/terror, administrative detention, sealed matters, etc.

**Sensitive rows are not deleted.** They are:

- flagged in `detention_sensitive_flagged_for_review.csv`
- excluded from **model bench inputs** by default (`include_in_model_inputs=false`)
- optionally preserved in internal inventory for expert review

---

## Source registry

File: `data/legal_sources/detention_sources.json`

Each source includes `full_text_allowed_internal`, `public_export_allowed`, and `requires_manual_review_before_dashboard`.

---

## Local fixture workflow

```bash
python -m benchassist.detention_fulltext_prepare \
  --input tests/fixtures/detention_public_sample.jsonl \
  --output-dir data/real_cases/detention \
  --max-examples 50 \
  --data-mode full_internal
```

Outputs under `data/real_cases/detention/`:

- `raw_real_detention_examples_fulltext.jsonl`
- `detention_case_summaries_fulltext.csv` / `.jsonl`
- `detention_bench_inputs_fulltext.csv` (non-sensitive model-input candidates only)
- `detention_sensitive_flagged_for_review.csv`
- `detention_data_handling_manifest.json`

---

## Public/submission export

```bash
python -m benchassist.detention_fulltext_prepare \
  --input data/real_cases/detention/raw_real_detention_examples_fulltext.jsonl \
  --output-dir data/real_cases/detention_public_export \
  --data-mode public_summary
```

Full raw text is **excluded**. Only source references, titles, and short excerpts are included.

---

## Optional Hugging Face workflow

Requires `pip install datasets` and network. Tests do **not** require HF.

```bash
python -m benchassist.detention_fulltext_prepare \
  --source huggingface \
  --dataset BrainboxAI/legal-training-il \
  --output-dir data/real_cases/detention \
  --max-examples 50 \
  --data-mode full_internal
```

If unavailable, the CLI completes with a clear note and zero HF rows.

---

## Manual public court decision workflow

1. Collect **public** decisions only; respect publication restrictions.
2. Create JSONL with `source_id`, `title`, `text`, `url`, `language`, `publication_status`.
3. Run `full_internal` preparation.
4. Legal experts review `detention_sensitive_flagged_for_review.csv`.
5. Deploy dashboard only behind access control if exporting full text.

---

## Vercel export safety

`vercel_export --auto` copies `data_access_policy.json` and prints a warning when full-text detention data may be present.

**Do not deploy** a full-text dashboard to a public URL without access control and legal sign-off.

---

## Legacy redaction module

`detention_redaction.py` remains for optional non-internal workflows. The **full-text internal path does not use it**.

---

## Human legal review

Required before:

- model batch runs on real detention examples
- dashboard deployment with full text
- any public release beyond `public_summary` mode
