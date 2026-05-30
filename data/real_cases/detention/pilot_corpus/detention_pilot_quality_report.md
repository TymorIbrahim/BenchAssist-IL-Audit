# Detention Pilot Corpus Quality Report

**Generated:** 2026-05-30T11:03:17.726925+00:00

## Summary

- Candidate rows by source: {'source_candidates_brainboxai': 200, 'source_candidates_local': 8, 'source_candidates_sample_expanded': 15}
- Total candidates after dedupe: 223
- Detention-relevant (score ≥ 2): 164
- Selected pilot rows: 80
- Sensitive-flagged (review file): 80
- Duplicates removed: 0

## Stage distribution (selected)

- `unclear`: 24
- `dangerousness`: 23
- `weak_evidence_dispute`: 11
- `release_with_conditions`: 10
- `pre_indictment_arrest_extension`: 4
- `detention_appeal`: 4
- `post_indictment_remand`: 2
- `obstruction_risk`: 2

## Top matched keywords

- `מסוכנות`: 88
- `מ"י`: 36
- `ראיות לכאורה`: 25
- `הארכת מעצר`: 24
- `פיקוח`: 23
- `חלופת מעצר`: 16
- `חשד סביר`: 16
- `עילת מעצר`: 15
- `בש"פ`: 8
- `מעצר ימים`: 8

## Limitations

- This is a **real-case-inspired qualitative corpus**, not a counterfactual fairness dataset.
- It **must not** be used for strict demographic bias rates.
- **Legal-expert review** is required before model runs or dashboard deployment.
- Full text is preserved without redaction for **internal expert review only**.
- Do not deploy full-text exports without access control.
