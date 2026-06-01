# BenchAssist-IL Detention Dashboard QA Checklist

Manual QA for the **slim** expert-facing detention audit dashboard (7 tabs, minimal dangerousness schema).

## Build & runtime

- [ ] `cd web_dashboard && npm install` succeeds
- [ ] `npm run lint` passes
- [ ] `npm run build` passes
- [ ] `npm test` passes (vitest unit tests)
- [ ] `npm run validate:data` passes (no literal `NaN` in export JSON)
- [ ] `npm run test:e2e` passes (Playwright; requires build first)
- [ ] `npm run dev` → http://localhost:3000 loads without console errors
- [ ] No Python backend, `.env`, or API keys required at runtime
- [ ] From repo root: `make dashboard-qa` and `python -m benchassist.validate_dashboard_export --data-dir web_dashboard/public/data`

## Information architecture (7 tabs)

- [ ] **Home** — research story, readiness, **Start expert review**, export metadata & provenance (git commit, flagging policy when exported)
- [ ] **Audit Results** — dangerousness-focused metrics, executive findings, variant matrix, address-proxy bucket callouts
- [ ] **Case Review** — queue, comparison, checklist, packet summary, cross-prompt strip, prefetch on navigation
- [ ] **Mitigation** — prompt mode cards and cross-prompt heatmap (or clear empty state)
- [ ] **Validity** — strict vs address-proxy; CTAs open Case Review with filters
- [ ] **Reports** — search, filter, Markdown render, download
- [ ] **Methodology** — flagging policy card, minimal schema, limitations
- [ ] Legacy tab URLs redirect (e.g. `overview` → Home, `findings` → Audit Results, `expert-workspace` → Case Review)
- [ ] URL updates on tab / review selection (`?tab=case-review&review_id=…`); does **not** change on scroll alone

## Removed / out of scope (slim product)

- [ ] No **Real Cases** tab or full-text source browser in this build
- [ ] No **Legal Reliability** tab (identity/grounding tables were housing-era / full-schema)
- [ ] No **Run Comparison** or **Identity Audit** legacy panels

## Safety & disclaimers

- [ ] **SafetyContextBar** chips visible (research only, not legal advice)
- [ ] No forbidden conclusion language (“bias proven”, “discriminatory”, “illegal”, etc.)
- [ ] Status strip shows data mode and access posture
- [ ] Full-text deployments require access control; demo export uses `--demo-redact-case-text`

## Home

- [ ] Hero, research question, audit method diagram
- [ ] Export metadata panel: row counts, dedupe note, optional `flagging_policy` / `dashboard_export_profile`
- [ ] **Start expert review** opens Case Review with focus + first high-priority flagged case

## Audit Results

- [ ] Summary cards and takeaways reflect **dangerousness** as primary signal
- [ ] “Review these cases” / matrix **Open in Case Review** set `review_id` and filters
- [ ] Address-proxy metrics labeled separately from strict demographic rates

## Case Review Workspace

- [ ] `detention_case_review_index.json` on first load; split records lazy-loaded
- [ ] Deep link `?review_id=` loads single record without blocking on full queue
- [ ] Adjacent queue records prefetched (±3) when browsing
- [ ] Quick filters: flagged only, high priority, strict demographic, address proxy, unreviewed
- [ ] Audit signal (dangerousness Δ) prominent; fact-preservation callout on diffs
- [ ] **Cross-prompt dangerousness strip** when multi-mode export present
- [ ] **Packet panel** summary table + open-in-review actions
- [ ] Hebrew case titles use correct `dir` when RTL
- [ ] Checklist, local notes, packet export (JSON/CSV/Markdown)
- [ ] Keyboard ↑/↓ or j/k for queue navigation
- [ ] Empty state shows export command when data missing

## Mitigation & Validity

- [ ] Mitigation heatmap or empty state with export hint
- [ ] Validity page buttons open Case Review with `flaggedOnly` / `analysisBucket` presets

## Reports & Methodology

- [ ] Reports searchable and downloadable
- [ ] Methodology documents dangerousness-only flagging and links to `docs/detention_flagging_policy.md`

## Performance

- [ ] Initial load does **not** fetch all split review JSON files
- [ ] Tab panels and charts code-split (`next/dynamic`)
- [ ] Manifest fetched once from server (`initialManifest` on dashboard shell)

## Commands

```bash
# Full export (expert review with case text):
python -m benchassist.vercel_export --use-case detention \
  --run-dir results/gemini/detention_expanded_minimal_address \
  --data-status gemini_minimal_address

# Public demo preview (omits full case text in review JSON):
python -m benchassist.vercel_export --use-case detention \
  --run-dir results/gemini/detention_expanded_minimal_address \
  --data-status gemini_minimal_address \
  --demo-redact-case-text

cd web_dashboard && npm install && npm test && npm run validate:data && npm run build && npm run test:e2e
python -m pytest tests/test_detention_flagging_policy.py tests/test_detention_case_review_export.py -q
```

## Known limitations

- Flagging is **dangerousness_level change only** for minimal schema exports
- Cross-prompt panel needs multi-mode outputs in export
- Review notes and packet state are browser-local only
- Existing Gemini runs may show reconstructed prompts until runner logs exact prompts

## Ready for legal-expert review?

After this checklist passes on a **full** export (not demo-redacted): **Yes** — deploy only behind access control when case text is included.
