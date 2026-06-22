# Detention Full Gemini Analysis Report

Generated: 2026-06-22T19:42:57.823231+00:00

**Audit signals only — not proof of unlawful discrimination. Requires human legal review.**

## Scope

- Total outputs: 6187
- Parse success rate: 96.5%
- Strict-eligible synthetic outputs: 2893
- Strict-excluded synthetic outputs: 3080
- Real-case-inspired qualitative outputs: 240
- Real cases in strict rates: **No**

## Cross-prompt screening

- Cross-prompt comparison rows: 3889
- Material instability flags (dangerousness change): 2266
- Wording-only changes (informational): 0

## Statistical screening (exploratory)

- Wilson 95% confidence intervals and Benjamini–Hochberg FDR q-values in `detention_statistical_tests*.csv` are **exploratory** screening aids across variant groups.
- They are **not** adjusted for all comparisons in a publication sense and **must not** be read as proof of discrimination or legal liability.
- Primary audit signal for the minimal schema remains **dangerousness_level** change on strict counterfactual pairs.

## Outputs

- `detention_pairwise_comparison.csv`
- `detention_group_summary.csv`
- `detention_flagged_cases.csv`
- `detention_strict_excluded_review_outputs.csv`
- `detention_real_case_inspired_review_outputs.csv`
- `detention_address_proxy_pairwise_comparison.csv`
- `detention_cross_prompt_comparisons.csv`
- `detention_statistical_tests.csv`
- `detention_statistical_tests_baseline.csv`
- `detention_full_metric_summary.json`

Full-run audit signals may indicate possible concerns requiring human review. Not proof of unlawful discrimination. Real-case rows excluded from strict rates.