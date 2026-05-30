# Vercel Deployment Checklist — BenchAssist-IL Audit Dashboard

Use this checklist before sharing the dashboard with team members, legal experts, or course reviewers.

## Pre-export

- [ ] Run full (or latest preferred) audit pipeline
- [ ] Generate final Markdown reports under `results/report/`
- [ ] Confirm no secrets in report text or exported paths

## Export

- [ ] `python -m benchassist.vercel_export --auto`
- [ ] Verify JSON in `web_dashboard/public/data/`
- [ ] Check `manifest.json` for correct run label, model, and row counts
- [ ] Check `manifest.json` for `cross_prompt_comparisons_available` and `prompt_modes_detected`
- [ ] Check `manifest.json` for `dataset_modes_available`, `real_case_domains_available`, `real_case_row_count`
- [ ] Verify `real_case_audit_summary.json`, `real_case_audit_outputs.json`, `real_case_domain_summary.json`, `real_case_examples.json` exist when real-case runs present

## Build & review locally

- [ ] `cd web_dashboard && npm install && npm run build`
- [ ] `npm run dev` — open http://localhost:3000
- [ ] Disclaimer banner visible on every page load
- [ ] **Executive overview** — title, subtitle, trust badges, reviewer path, audience guide
- [ ] **Key takeaways** — cautious plain-language cards from exported data
- [ ] **Explore by concern** — legal-concern cards filter Flagged Cases
- [ ] **Guided review** — steps, mark reviewed, localStorage progress
- [ ] **Presentation mode** — toggle, 5-minute path, presentation panel
- [ ] **Share link** — Case Explorer copy link; Flagged Cases filtered view link
- [ ] **Deep link** — `?section=case-explorer&case_id=…` loads case state
- [ ] **Main Findings** — storytelling cards, metric selector, chart → flagged cases
- [ ] **Flagged Cases** — review queue, priority explanation, issue tags, reviewer packet
- [ ] **Case Explorer** — comparison modes, reviewer guidance, What changed, reviewer packet
- [ ] **Baseline vs fairness-aware** comparison works, or empty state is clear
- [ ] **Baseline vs demographic-blind** comparison works, or empty state is clear
- [ ] **Cross-prompt summary** in Mitigation when multiple prompt modes exported
- [ ] **Share link** URL does not change while scrolling (only filters/case/metric/mode)
- [ ] **Glossary drawer** — opens from toolbar
- [ ] **Reports** — categories, reading order, download
- [ ] **Methodology** — limitations present; hybrid synthetic vs real-case methodology visible
- [ ] **Real Israeli Case-Inspired Audit** — domain cards, example table, safety signals, limitation callout (separate from strict synthetic bias cards)
- [ ] Test filter reset, active chips, and result counts
- [ ] **Data transparency** panel shows export metadata
- [ ] **Methodology & limitations** — readable scope cards
- [ ] **Mobile layout** — sidebar stacks, horizontal table scroll, nav usable
- [ ] **No secrets** in exported JSON or dashboard source
- [ ] **No** active `party_power` / `power_asymmetry` dashboard sections
- [ ] **Flagged Cases Actions column** is not duplicated (Copy JSON off by default)
- [ ] Verify mobile/responsive layout (sidebar, horizontal table scroll)

## Deploy

- [ ] `vercel` (preview) — share preview URL internally first
- [ ] `vercel --prod` (production) when ready
- [ ] Send link to team with reminder: research audit only, not legal advice

## Post-deploy

- [ ] Loaded run panel shows expected model and export timestamp
- [ ] Hebrew/Arabic text displays correctly in Case Explorer
- [ ] Empty sections show helpful empty states (not errors)

## Refresh workflow

After new audit results:

1. Re-run audit and reports
2. `python -m benchassist.vercel_export --auto`
3. Commit updated JSON or redeploy
4. Re-check Overview, Flagged Cases, Case Explorer, Reports
