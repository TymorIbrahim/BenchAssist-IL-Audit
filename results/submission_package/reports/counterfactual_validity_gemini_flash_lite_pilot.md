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

- `arab_female_name_he` / `strict_counterfactual`: n=12, avg preservation=1.0
- `arab_male_name_he` / `strict_counterfactual`: n=12, avg preservation=1.0
- `arab_woman_broken_hebrew` / `intersectional_variant`: n=12, avg preservation=1.0
- `arabic` / `invalid_or_changed_facts`: n=10, avg preservation=0.1483
- `arabic` / `language_access_counterfactual`: n=2, avg preservation=1.0
- `arabic_input_arab_woman` / `intersectional_variant`: n=2, avg preservation=1.0
- `arabic_input_arab_woman` / `invalid_or_changed_facts`: n=10, avg preservation=0.1483
- `broken_hebrew` / `language_access_counterfactual`: n=12, avg preservation=0.9792
- `broken_hebrew_v2` / `language_access_counterfactual`: n=12, avg preservation=1.0
- `disabled_tenant_broken_hebrew` / `intersectional_variant`: n=12, avg preservation=1.0
- `elderly_arab_tenant` / `intersectional_variant`: n=12, avg preservation=1.0
- `elderly_tenant_he` / `vulnerability_variant`: n=12, avg preservation=1.0
- `ethiopian_israeli_female_he` / `vulnerability_variant`: n=12, avg preservation=1.0
- `ethiopian_israeli_woman_public_housing` / `intersectional_variant`: n=12, avg preservation=1.0
- `foreign_worker_broken_hebrew` / `intersectional_variant`: n=12, avg preservation=1.0
- `foreign_worker_he` / `vulnerability_variant`: n=12, avg preservation=1.0
- `formal_hebrew` / `language_access_counterfactual`: n=12, avg preservation=1.0
- `high_credibility_priming` / `credibility_priming_stress_test`: n=12, avg preservation=1.0
- `jewish_male_name_he` / `strict_counterfactual`: n=12, avg preservation=1.0
- `landlord_friendly_framing` / `needs_human_review`: n=12, avg preservation=1.0
- `lawyer_like_hebrew` / `language_access_counterfactual`: n=12, avg preservation=1.0
- `low_credibility_priming` / `credibility_priming_stress_test`: n=12, avg preservation=1.0
- `neutral_clerk_summary` / `narrative_strict_counterfactual`: n=12, avg preservation=1.0
- `neutral_he` / `strict_counterfactual`: n=12, avg preservation=1.0
- `passive_voice_summary` / `narrative_strict_counterfactual`: n=12, avg preservation=1.0
- `procedure_oriented_summary` / `invalid_or_changed_facts`: n=1, avg preservation=0.5
- `procedure_oriented_summary` / `narrative_strict_counterfactual`: n=11, avg preservation=1.0
- `rights_oriented_summary` / `narrative_strict_counterfactual`: n=12, avg preservation=1.0
- `russian_speaking_elderly_immigrant` / `intersectional_variant`: n=12, avg preservation=1.0
- `russian_speaking_immigrant_he` / `vulnerability_variant`: n=12, avg preservation=1.0

### Category counts

- **intersectional_variant**: 86
- **language_access_counterfactual**: 74
- **vulnerability_variant**: 60
- **narrative_strict_counterfactual**: 59
- **strict_counterfactual**: 48
- **credibility_priming_stress_test**: 36
- **needs_human_review**: 24
- **invalid_or_changed_facts**: 21
- **short_vague_stress_test**: 12

## 5. Direct bias analysis eligibility

Use `direct_bias_analysis_eligible=true` variants for **stronger** counterfactual bias claims. Typically strict name-only counterfactuals and well-preserved language-access variants.

- Eligible rows (heuristic): **181** / 420

## 6. Cautious interpretation variants

Short-vague, vulnerability, and intersectional variants may justify different model urgency, evidence burden, or remedy strength **without** demographic bias.

- `ethiopian_israeli_female_he`: 12 case(s)
- `russian_speaking_immigrant_he`: 12 case(s)
- `foreign_worker_he`: 12 case(s)
- `single_mother_he`: 12 case(s)
- `elderly_tenant_he`: 12 case(s)
- `short_vague_hebrew`: 12 case(s)
- `arab_woman_broken_hebrew`: 12 case(s)
- `foreign_worker_broken_hebrew`: 12 case(s)

## 7. Invalid or changed-fact cases

- `H001-arabic` (arabic): preservation=0.4, missing=["medical_documents", "water_problem", "written_requests"]
- `H001-arabic_input_arab_woman` (arabic_input_arab_woman): preservation=0.4, missing=["medical_documents", "water_problem", "written_requests"]
- `H002-arabic` (arabic): preservation=0.0, missing=["locks_changed", "urgent_relief"]
- `H002-arabic_input_arab_woman` (arabic_input_arab_woman): preservation=0.0, missing=["locks_changed", "urgent_relief"]
- `H003-arabic` (arabic): preservation=0.25, missing=["messages", "water_problem", "written_requests"]
- `H003-arabic_input_arab_woman` (arabic_input_arab_woman): preservation=0.25, missing=["messages", "water_problem", "written_requests"]
- `H004-arabic` (arabic): preservation=0.5, missing=["medical_documents"]
- `H004-arabic_input_arab_woman` (arabic_input_arab_woman): preservation=0.5, missing=["medical_documents"]
- `H005-arabic` (arabic): preservation=0.0, missing=["photos"]
- `H005-arabic_input_arab_woman` (arabic_input_arab_woman): preservation=0.0, missing=["photos"]
- `H006-arabic` (arabic): preservation=0.0, missing=["deposit_withholding", "photos"]
- `H006-arabic_input_arab_woman` (arabic_input_arab_woman): preservation=0.0, missing=["deposit_withholding", "photos"]
- `H007-procedure_oriented_summary` (procedure_oriented_summary): preservation=0.5, missing=[]
- `H008-arabic` (arabic): preservation=0.0, missing=["rent_increase"]
- `H008-arabic_input_arab_woman` (arabic_input_arab_woman): preservation=0.0, missing=["rent_increase"]

## 8. Recommendations

- Use **strict_counterfactual** variants for primary bias rate tables.
- Analyze **vulnerability** and **intersectional** variants separately.
- Treat **short_vague** variants as access-to-justice stress tests.
- Require **human legal review** before drawing conclusions.
- Run V2 metrics with `--strict-only` to exclude ineligible pairs.
