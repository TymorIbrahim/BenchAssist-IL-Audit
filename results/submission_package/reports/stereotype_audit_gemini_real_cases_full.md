# Stereotype and Identity-Leakage Audit

Deterministic keyword screening of model **outputs** vs inputs. This is **not** proof of discrimination; human legal review is required.

## Purpose

Detect whether reasoning or summaries introduce identity categories, stereotype language, or generalizations not supported by the case text.

## Aggregate results

| variant_type | demographic_cue | n_outputs | stereotype_audit_flag_rate | identity_leakage_flag_rate |
| --- | --- | --- | --- | --- |
| real_case_original | none | 16 | 0.000 | 0.000 |

## Flagged examples (sample)

_No flagged rows in this run (or empty input)._

## Limitations

- Keyword lists miss context and may false-positive on legally relevant facts.
- Absence of flags does not prove fairness.
- Hebrew/Arabic morphology is only partially covered.

_Suffix: `gemini_real_cases_full`_
