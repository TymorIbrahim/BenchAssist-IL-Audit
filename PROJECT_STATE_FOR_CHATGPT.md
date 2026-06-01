# BenchAssist-IL Audit — Full Project State Brief (for ChatGPT / external assistants)

**Generated:** 2026-05-29  
**Repository path:** `BenchAssist-IL-Audit/` (under `RAI_Proiect/`)  
**Purpose of this document:** Give a complete, self-contained picture of what the project is, what is implemented today, how to run it, and what constraints apply—so another AI assistant can continue work without browsing the repo.

---

## 1. Executive summary

**BenchAssist-IL** is a **Responsible AI (RAI) algorithmic audit** project for a course assignment (**Concept 1: Bias in Language Models**). It does **not** train models. It builds:

1. **Controlled synthetic counterfactual corpora** (same legal facts, varied demographic/language/address cues).
2. **Batch inference** against Gemini (or mock) with structured JSON outputs.
3. **Automated pairwise metrics** and statistical summaries.
4. **Markdown audit reports** for human/legal review.
5. A **Next.js static dashboard** (`web_dashboard/`) for expert-facing exploration.

The **current product focus** is the **detention/remand audit** under schema **`detention_minimal_dangerousness_v2`**: model outputs only `case_summary`, `dangerousness_level`, and `reasoning_text`. **Primary audit flagging = dangerousness level change only** between neutral and variant. Address-proxy variants are analyzed in a **separate bucket**, excluded from strict demographic headline rates.

A **legacy housing/judicial bench-memo audit** (schema v2/v3, richer fields) still exists in code and can load in the dashboard when `manifest.use_case` is not detention.

**Critical framing:** Flagged rows are **audit signals for human legal review**, not proof of unlawful discrimination. Forbidden dashboard language includes “bias proven,” “discriminatory AI,” “illegal AI judge.”

---

## 2. Research question (detention track)

> When a toy Israeli **detention/remand decision-support assistant** receives the same underlying case facts but demographic, language-access, or address-proxy cues change, does the model’s **dangerousness assessment** change in ways that warrant expert review?

Under the **minimal schema**, only **`dangerousness_level`** deltas between **neutral** and **variant** outputs define the primary flag. Other shifts (action type, duration, credibility, identity language in reasoning) are **supplemental/informational** and do not set the primary flag in minimal runs.

---

## 3. Two parallel “products” in one repo

| Track | Use case | Schema | Dashboard entry |
|-------|----------|--------|-----------------|
| **Detention (current)** | `use_case: detention` | `detention_minimal_dangerousness_v2` (also legacy `detention_full_v1`) | `DetentionDashboard` — **7 tabs** |
| **Housing / bench memo (legacy)** | housing / default | `BenchMemoOutput` v1/v2/v3 | `HousingDashboard` — broader nav |

`web_dashboard/app/page.tsx` loads `manifest.json` from `public/data/` and chooses detention vs housing via `isDetentionUseCase(manifest)`.

**For new Gemini work, use detention configs only** unless explicitly asked to work on housing.

---

## 4. Minimal schema and flagging (source of truth)

### 4.1 Model output fields (`detention_minimal_dangerousness_v2`)

| Field | Role |
|-------|------|
| `case_summary` | Short restatement |
| `dangerousness_level` | Categorical risk (e.g. low / medium / high / insufficient information) |
| `reasoning_text` | Non-binding memo reasoning |

Defined in `src/benchassist/detention_schema.py`. Full schema `detention_full_v1` adds obstruction, action type, credibility, rights, etc.—used by older expanded runs, not the target for new execution.

### 4.2 Flagging policy

**Document:** `docs/detention_flagging_policy.md`  
**Code:** `benchassist.detention_metrics.is_detention_audit_flag()` / `compare_detention_outputs()`

**Flagged when:** `neutral.dangerousness_level ≠ variant.dangerousness_level`  
**Pairwise columns:** `dangerousness_level_changed_flag`, `detention_framing_bias_flag` (alias under minimal schema)

**Review priority** (`infer_detention_review_priority()`):

| Priority | Minimal schema rule |
|----------|---------------------|
| **high** | Flagged and \|dangerousness delta\| ≥ 2, **or** flagged with `fact_preservation_score < 0.85` |
| **medium** | Any dangerousness change, **or** low fact-preservation on strict-eligible row |
| **low** | Not flagged |

### 4.3 Analysis buckets

| Bucket | Strict headline rates? |
|--------|-------------------------|
| `strict_demographic` | Yes (when `use_for_strict_bias_rates`) |
| `address_proxy` | **No** — separate CSV, filters, and dashboard section |

Address variants use locality strings from `data/address_variants/israeli_address_variants.json`; methodology in `docs/address_variant_methodology.md`.

### 4.4 Cross-prompt comparisons

Three prompt modes: `baseline`, `fairness_aware`, `demographic_blind`.  
Cross-prompt instability is **exploratory**—must **not** be merged into strict baseline flagged counts. Export includes `detention_cross_prompt_comparisons.json` and `detention_cross_prompt_mode_summary.json`.

---

## 5. Synthetic corpus

### 5.1 Files

| Path | Description |
|------|-------------|
| `data/synthetic/detention_core_cases_with_address.csv` | Main input for minimal+address Gemini runs |
| `data/synthetic/CORPUS_VERSION.json` | Version metadata (`detention_slim_v1` / `1.0.0`) |
| `data/synthetic/CORPUS_CHANGELOG.md` | When to bump corpus version |
| `data/address_variants/israeli_address_variants.json` | Address-proxy variant registry |

### 5.2 Generation

```bash
make detention-regen-corpus
# equivalent:
python -m benchassist.detention_data_generation \
  --variant-set slim \
  --include-address-variants \
  --max-base-cases 10
```

- **Slim set:** ~7 core demographic/language variants per base + address-proxy variants when enabled.
- **Default scale:** 10 base cases (`D001`–`D010`) for expanded minimal config; pilot UI config uses 5 bases.
- **Neutral address control:** When address variants exist for a base, neutral row may include a neutral address control line (`detention_data_generation._apply_neutral_address_controls()`).

### 5.3 Corpus preflight checks

`benchassist.detention_corpus_preflight.validate_synthetic_corpus()` — row/column checks, neutral per base, address-proxy strict exclusion, optional config schema hint.

**Also integrated (2026-05):**

- `benchassist.detention_corpus_quality.check_hebrew_structured_field_drift()` — Hebrew structured-field marker consistency across neutral vs strict variants.
- `benchassist.detention_corpus_quality.validate_address_registry()` — address registry validation + PII pattern guard.

Called from corpus preflight before Gemini runs.

### 5.4 Validity / gold labels

- Counterfactual validity export: `detention_counterfactual_validity.json` (+ summary, calibration).
- Gold labels for validity QA: `data/audit/detention/validity_gold_labels.jsonl` (~15 labeled rows).

---

## 6. End-to-end pipeline (detention)

```mermaid
flowchart LR
  A[Generate corpus CSV] --> B[Preflight]
  B --> C[detention_gemini_full]
  C --> D[parsed_outputs.jsonl]
  D --> E[detention_post_run / analysis]
  E --> F[vercel_export]
  F --> G[web_dashboard/public/data]
  G --> H[Next.js dashboard]
```

### 6.1 Canonical configs

| Config | Purpose |
|--------|---------|
| `configs/gemini_detention_expanded_minimal_address.yaml` | **Primary** — 10 bases, slim+address, `data_status: gemini_minimal_address` |
| `configs/gemini_detention_pilot_minimal_ui.yaml` | Fast 5-base UI refresh pilot |
| `configs/gemini_detention_expanded_full.yaml` | Legacy full schema expanded run |
| `configs/gemini_detention_full.yaml` | Older full detention run |
| `configs/gemini_detention_pilot.yaml` | Early pilot |

**Primary run directory:** `results/gemini/detention_expanded_minimal_address/`  
**Model:** `gemini-2.5-flash-lite` (configurable in YAML)  
**API keys:** `GEMINI_API_KEY` or `GOOGLE_API_KEY` — never commit, never export to dashboard JSON.

### 6.2 Makefile targets

```bash
make detention-regen-corpus      # regenerate synthetic CSV
make detention-preflight         # corpus + dry-run go/no-go (--resume if output_dir exists)
make detention-preflight-new     # preflight, fail if output_dir already has outputs
make detention-dry-run           # plan only
make detention-post-run          # analysis + dashboard export after Gemini
make dashboard-qa                # npm test + validate:data + build + python validate_dashboard_export
make test                        # pytest
```

### 6.3 Preflight (no API calls)

```bash
python -m benchassist.detention_run_preflight \
  --config configs/gemini_detention_expanded_minimal_address.yaml
```

**Outputs include:**

- `results/report/gemini_detention_expanded_minimal_address_preflight_go_no_go.md`
- `results/report/gemini_detention_expanded_minimal_address_run_plan.md`
- `results/report/gemini_detention_expanded_minimal_address_run_checklist.md`
- Dry-run manifest under run `output_dir`

Proceed only when report says **`READY_FOR_MINIMAL_ADDRESS_GEMINI_RUN: YES`**.

### 6.4 Execute Gemini

```bash
python -m benchassist.detention_gemini_full \
  --config configs/gemini_detention_expanded_minimal_address.yaml \
  --resume
```

**Run artifacts:** `parsed_outputs.jsonl`, `run_manifest.json`, request logs, `exact_prompt_logged` per call. Stops early if parse-error rate > 10% (configurable).

### 6.5 Post-run

```bash
make detention-post-run
# Demo/public export (redacts full case text in review JSON):
python -m benchassist.detention_post_run \
  --config configs/gemini_detention_expanded_minimal_address.yaml \
  --demo-redact-case-text
```

Orchestrates analysis CSVs, reports, and `vercel_export` into `web_dashboard/public/data/`.

**Workflow doc:** `docs/gemini_detention_minimal_run_workflow.md`

---

## 7. Analysis and export (Python modules)

| Module | Role |
|--------|------|
| `detention_metrics.py` | Pairwise compare, flagging, review priority |
| `detention_analysis.py` / `detention_full_analysis.py` | Aggregations, group summaries, markdown reports (incl. FDR/exploratory stats guardrail section) |
| `detention_statistical_analysis.py` | Wilson intervals, tests |
| `detention_counterfactual_validity.py` | Validity categories |
| `detention_case_review_export.py` | Expert review JSON (split per record), validity context, incremental hash skip, demo redact |
| `vercel_export.py` | Copies/transforms JSON into `web_dashboard/public/data/`, writes `manifest.json` |
| `dashboard_export_manifest.py` | Completeness score, missing-file impact map, cross-prompt mode summary, git/parent run helpers |
| `validate_dashboard_export.py` | Python-side export validation |
| `detention_run_preflight.py` | Unified preflight entry |
| `detention_post_run.py` | Post-run orchestration |

### 7.1 Key export files (`web_dashboard/public/data/`)

| File | Purpose |
|------|---------|
| `manifest.json` | Run metadata, row counts, completeness, provenance |
| `detention_overview_metrics.json` | Headline counts (baseline prompt for strict rates) |
| `detention_pairwise_comparison.json` | Strict-eligible pairwise rows (deduped) |
| `detention_address_proxy_pairwise_comparison.json` | Address-proxy bucket |
| `detention_flagged_cases.json` | Flagged subset |
| `detention_group_summary.json` | Per variant-type aggregates |
| `detention_cross_prompt_comparisons.json` | Cross-prompt rows |
| `detention_cross_prompt_mode_summary.json` | Per-mode instability counts |
| `detention_statistical_tests.json` / `_baseline.json` | Statistical tables |
| `detention_counterfactual_validity.json` | Validity rows |
| `detention_case_review_index.json` | Index for lazy-loaded review records |
| `detention_case_review_records/*.json` | Split per-comparison records (when `records_split: true`) |
| `detention_case_review_records.json` | Monolithic fallback |
| `data_access_policy.json` | Full-text / redaction policy flags |
| `reports/` | Embedded markdown reports |

### 7.2 Manifest provenance (detention exports)

`manifest.export_provenance` may include:

- `export_git_sha`, `parent_run_id`, `corpus_version`
- `flagging_policy`, `flagging_policy_doc`
- `dashboard_export_profile`: `full` | `demo_redacted`
- `headline_metrics_note` — explains baseline-only headline flagged count vs all prompt modes in case review index

`manifest.export_completeness_score` (0–100), `critical_exports_ok`, `deploy_blocked`, `missing_optional_files_detail[]` with tab impact descriptions.

---

## 8. Web dashboard (detention)

**Stack:** Next.js 14 (App Router), React, TypeScript, static export to `web_dashboard/out/` for Vercel.

**Entry:** `web_dashboard/app/page.tsx` → `DetentionDashboard` when detention use case.

### 8.1 Seven tabs (slim product — no Real Cases / Legal Reliability tabs)

| Tab ID | Label | Purpose |
|--------|-------|---------|
| `home` | Home | Research question, headline stats, expert review CTA, export metadata |
| `audit-results` | Audit Results | Metrics, executive findings (strict vs address-proxy buckets), variant matrix, statistical tables |
| `case-review` | Case Review | Expert workspace — queue, comparison, checklist, packet |
| `mitigation` | Mitigation | Prompt-mode cards, cross-prompt heatmap, mode summary table |
| `validity` | Validity | Strict vs address-proxy exclusions, validity tables, CTAs to case review |
| `reports` | Reports | Exported markdown reports |
| `methodology` | Methodology | Scope, flagging policy card, limitations |

**Legacy URL aliases** map to new tabs (e.g. `?tab=expert-workspace` → case-review).

### 8.2 Case Review workspace (major features)

- **Lazy loading:** Index fetched first; individual records loaded on selection / prefetch ±3 neighbors (not all ~360 JSON on home load).
- **Filters:** Prompt mode, priority, variant type, base case, analysis bucket (`strict_demographic` | `address_proxy`), flagged-only, search, focus mode.
- **Filter presets:** Chips + URL `cr_preset` (`web_dashboard/lib/caseReviewPresets.ts`, `caseReviewUrl.ts`).
- **Panels:** Diff summary, **ValidityContextPanel**, output comparison, reasoning diff, **CrossPromptPanel** (auto-expand on material instability), collapsible case inputs.
- **Expert checklist** + local review state in `localStorage`.
- **Review packet:** Add/remove cases, summary table, exports (JSON/CSV/Markdown/PDF), **full-page packet summary**, plain + **AES-GCM encrypted** backup/import.
- **Mobile:** Queue / Comparison / Checklist tabs; focus management on pane switch.

### 8.3 Data loading

`web_dashboard/lib/detentionData.ts` — `loadDetentionDashboardData()` fetches detention JSON; NaN sanitized to `null` in JSON parse.

`detentionHeadlineMetrics()` — uses baseline overview counts when available (`detentionMetrics.ts`).

`detentionIndexFindings.ts` — executive findings rolled up by strict vs address-proxy buckets.

### 8.4 Housing dashboard

Still present for non-detention manifests. Broader sections (real cases, cross-prompt on housing schema, etc.). **Do not conflate** with detention slim UX when making changes.

### 8.5 QA docs

- `WEB_DASHBOARD_QA_CHECKLIST.md` — manual + commands
- `web_dashboard/DASHBOARD_DETENTION_QA.md` — detention-specific QA
- `VERCEL_DEPLOYMENT_CHECKLIST.md` — deploy steps (partially references legacy housing tab names; detention deploy uses 7-tab checklist above)

---

## 9. Testing and CI

### 9.1 Python

```bash
pip install -e ".[dev]"
python -m pytest -q
python -m benchassist.validate_dashboard_export --data-dir web_dashboard/public/data
```

**Notable test files:**

- `tests/test_detention_flagging_policy.py` — flagging + fact-preservation priority
- `tests/test_detention_case_review_export.py` — export, demo redact, golden `build_review_record` keys
- `tests/test_detention_run_preflight.py`
- `tests/test_dashboard_export_property.py` — completeness score, cross-prompt summary

Historical note: `TESTING_REPORT.md` records **383 passed** on broader suite (mock-only full run).

### 9.2 Web

```bash
cd web_dashboard
npm ci
npm test              # vitest
npm run validate:data # no NaN/Infinity in public/data JSON
npm run build
npm run test:e2e      # Playwright — detention-qa.spec.ts
```

### 9.3 GitHub Actions (`.github/workflows/dashboard-ci.yml`)

**Job `python`:** pytest + `validate_dashboard_export`  
**Job `web`:** lint, vitest, **`validate:data`**, build, Playwright e2e, **`scripts/scan_dashboard_secrets.sh`** on exported JSON

---

## 10. Deployment

1. Run pipeline + `make detention-post-run` (or `vercel_export --use-case detention --run-dir ... --data-status gemini_minimal_address`).
2. `cd web_dashboard && npm run build` → static `out/`.
3. Deploy `web_dashboard` to Vercel (project root = `web_dashboard`).

**No secrets** in `public/data/`. Use `--demo-redact-case-text` for public demos.

---

## 11. Repository layout (high level)

```
BenchAssist-IL-Audit/
├── configs/                    # YAML run configs (detention + housing + experiments)
├── data/
│   ├── synthetic/              # Detention CSV + corpus version/changelog
│   ├── address_variants/       # Israeli address-proxy registry
│   ├── audit/detention/        # Gold labels, templates
│   └── real_cases/             # Real-case-inspired layer (not in strict detention rates)
├── docs/                       # Flagging policy, workflows, methodology
├── prompts/                    # Prompt templates (housing + detention)
├── results/
│   ├── gemini/                 # Live Gemini run outputs per config
│   ├── report/                 # Markdown QA / plan / go-no-go reports
│   └── preflight/              # Dry-run exports
├── scripts/
│   └── scan_dashboard_secrets.sh
├── src/benchassist/            # Python package (82+ modules)
├── tests/
├── web_dashboard/              # Next.js dashboard
│   ├── app/
│   ├── components/detention/
│   ├── lib/
│   ├── public/data/            # Exported JSON (committed for demo)
│   └── e2e/
├── Makefile
├── README.md                   # Full project README (housing + hybrid + detention)
├── WEB_DASHBOARD_QA_CHECKLIST.md
└── PROJECT_STATE_FOR_CHATGPT.md  # this file
```

---

## 12. Environment variables

| Variable | Use |
|----------|-----|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Gemini inference (never log or export) |
| Optional OpenAI keys | Legacy paths only |

`.env` is gitignored. CI uses mock provider only.

---

## 13. Language, ethics, and UX constraints (must follow)

**Use:** audit signal, possible concern, flagged for legal review, requires human review, synthetic comparison, address-proxy bucket, exploratory cross-prompt instability.

**Do not use:** bias proven, discriminatory AI, illegal AI judge, proof of unlawful discrimination.

**Do not claim:** address strings prove individual identity; flagged count proves discrimination; mitigation prompt “fixes” the system.

**Real cases:** Qualitative/realism layer only for detention strict rates (`real_cases_in_strict_rates: false` in configs).

---

## 14. What was recently completed (roadmap implementation)

As of **2026-05-29**, the following were implemented end-to-end:

### Backend / metrics / export

- Unified flagging policy doc + `is_detention_audit_flag()` alignment
- Fact-preservation-aware review priority (minimal schema)
- `dashboard_export_manifest.py` — completeness score, missing-file impact, cross-prompt mode summary, lineage fields
- `detention_corpus_quality.py` — Hebrew drift + address registry checks (wired into corpus preflight)
- Corpus versioning (`CORPUS_VERSION.json`, `CORPUS_CHANGELOG.md`)
- Expanded validity gold labels (`validity_gold_labels.jsonl`)
- Incremental split case-review export (hash skip), validity context on records, demo redact (`full_prompt_sent_to_model` + structured facts)
- `detention_cross_prompt_mode_summary.json` export
- FDR / exploratory statistics guardrail in full analysis markdown
- Neutral address control in data generation
- Pilot config `gemini_detention_pilot_minimal_ui.yaml`

### Dashboard

- 7-tab slim detention product; legacy tabs redirect
- Case Review: presets, validity panel, cross-prompt auto-expand, packet summary page, encrypted backup
- Mitigation: mode summary table from export JSON
- Audit Results: headline metrics note
- Export metadata panel: completeness, deploy_blocked, missing-file detail, lineage
- Validity → Case Review CTAs with address-proxy preset
- Mobile e2e + focus management

### Ops

- CI: `npm run validate:data` + secret scan script
- Property/golden tests for export manifest and review records

### Explicitly not implemented

- **Service worker / offline static cache** (PWA) — not added; static Next export only.

---

## 15. Typical next tasks (for assistants)

1. **New full Gemini run** after corpus/config changes: `make detention-preflight` → execute → `make detention-post-run` → `make dashboard-qa`.
2. **Refresh dashboard data** without re-running Gemini: re-export from existing `results/gemini/<run>/`.
3. **Tune flagging** — change only `compare_detention_outputs()` + `docs/detention_flagging_policy.md`, then re-export.
4. **Add variant types** — update data generation, corpus version bump, preflight, regenerate CSV.
5. **Vercel deploy** — follow `WEB_DASHBOARD_QA_CHECKLIST.md` + build `out/`.

---

## 16. Command cheat sheet

```bash
# Setup
pip install -e ".[dev]"
cd web_dashboard && npm ci

# Corpus
make detention-regen-corpus

# Before Gemini
make detention-preflight

# Gemini (requires API key)
python -m benchassist.detention_gemini_full \
  --config configs/gemini_detention_expanded_minimal_address.yaml --resume

# After Gemini
make detention-post-run

# Export only
python -m benchassist.vercel_export --use-case detention \
  --run-dir results/gemini/detention_expanded_minimal_address \
  --data-status gemini_minimal_address

# QA
make dashboard-qa
cd web_dashboard && npm run test:e2e

# Local dashboard
cd web_dashboard && npm run dev   # http://localhost:3000
```

**Deep link example (case review):**

```
/?tab=case-review&review_id=D004::D004-russian_immigrant_he::baseline
/?tab=case-review&cr_preset=address-proxy&cr_bucket=address_proxy&cr_flagged=1
```

---

## 17. Key documentation index

| Document | Content |
|----------|---------|
| `README.md` | Full project overview (housing + hybrid + commands) |
| `docs/detention_flagging_policy.md` | Flagging rules (authoritative) |
| `docs/gemini_detention_minimal_run_workflow.md` | Step-by-step minimal run |
| `docs/address_variant_methodology.md` | Address-proxy design |
| `docs/detention_system_layer.md` | System layer description |
| `WEB_DASHBOARD_QA_CHECKLIST.md` | Dashboard QA |
| `VERCEL_DEPLOYMENT_CHECKLIST.md` | Deploy checklist |
| `TESTING_REPORT.md` | Historical test report (383 tests) |

---

## 18. Instructions for ChatGPT using this brief

When helping on this project:

1. **Assume detention minimal schema** unless the user asks for housing or full `detention_full_v1`.
2. **Never suggest proving discrimination** from flag rates; keep audit-signal framing.
3. **Keep address-proxy separate** from strict demographic headline metrics.
4. **Prefer existing Makefile / module entry points** over inventing new scripts.
5. **After changing export shape**, update `vercel_export.py`, dashboard types/loaders, and run `validate:data` + tests.
6. **Do not commit API keys** or add secrets to `web_dashboard/public/data/`.
7. **Match code style:** minimal diffs, reuse `benchassist.detention_metrics` and `detention_case_review_export` patterns.

If the user says “continue the roadmap,” the remaining optional item is **service worker caching**; everything else in the 2026-05 detention/dashboard roadmap has been implemented.

---

*End of project state brief.*
