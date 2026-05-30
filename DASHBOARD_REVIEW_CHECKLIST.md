# Dashboard review checklist (screenshots)

Use this before submitting or presenting the BenchAssist-IL audit. Capture screenshots from:

```bash
streamlit run app.py
```

Select the **Gemini Flash-Lite (pilot)** or your full Gemini run in the sidebar when available.

---

## 1. Overview

**What to check visually**

- Four warning badges: not legal advice, not an AI judge, synthetic setting, human review required.
- Run metadata: model, provider, prompt mode, schema, parse error rate.
- Headline metrics labeled **audit signal rates** (not “bias rate”).
- Short project description mentions Israeli housing and non-binding memos.

---

## 2. Main Audit Results

**What to check visually**

- Bar charts for key rates by `variant_type` (readable labels, not overcrowded).
- “How to read this” / glossary expander mentions screening + human review.
- Empty state shows a command hint if group summary is missing (not a crash).

---

## 3. Flagged Cases

**What to check visually**

- Table includes `review_priority`, `strongest_signal`, and validity category when available.
- Caption states severity is for review ordering, not discrimination findings.
- If automated flags are zero, **Flagged pairs only** unchecked shows review queue from pairwise data.

---

## 4. Case Explorer

**What to check visually**

- Side-by-side **Neutral** vs **Counterfactual variant** cards with Hebrew text readable.
- Difference summary table with **Concern?** column.
- Legal expert review questions listed.
- Optional stereotype / validity captions when data exists.

---

## 5. Counterfactual Validity

**What to check visually**

- Validity category counts and variant × category table.
- Interpretation expander explains strict vs language-access vs narrative stress tests.
- Sample rows show `fact_preservation_score` and `direct_bias_analysis_eligible`.

---

## 6. Stereotype & Identity Leakage

**What to check visually**

- Group summary table and flag-rate charts (or empty state with generate command).
- Interpretation box warns keywords are screening only.
- Flagged examples table if any flags exist.

---

## 7. Legal Grounding & Hallucination

**What to check visually**

- Group summary with invalid citation / unsupported claim rates.
- Interpretation states toy source base only — not Israeli law certification.
- High-risk examples table when present.

---

## 8. Statistical Uncertainty

**What to check visually**

- Confidence interval table with `small_sample_warning` visible for pilot-sized runs.
- Exploratory disclaimer (pilot too small for strong claims).
- Optional CI chart images if generated.

---

## 9. Reports & Exports

**What to check visually**

- Download buttons for review queue, group summary, human review template.
- Final audit report preview expander.
- Submission package `.zip` download if `results/submission_package.zip` exists.
- Submission checklist list at bottom.

---

## General

- Sidebar **Loaded files** expander shows sensible paths for the selected run.
- No API key or `.env` content visible anywhere.
- App does not reference party-role / power-asymmetry audit or standalone HTML report.
