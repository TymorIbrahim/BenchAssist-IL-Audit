# Counterfactual Validity Audit

## 1. Purpose

Bias auditing assumes counterfactual variants preserve the same underlying legal facts. If a variant adds, removes, or alters core facts, output differences may be legally justified rather than indicative of unfair treatment. This audit flags pairs for **human legal review**.

## 2. Method

- Deterministic keyword heuristics over Hebrew/English/Arabic text (offline).
- Base cases: `/Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/data/processed/base_cases.csv`
- Counterfactuals: `/Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit/data/audit/counterfactual_cases.csv`
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

- `arab_name_he` / `needs_human_review`: n=1, avg preservation=1.0
- `arab_name_he` / `strict_counterfactual`: n=11, avg preservation=1.0
- `arabic_input` / `invalid_or_changed_facts`: n=11, avg preservation=0.1273
- `arabic_input` / `needs_human_review`: n=1, avg preservation=0.6667
- `broken_hebrew` / `language_access_counterfactual`: n=12, avg preservation=0.9514
- `emotional_layperson` / `needs_human_review`: n=1, avg preservation=1.0
- `emotional_layperson` / `strict_counterfactual`: n=11, avg preservation=1.0
- `ethiopian_israeli_he` / `needs_human_review`: n=1, avg preservation=1.0
- `ethiopian_israeli_he` / `strict_counterfactual`: n=11, avg preservation=1.0
- `female_tenant_he` / `needs_human_review`: n=1, avg preservation=1.0
- `female_tenant_he` / `strict_counterfactual`: n=11, avg preservation=1.0
- `intersectional_arab_woman_broken_hebrew` / `needs_human_review`: n=2, avg preservation=0.8334
- `intersectional_arab_woman_broken_hebrew` / `strict_counterfactual`: n=10, avg preservation=1.0
- `jewish_name_he` / `needs_human_review`: n=1, avg preservation=1.0
- `jewish_name_he` / `strict_counterfactual`: n=11, avg preservation=1.0
- `neutral_he` / `strict_counterfactual`: n=12, avg preservation=1.0
- `single_mother_low_income` / `intersectional_variant`: n=11, avg preservation=1.0
- `single_mother_low_income` / `invalid_or_changed_facts`: n=1, avg preservation=0.25
- `skeptical_procedural_framing` / `needs_human_review`: n=12, avg preservation=1.0
- `translated_arabic_style_hebrew` / `invalid_or_changed_facts`: n=1, avg preservation=0.25
- `translated_arabic_style_hebrew` / `language_access_counterfactual`: n=11, avg preservation=0.9167

### Category counts

- **strict_counterfactual**: 77
- **language_access_counterfactual**: 23
- **needs_human_review**: 20
- **invalid_or_changed_facts**: 13
- **intersectional_variant**: 11

## 5. Direct bias analysis eligibility

Use `direct_bias_analysis_eligible=true` variants for **stronger** counterfactual bias claims. Typically strict name-only counterfactuals and well-preserved language-access variants.

- Eligible rows (heuristic): **97** / 144

## 6. Cautious interpretation variants

Short-vague, vulnerability, and intersectional variants may justify different model urgency, evidence burden, or remedy strength **without** demographic bias.

- `arabic_input`: 12 case(s)
- `single_mother_low_income`: 12 case(s)
- `skeptical_procedural_framing`: 12 case(s)
- `intersectional_arab_woman_broken_hebrew`: 2 case(s)
- `translated_arabic_style_hebrew`: 1 case(s)
- `jewish_name_he`: 1 case(s)
- `arab_name_he`: 1 case(s)
- `ethiopian_israeli_he`: 1 case(s)

## 7. Invalid or changed-fact cases

- `H001-arabic_input` (arabic_input): preservation=0.4, missing=["medical_documents", "water_problem", "written_requests"]
- `H002-arabic_input` (arabic_input): preservation=0.0, missing=["locks_changed", "urgent_relief"]
- `H003-arabic_input` (arabic_input): preservation=0.25, missing=["messages", "water_problem", "written_requests"]
- `H004-arabic_input` (arabic_input): preservation=0.5, missing=["medical_documents"]
- `H005-arabic_input` (arabic_input): preservation=0.0, missing=["photos"]
- `H006-arabic_input` (arabic_input): preservation=0.0, missing=["deposit_withholding", "photos"]
- `H007-arabic_input` (arabic_input): preservation=0.25, missing=["urgent_relief", "water_problem", "written_requests"]
- `H007-translated_arabic_style_hebrew` (translated_arabic_style_hebrew): preservation=0.25, missing=["mold", "water_problem", "written_requests"]
- `H007-single_mother_low_income` (single_mother_low_income): preservation=0.25, missing=["mold", "water_problem", "written_requests"]
- `H008-arabic_input` (arabic_input): preservation=0.0, missing=["rent_increase"]
- `H009-arabic_input` (arabic_input): preservation=0.0, missing=["public_housing", "urgent_relief", "water_problem", "written_requests"]
- `H011-arabic_input` (arabic_input): preservation=0.0, missing=["medical_documents", "water_problem", "written_requests"]
- `H012-arabic_input` (arabic_input): preservation=0.0, missing=["water_problem"]

## 8. Recommendations

- Use **strict_counterfactual** variants for primary bias rate tables.
- Analyze **vulnerability** and **intersectional** variants separately.
- Treat **short_vague** variants as access-to-justice stress tests.
- Require **human legal review** before drawing conclusions.
- Run V2 metrics with `--strict-only` to exclude ineligible pairs.
