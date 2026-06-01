# Address Variant Methodology — BenchAssist-IL Detention Audit

## Why address is included

Israeli detention/remand risk assessments may receive suspect residence information in case summaries. This audit adds **address proxy-cautious variants** to stress-test whether model dangerousness assessments remain stable when only the suspect's living address string changes while legally relevant facts are held constant.

## Why address is a proxy-cautious condition

An address string may correlate with geographic, demographic, or socioeconomic patterns in aggregate public data. It must **not** be treated as proof of an individual's ethnicity, religion, nationality, or socioeconomic status. Address effects observed in this audit are **audit signals** that require human legal review — not proof of unlawful discrimination.

## Why address variants are not proof of individual demographic identity

Each address record uses a **generic, manually curated, public geographic example** (street or neighborhood + locality). We do not attach addresses to real suspects, private individuals, or scraped personal databases. The audit metadata describes **aggregate geographic context labels** for analysis grouping only.

## How addresses were selected

- Manually curated from well-known public localities and generic street/neighborhood examples in Israel.
- Balanced set covering: affluent center, lower-SES periphery, Arab localities, mixed-city neighborhoods, Haredi areas, Ethiopian-Israeli concentration areas, Bedouin localities, rural cooperative settlements, development towns, and neutral large-city centers.
- Registry: `data/address_variants/israeli_address_variants.json`

## Why no private addresses are used

Private residential data could identify individuals and is inappropriate for synthetic audit research. All strings are generic examples suitable for geocodable public geography discussion, not tied to real people.

## Why no apartment numbers are used

Apartment-level detail increases re-identification risk without adding audit value. Address variants use street- or neighborhood-level strings only.

## How address variants are analyzed separately

- `counterfactual_strength`: `proxy_cautious_address`
- `protected_attribute_tested`: `address_proxy`
- `use_for_strict_bias_rates`: `false` by default
- `exclude_from_strict_bias_rates`: `true` by default
- Analysis bucket: `address_proxy_audit` (not headline strict demographic counterfactual rates)

Core synthetic demographic counterfactuals remain the **strict audit layer**. Address proxy variants are reported in a separate bucket.

## Why human legal review is required

Automated metrics (dangerousness shifts, address mentions in reasoning, unsupported inference flags) are screening signals only. A qualified legal reviewer must assess whether any pattern could reflect legitimate legal reasoning, data limitations, or model error — and must not treat audit outputs as adjudication or proof of discrimination.
