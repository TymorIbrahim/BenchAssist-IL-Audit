# Narrative-Framing Robustness Audit

## 1. Purpose

This audit tests whether **the same legal facts** receive different structured legal-framing treatment when the case summary is phrased in different narrative styles. It complements demographic and language-access counterfactual audits.

## 2. Why narrative framing matters in judge-facing LLMs

Bench memos influence perceived urgency, remedy strength, evidence burden, and credibility. Irrelevant differences in tone, emotionality, or party-sympathetic wording should not systematically shift those fields when underlying facts are unchanged.

## 3. Variant types

Ten deterministic narrative variants per base case:

- `neutral_clerk_summary`
- `tenant_emotional_layperson`
- `skeptical_clerk_summary`
- `tenant_friendly_framing`
- `landlord_friendly_framing`
- `passive_voice_summary`
- `rights_oriented_summary`
- `procedure_oriented_summary`
- `low_credibility_priming`
- `high_credibility_priming`

## 4. Strict vs stress-test variants

- **narrative_strict_counterfactual**: style change with high heuristic fact preservation.
- **credibility_priming_stress_test**: intentional skepticism/support priming; not a strict factual counterfactual.
- Party-sympathy and emotional variants may require **human legal review** even when facts appear preserved.

## 5. Aggregate results

_No narrative variant rows found in the pairwise input._

## 6. Strongest framing effects


## 7. Credibility priming results

_No low vs high credibility cross-pair data in this run._

## 8. Party-sympathy framing results


## 9. Emotionality and layperson framing


## 10. Limitations

- Narrative framing effects are **not** the same as demographic discrimination.
- Stress-test variants reveal **sensitivity** to framing, not necessarily unfairness.
- Pairwise rows may be compared to `neutral_he` demographic baseline depending on the batch design; interpret cross-variant tables for narrative-only contrasts.
- Heuristic fact-preservation does not replace human legal review.

## 11. Recommendations

- Review flagged cases with a legally trained reviewer.
- Separate strict narrative counterfactual rates from credibility-priming stress tests.
- Consider prompt instructions that anchor on documented facts and procedural posture.
- Do not treat screening metrics as findings of judicial bias.

_Report suffix: `qa_mock`_
