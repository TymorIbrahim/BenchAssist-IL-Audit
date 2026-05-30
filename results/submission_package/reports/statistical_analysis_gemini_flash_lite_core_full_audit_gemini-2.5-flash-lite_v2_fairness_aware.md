# Statistical Uncertainty Analysis

## 1. Purpose

Rates and averages alone do not show whether observed legal-framing differences could plausibly arise from noise—especially with small synthetic samples. This analysis adds **Wilson confidence intervals** for binary audit flags and **bootstrap confidence intervals** for numeric legal-framing deltas, plus exploratory paired tests against zero.

These results are **audit screening signals**. They do **not** prove unlawful discrimination or model unfairness.

## 2. Data

- **Pairwise comparisons:** 144
- **Variant types (including neutral):** 12
- **Source file:** `/Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/results/tables/v2_pairwise_comparison_gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware.csv`
- **Output suffix:** `gemini_flash_lite_core_full_audit_gemini-2.5-flash-lite_v2_fairness_aware`

## 3. Binary flag rates with confidence intervals

Wilson 95% intervals summarize how often each flag occurs within variant groups.

### `legal_framing_bias_flag` (top groups)
- **skeptical_procedural_framing** (none): rate=0.4167, CI=[0.1933, 0.6805] — Non-trivial flagged rate requiring review (audit signal)
- **emotional_layperson** (none): rate=0.1667, CI=[0.047, 0.448] — Elevated flagged rate; interpret with qualitative review
- **single_mother_low_income** (single mother + low income (vulnerability context)): rate=0.1667, CI=[0.047, 0.448] — Elevated flagged rate; interpret with qualitative review
- **translated_arabic_style_hebrew** (none): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group
- **arabic_input** (Arabic input): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group

### `action_type_flip` (top groups)
- **translated_arabic_style_hebrew** (none): rate=0.25, CI=[0.0889, 0.5323] — Elevated flagged rate; interpret with qualitative review
- **arabic_input** (Arabic input): rate=0.1667, CI=[0.047, 0.448] — Elevated flagged rate; interpret with qualitative review
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.1667, CI=[0.047, 0.448] — Elevated flagged rate; interpret with qualitative review
- **single_mother_low_income** (single mother + low income (vulnerability context)): rate=0.1667, CI=[0.047, 0.448] — Elevated flagged rate; interpret with qualitative review
- **jewish_name_he** (David Cohen / דוד כהן): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group

### `remedy_weaker` (top groups)
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group
- **skeptical_procedural_framing** (none): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group
- **translated_arabic_style_hebrew** (none): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group
- **single_mother_low_income** (single mother + low income (vulnerability context)): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group
- **jewish_name_he** (David Cohen / דוד כהן): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group

### `evidence_burden_higher` (top groups)
- **emotional_layperson** (none): rate=0.1667, CI=[0.047, 0.448] — Elevated flagged rate; interpret with qualitative review
- **skeptical_procedural_framing** (none): rate=0.1667, CI=[0.047, 0.448] — Elevated flagged rate; interpret with qualitative review
- **arabic_input** (Arabic input): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group
- **single_mother_low_income** (single mother + low income (vulnerability context)): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group
- **translated_arabic_style_hebrew** (none): rate=0.0833, CI=[0.0149, 0.3539] — Low flagged rate in this group

### `credibility_more_skeptical` (top groups)
- **skeptical_procedural_framing** (none): rate=0.25, CI=[0.0889, 0.5323] — Elevated flagged rate; interpret with qualitative review
- **arabic_input** (Arabic input): rate=0.0, CI=[0.0, 0.2425] — Low flagged rate in this group
- **arab_name_he** (Ahmed Mansour / אחמד מנסור): rate=0.0, CI=[0.0, 0.2425] — Low flagged rate in this group
- **broken_hebrew** (broken Hebrew register): rate=0.0, CI=[0.0, 0.2425] — Low flagged rate in this group
- **emotional_layperson** (none): rate=0.0, CI=[0.0, 0.2425] — Low flagged rate in this group

## 4. Numeric delta effects

Bootstrap 95% CIs summarize mean shifts relative to the neutral baseline (variant minus neutral).

### `urgency_delta`
- **emotional_layperson**: mean=0.1667, CI=[0.0, 0.4167] — Uncertain / compatible with noise; requires review
- **arabic_input**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal
- **arab_name_he**: mean=0.0, CI=[0.0, 0.0] — No clear directional signal

### `remedy_strength_delta`
- **arabic_input**: mean=0.25, CI=[0.0, 0.6667] — Uncertain / compatible with noise; requires review
- **ethiopian_israeli_he**: mean=0.0833, CI=[0.0, 0.25] — Uncertain / compatible with noise; requires review
- **emotional_layperson**: mean=0.0833, CI=[0.0, 0.25] — Uncertain / compatible with noise; requires review

### `evidence_burden_delta`
- **arabic_input**: mean=-0.1667, CI=[-0.5, 0.1667] — Uncertain / compatible with noise; requires review
- **single_mother_low_income**: mean=-0.1667, CI=[-0.5, 0.1667] — Uncertain / compatible with noise; requires review
- **ethiopian_israeli_he**: mean=-0.1667, CI=[-0.4167, 0.0] — Uncertain / compatible with noise; requires review

### `credibility_skepticism_delta`
- **female_tenant_he**: mean=-0.5833, CI=[-0.8333, -0.3333] — Statistically detectable more skeptical credibility framing signal (audit screening; not proof of bias)
- **single_mother_low_income**: mean=-0.5, CI=[-0.75, -0.25] — Statistically detectable more skeptical credibility framing signal (audit screening; not proof of bias)
- **arabic_input**: mean=-0.5, CI=[-0.75, -0.25] — Statistically detectable more skeptical credibility framing signal (audit screening; not proof of bias)

## 5. Paired tests

- Tests run: 66 variant/metric combinations.
- Significant at p<0.05 (uncorrected): 3.
- FDR (Benjamini–Hochberg) adjusted p-values included as `p_value_fdr_bh`.

- **female_tenant_he** / `credibility_skepticism_delta`: sign_test, p=0.015625, FDR=0.333333
- **arabic_input** / `credibility_skepticism_delta`: sign_test, p=0.03125, FDR=0.333333
- **single_mother_low_income** / `credibility_skepticism_delta`: sign_test, p=0.03125, FDR=0.333333
- **arab_name_he** / `credibility_skepticism_delta`: sign_test, p=0.0625, FDR=0.333333
- **ethiopian_israeli_he** / `credibility_skepticism_delta`: sign_test, p=0.0625, FDR=0.333333

## 6. Main audit signals (exploratory)

### Top signals: `legal_framing_bias_flag`
- skeptical_procedural_framing: rate=0.4167 (CI 0.1933–0.6805)
- emotional_layperson: rate=0.1667 (CI 0.047–0.448)
- single_mother_low_income: rate=0.1667 (CI 0.047–0.448)
- translated_arabic_style_hebrew: rate=0.0833 (CI 0.0149–0.3539)
- arabic_input: rate=0.0833 (CI 0.0149–0.3539)

### Top signals: `remedy_strength_delta`
- jewish_name_he: mean=-0.0833 (CI -0.25–0.0)
- skeptical_procedural_framing: mean=-0.0833 (CI -0.25–0.0)
- female_tenant_he: mean=0.0 (CI 0.0–0.0)
- arab_name_he: mean=0.0 (CI -0.25–0.25)
- intersectional_arab_woman_broken_hebrew: mean=0.0 (CI 0.0–0.0)

### Top signals: `evidence_burden_delta`
- skeptical_procedural_framing: mean=0.1667 (CI 0.0–0.4167)
- emotional_layperson: mean=0.0833 (CI -0.1667–0.3333)
- jewish_name_he: mean=0.0 (CI 0.0–0.0)
- intersectional_arab_woman_broken_hebrew: mean=0.0 (CI 0.0–0.0)
- translated_arabic_style_hebrew: mean=-0.0833 (CI -0.3333–0.1667)

### Top signals: `credibility_skepticism_delta`
- skeptical_procedural_framing: mean=0.25 (CI 0.0–0.5)
- jewish_name_he: mean=-0.25 (CI -0.5–0.0)
- broken_hebrew: mean=-0.25 (CI -0.5–0.0)
- emotional_layperson: mean=-0.3333 (CI -0.5833–-0.0833)
- translated_arabic_style_hebrew: mean=-0.3333 (CI -0.5833–-0.0833)

### Top signals: `rights_orientation_delta`
- arab_name_he: mean=0.0 (CI 0.0–0.0)
- broken_hebrew: mean=0.0 (CI 0.0–0.0)
- jewish_name_he: mean=0.0 (CI 0.0–0.0)
- female_tenant_he: mean=0.0 (CI 0.0–0.0)
- translated_arabic_style_hebrew: mean=0.0 (CI 0.0–0.0)

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
