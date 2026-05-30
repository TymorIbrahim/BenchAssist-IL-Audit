# Data Dictionary

Practical reference for key audit files. Paths are relative to the project root.

---

## 1. Base cases

**File:** `data/processed/base_cases.csv` (and `base_cases.jsonl`)

| Column | Description |
|--------|-------------|
| `case_id` | Unique case identifier (e.g. `H001`). |
| `legal_area` | Domain label (typically `housing`). |
| `title` | Short case title. |
| `base_facts_he` | Canonical facts in Hebrew. |
| `base_facts_en` | Optional English summary. |
| `requested_remedy` | Relief sought by the petitioner. |
| `expected_urgency` | Ground-truth urgency: `low`, `medium`, or `high`. |
| `expected_direction` | Expected recommendation direction (e.g. grant/deny). |
| `source_note` | Provenance note (synthetic audit scenario). |

---

## 2. Counterfactual cases

**File:** `data/audit/counterfactual_cases.csv` (and `.jsonl`)

Optional family exports: `demographic_variants.csv`, `language_access_variants.csv`, `intersectional_variants.csv`, `narrative_framing_variants.csv`.

| Column | Description |
|--------|-------------|
| `case_id` | Links to base case. |
| `variant_id` | Unique id, usually `{case_id}-{variant_type}`. |
| `variant_type` | Perturbation type (e.g. `arab_male_name_he`, `broken_hebrew`, `neutral_clerk_summary`). |
| `demographic_cue` | Demographic or language cue label (`none` for narrative-only variants). |
| `language` | Input language code (`he`, `ar`, etc.). |
| `input_text` | Full text sent to the model. |
| `expected_urgency` | Should match base case. |
| `expected_direction` | Should match base case. |
| `transformation_style` | How the text was transformed (when set). |
| `strict_counterfactual_candidate` | Whether intended as strict factual counterfactual. |
| `framing_axis` | Narrative axis (e.g. `emotionality`, `credibility_priming`). |
| `framing_direction` | Narrative direction (e.g. `tenant_favorable`, `skeptical`). |

---

## 3. Model outputs

**Files:** `results/outputs/model_outputs_*.csv` (and `.jsonl`)

| Column | Description |
|--------|-------------|
| `run_id` | UUID for this generation. |
| `case_id` | Base case id. |
| `variant_id` | Counterfactual variant id. |
| `variant_type` | Variant type string. |
| `demographic_cue` | Demographic cue from input. |
| `language` | Input language. |
| `input_text` | Prompt input text. |
| `raw_output` | Raw model JSON/text. |
| `case_summary` | Parsed summary (V1/V2/V3). |
| `urgency` / `urgency_score` | Parsed urgency. |
| `recommended_action_type` | V2/V3 categorical action. |
| `remedy_strength_score` | V2/V3 integer 0–5. |
| `evidence_burden_level` / `evidence_burden_score` | Burden level or numeric score. |
| `party_credibility_framing` | supportive / neutral / skeptical. |
| `rights_orientation` / `rights_orientation_score` | Rights emphasis. |
| `procedural_posture` / `procedural_posture_score` | Procedural stance. |
| `reasoning_text` | Free-text reasoning (V2+). |
| `cited_source_ids` | V3 grounded citations. |
| `retrieved_source_ids` | V3 retrieved toy sources. |
| `legal_hallucination_risk` | V3 risk label. |
| `unsupported_legal_claims` | V3 flagged claims. |
| `schema_version` | `v1`, `v2`, or `v3`. |
| `prompt_mode` | `baseline`, `fairness_aware`, `demographic_blind`, `grounded`. |
| `model_name` | Model identifier. |
| `provider` | `mock`, `gemini`, or `openai`. |
| `timestamp` | Run timestamp (when recorded). |
| `parse_error` | Parsing error message, if any. |
| `repetition_index` | Repeat run index (stability batches). |

---

## 4. V2 pairwise comparisons

**Files:** `results/tables/v2_pairwise_comparison_*.csv`

Each row compares **one variant** to the **`neutral_he`** baseline for the same `case_id`.

| Column | Description |
|--------|-------------|
| `case_id` | Base case. |
| `variant_id` / `variant_type` | Variant compared. |
| `urgency_delta` | Variant minus neutral urgency score. |
| `remedy_strength_delta` | Variant minus neutral remedy score. |
| `evidence_burden_delta` | Variant minus neutral evidence burden. |
| `credibility_skepticism_delta` | Variant minus neutral credibility skepticism. |
| `rights_orientation_delta` | Variant minus neutral rights orientation. |
| `procedural_posture_delta` | Variant minus neutral procedural posture. |
| `action_type_flip` | Boolean: recommended action type changed. |
| `legal_framing_bias_flag` | True if any weakening/hardening flag triggered (screening). |
| `urgency_weaker`, `remedy_weaker`, etc. | Directional boolean flags. |

---

## 5. Group summaries

**Files:** `results/tables/v2_group_summary_*.csv`

Aggregated rates and mean deltas by `variant_type` (and `demographic_cue`), e.g. `legal_framing_bias_flag_rate`, `action_type_flip_rate`, `remedy_weaker_rate`.

---

## 6. Validity audit files

| File | Description |
|------|-------------|
| `counterfactual_validity_*.csv` | Per-variant validity category, fact preservation score, eligibility flags. |
| `counterfactual_validity_summary_*.csv` | Counts by variant type and category. |
| `counterfactual_validity_*.md` | Narrative validity report. |

Categories include `strict_counterfactual`, `language_access_counterfactual`, `narrative_strict_counterfactual`, `credibility_priming_stress_test`, `short_vague_stress_test`, `vulnerability_variant`, `invalid_or_changed_facts`, `needs_human_review`.

---

## 7. Stereotype audit files

| File | Description |
|------|-------------|
| `stereotype_audit_per_output_*.csv` | Per-output identity/stereotype flags. |
| `stereotype_audit_group_summary_*.csv` | Rates by variant group. |
| `stereotype_audit_flagged_examples_*.csv` | Sample flagged rows. |
| `stereotype_audit_*.md` | Screening report. |

---

## 8. Hallucination audit files (V3 grounded)

| File | Description |
|------|-------------|
| `hallucination_audit_per_output_*.csv` | Invalid citations, unsupported claims, risk scores. |
| `hallucination_audit_group_summary_*.csv` | Group aggregates. |
| `hallucination_audit_*.md` | Grounding/hallucination report. |

---

## 9. Statistical analysis files

| File | Description |
|------|-------------|
| `statistical_group_effects_*.csv` | Wilson/bootstrap intervals by variant. |
| `statistical_pairwise_tests_*.csv` | Exploratory paired tests. |
| `statistical_analysis_*.md` | Methods and caveats. |

---

## 10. Human-review files

| File | Description |
|------|-------------|
| `qualitative_case_studies_*.csv` | Cases selected for review with auto interpretations. |
| `human_review_template_*.csv` | Blank rubric columns for reviewers. |
| `human_review_summary.csv` | Aggregated completed reviews (after summarization). |
| `human_review_rubric.md` | Scoring instructions. |

---

## 11. Real-case-inspired layer files

| File | Description |
|------|-------------|
| `data/real_cases/raw_real_case_examples.jsonl` | Ingested source records (redacted summaries). |
| `data/real_cases/real_case_summaries.csv` / `.jsonl` | Normalized summaries with `real_case_id`, `normalized_domain`, PII flags. |
| `data/real_cases/real_case_domain_summary.csv` | Counts by domain. |
| `data/real_cases/real_case_bench_inputs.csv` | Bench-ready rows: `dataset_mode=real_case_inspired`, `use_for_strict_bias_rates=false`. |
| `data/real_cases/real_case_counterfactual_variants.csv` | Approximate variants (`counterfactual_strength=approximate`). |
| `real_case_audit_group_summary_*.csv` | Domain-level real-case audit aggregates. |
| `real_case_audit_per_output_*.csv` | Per-output real-case metrics. |
| `real_case_audit_*.md` | Real-case audit report. |
| `web_dashboard/public/data/real_case_*.json` | Vercel export for dashboard Real-Case section. |

Key columns: `dataset_mode`, `variant_type`, `counterfactual_strength`, `use_for_strict_bias_rates`, `use_for_reliability_audit`, `normalized_domain`, `source_note`, `attribution_note`.
