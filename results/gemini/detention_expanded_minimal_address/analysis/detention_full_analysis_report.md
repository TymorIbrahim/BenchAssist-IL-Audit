# Detention Full Gemini Analysis Report

Generated: 2026-06-01T22:24:26.037755+00:00

**Audit signals only — not proof of unlawful discrimination. Requires human legal review.**

## Scope

- Total outputs: 6721
- Parse success rate: 99.7%
- Strict-eligible synthetic outputs: 2872
- Strict-excluded synthetic outputs: 3831
- Real-case-inspired qualitative outputs: 0
- Real cases in strict rates: **No**

## Cross-prompt screening

- Cross-prompt comparison rows: 4460
- Material instability flags (dangerousness change): 383
- Wording-only changes (informational): 4077

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