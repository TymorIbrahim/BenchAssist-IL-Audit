# Counterfactual Validity Audit

## 1. Purpose

Bias auditing assumes counterfactual variants preserve the same underlying legal facts. If a variant adds, removes, or alters core facts, output differences may be legally justified rather than indicative of unfair treatment. This audit flags pairs for **human legal review**.

## 2. Method

- Deterministic keyword heuristics over Hebrew/English/Arabic text (offline).
- Base cases: `data/processed/base_cases.csv`
- Counterfactuals: `data/real_cases/real_case_counterfactual_variants.csv`
- When base CSV text does not match case IDs, neutral `neutral_he` inputs are used as fallback.
- **Not legally authoritative**; does not replace expert review.

## 3. Validity categories

| Category | Meaning |
|----------|---------|
| strict_counterfactual | Name/demographic cue change; facts appear preserved |
| language_access_counterfactual | Language style change; facts intended preserved |
| short_vague_stress_test | Intentionally less detail; access-to-justice stress test |
| vulnerability_variant | May add legally relevant vulnerability |
| intersectional_variant | Multiple cues; careful review required |
| invalid_or_changed_facts | Material fact mismatch vs base |
| needs_human_review | Heuristic uncertain |
| narrative_strict_counterfactual | Narrative style change; facts appear preserved |
| credibility_priming_stress_test | Credibility/skepticism priming stress test |

## 4. Summary results

- `arab_name` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `arabic_translation_style_hebrew` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `broken_hebrew_if_hebrew` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `emotional_layperson` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `formal_legal_language` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `jewish_name` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `neutralized_names` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `procedural_clerk_summary` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan
- `real_case_original` / `real_case_original_not_counterfactual`: n=16, avg preservation=nan
- `simple_language` / `real_case_approximate_counterfactual`: n=16, avg preservation=nan

### Category counts

- **real_case_approximate_counterfactual**: 144
- **real_case_original_not_counterfactual**: 16

## 5. Direct bias analysis eligibility

Use `direct_bias_analysis_eligible=true` variants for **stronger** counterfactual bias claims. Typically strict name-only counterfactuals and well-preserved language-access variants.

- Eligible rows (heuristic): **0** / 160

## 6. Cautious interpretation variants

Short-vague, vulnerability, and intersectional variants may justify different model urgency, evidence burden, or remedy strength **without** demographic bias.

- `real_case_original`: 16 case(s)
- `neutralized_names`: 16 case(s)
- `arab_name`: 16 case(s)
- `jewish_name`: 16 case(s)
- `broken_hebrew_if_hebrew`: 16 case(s)
- `simple_language`: 16 case(s)
- `formal_legal_language`: 16 case(s)
- `arabic_translation_style_hebrew`: 16 case(s)

## 7. Invalid or changed-fact cases

_None flagged at heuristic threshold._

## 8. Recommendations

- Use **strict_counterfactual** variants for primary bias rate tables.
- Analyze **vulnerability** and **intersectional** variants separately.
- Treat **short_vague** variants as access-to-justice stress tests.
- Require **human legal review** before drawing conclusions.
- Run V2 metrics with `--strict-only` to exclude ineligible pairs.
