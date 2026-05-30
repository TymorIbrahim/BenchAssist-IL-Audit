# Real Israeli Case-Inspired Data Card

## 1. Purpose

The **real-case-inspired layer** improves **realism** and **multi-domain coverage** for the BenchAssist-IL audit. It complements — but does not replace — the **synthetic controlled counterfactual audit**, which remains the primary source for strict demographic/language/narrative fairness measurement.

## 2. Source

**Preferred source:** [BrainboxAI/legal-training-il](https://huggingface.co/datasets/BrainboxAI/legal-training-il) (public/licensed training-evaluation material), when available locally or downloaded via Hugging Face.

**Also supported:** Local JSONL files in a Legal-Training-IL-like shape (see `tests/fixtures/legal_training_sample.jsonl`).

See source dataset card for license and terms. This project does not invent exact license language.

## 3. Domains (default demo)

| Normalized domain | Examples |
|-------------------|----------|
| `housing` | Landlord–tenant, repairs, eviction, rent, deposit, public housing |
| `labor_employment` | Dismissal, wages, notice, workplace rights |
| `social_benefits_welfare` | Disability benefits, national insurance, welfare eligibility |
| `immigration_status` | Visas, residency, asylum/tribunal, foreign workers |
| `consumer_small_claims` | Consumer transactions, contracts, small claims |
| `accessibility_disability_rights` | Accommodations, accessibility in services |

Family and criminal domains are intentionally **not** in the default demo (more sensitive/complex).

## 4. What this data is used for

- Multi-domain **coverage** and **external validity**
- **Real-case reliability** screening (actions, urgency, evidence burden, etc.)
- **Stereotype / identity leakage** audit (when run on real-case outputs)
- **Grounding / hallucination** audit (grounded V3 mode + multidomain knowledge base)
- **Qualitative legal review** and presentation realism

## 5. What this data is NOT used for (by default)

- **Strict demographic counterfactual bias rates** (reserved for synthetic controlled layer)
- **Proof of discrimination** or unlawful bias
- **Legal advice** or judicial decisions
- **Legal correctness certification**

Rows are tagged `dataset_mode=real_case_inspired`, `use_for_strict_bias_rates=false`, and `counterfactual_strength=not_counterfactual` (originals) or `approximate` (optional variants).

## 6. Privacy and redaction

- Obvious **emails**, **phone numbers**, **ID-like numbers**, and **possible names** are redacted with deterministic heuristics.
- Redaction is **not perfect** — human review is still required.
- Records may be flagged `contains_possible_personal_data=true` with `pii_redaction_notes`.

## 7. Limitations

- Source-derived summaries may be **incomplete** or **out of context**
- Domain distribution may be **imbalanced**
- **Legal correctness is not certified** — toy audit setting only
- Real cases contain **legally relevant differences**; not all are strict counterfactuals
- Not every example supports **counterfactual fairness claims**

## 8. Attribution

When Legal-Training-IL is used, preserve attribution metadata (`source_dataset`, `source_id`, `attribution_note`). See the Hugging Face dataset card for license and terms.

**Toy audit disclaimer:** Research audit only. Not legal advice. Not an AI judge. Human legal review required.
