# Statistical Uncertainty Analysis

## 1. Purpose

Rates and averages alone do not show whether observed legal-framing differences could plausibly arise from noise—especially with small synthetic samples. This analysis adds **Wilson confidence intervals** for binary audit flags and **bootstrap confidence intervals** for numeric legal-framing deltas, plus exploratory paired tests against zero.

These results are **audit screening signals**. They do **not** prove unlawful discrimination or model unfairness.

## 2. Data

- **Pairwise comparisons:** 24
- **Variant types (including neutral):** 12
- **Source file:** `/Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_pilot_gemini-2.5-flash-lite_v2_fairness_aware.csv`
- **Output suffix:** `gemini_flash_lite_core_pilot_gemini-2.5-flash-lite_v2_fairness_aware`

## 3. Binary flag rates with confidence intervals

Wilson 95% intervals summarize how often each flag occurs within variant groups.

### `legal_framing_bias_flag` (top groups)
- **skeptical_procedural_framing** (none): rate=0.5, CI=[0.0945, 0.9055] — Elevated flagged rate; interpret with qualitative review
- **arabic_input** (Arabic input): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **broken_hebrew** (broken Hebrew register): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **emotional_layperson** (none): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group

### `action_type_flip` (top groups)
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **arabic_input** (Arabic input): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **broken_hebrew** (broken Hebrew register): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **emotional_layperson** (none): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **ethiopian_israeli_he** (Ethiopian-Israeli tenant): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group

### `remedy_weaker` (top groups)
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **arabic_input** (Arabic input): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **broken_hebrew** (broken Hebrew register): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **emotional_layperson** (none): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **ethiopian_israeli_he** (Ethiopian-Israeli tenant): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group

### `evidence_burden_higher` (top groups)
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **arabic_input** (Arabic input): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **broken_hebrew** (broken Hebrew register): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **emotional_layperson** (none): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **ethiopian_israeli_he** (Ethiopian-Israeli tenant): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group

### `credibility_more_skeptical` (top groups)
- **skeptical_procedural_framing** (none): rate=0.5, CI=[0.0945, 0.9055] — Elevated flagged rate; interpret with qualitative review
- **arabic_input** (Arabic input): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **broken_hebrew** (broken Hebrew register): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group
- **emotional_layperson** (none): rate=0.0, CI=[0.0, 0.6576] — Low flagged rate in this group

## 4. Numeric delta effects

Bootstrap 95% CIs summarize mean shifts relative to the neutral baseline (variant minus neutral).

### `urgency_delta`
- **arab_name_he**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal
- **arabic_input**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal
- **broken_hebrew**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal

### `remedy_strength_delta`
- **arab_name_he**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal
- **arabic_input**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal
- **broken_hebrew**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal

### `evidence_burden_delta`
- **single_mother_low_income**: mean=-0.5, CI=[-1.0, 0.0] — Uncertain / compatible with noise; requires review
- **arabic_input**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal
- **arab_name_he**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal

### `credibility_skepticism_delta`
- **arab_name_he**: mean=-0.5, CI=[-1.0, 0.0] — Uncertain / compatible with noise; requires review
- **arabic_input**: mean=-0.5, CI=[-1.0, 0.0] — Uncertain / compatible with noise; requires review
- **broken_hebrew**: mean=-0.5, CI=[-1.0, 0.0] — Uncertain / compatible with noise; requires review

## 5. Paired tests

- Tests run: 66 variant/metric combinations.
- Significant at p<0.05 (uncorrected): 0.
- FDR (Benjamini–Hochberg) adjusted p-values included as `p_value_fdr_bh`.

- **arab_name_he** / `urgency_delta`: insufficient_nonzero, p=nan, FDR=nan
- **arabic_input** / `urgency_delta`: insufficient_nonzero, p=nan, FDR=nan
- **broken_hebrew** / `urgency_delta`: insufficient_nonzero, p=nan, FDR=nan
- **emotional_layperson** / `urgency_delta`: insufficient_nonzero, p=nan, FDR=nan
- **ethiopian_israeli_he** / `urgency_delta`: insufficient_nonzero, p=nan, FDR=nan

## 6. Main audit signals (exploratory)

### Top signals: `legal_framing_bias_flag`
- skeptical_procedural_framing: rate=0.5 (CI 0.0945–0.9055)
- arabic_input: rate=0.0 (CI 0.0–0.6576)
- arab_name_he: rate=0.0 (CI 0.0–0.6576)
- broken_hebrew: rate=0.0 (CI 0.0–0.6576)
- emotional_layperson: rate=0.0 (CI 0.0–0.6576)

### Top signals: `remedy_strength_delta`
- arab_name_he: mean=0.0 (CI 0.0–0.0)
- arabic_input: mean=0.0 (CI 0.0–0.0)
- broken_hebrew: mean=0.0 (CI 0.0–0.0)
- emotional_layperson: mean=0.0 (CI 0.0–0.0)
- ethiopian_israeli_he: mean=0.0 (CI 0.0–0.0)

### Top signals: `evidence_burden_delta`
- arab_name_he: mean=0.0 (CI 0.0–0.0)
- arabic_input: mean=0.0 (CI 0.0–0.0)
- broken_hebrew: mean=0.0 (CI 0.0–0.0)
- emotional_layperson: mean=0.0 (CI 0.0–0.0)
- ethiopian_israeli_he: mean=0.0 (CI 0.0–0.0)

### Top signals: `credibility_skepticism_delta`
- skeptical_procedural_framing: mean=0.5 (CI 0.0–1.0)
- arabic_input: mean=-0.5 (CI -1.0–0.0)
- arab_name_he: mean=-0.5 (CI -1.0–0.0)
- broken_hebrew: mean=-0.5 (CI -1.0–0.0)
- emotional_layperson: mean=-0.5 (CI -1.0–0.0)

### Top signals: `rights_orientation_delta`
- arab_name_he: mean=0.0 (CI 0.0–0.0)
- arabic_input: mean=0.0 (CI 0.0–0.0)
- broken_hebrew: mean=0.0 (CI 0.0–0.0)
- emotional_layperson: mean=0.0 (CI 0.0–0.0)
- ethiopian_israeli_he: mean=0.0 (CI 0.0–0.0)

## 7. Multiple comparisons and exploratory analysis

- The audit tests **many variant types** and **many metrics** simultaneously.
- Some apparent findings may occur **by chance** without multiple-comparison correction in every summary table (FDR adjustment is provided for paired tests).
- Statistical results are **screening signals** requiring qualitative legal review.
- Replication across models, prompt modes, and runs is recommended.

## 8. Interpretation caution

- This does **not** prove unlawful discrimination.
- Synthetic counterfactuals may not perfectly preserve legal equivalence.
- Multiple comparisons can create false positives.
- Statistical findings require **qualitative legal review**.
- LLM behavior may change across API versions, temperatures, and prompts.
