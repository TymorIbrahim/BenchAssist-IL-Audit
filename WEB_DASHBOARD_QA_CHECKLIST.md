# Web Dashboard QA Checklist

Manual checks before demo, class presentation, or Vercel deploy.

## Core experience (slim detention audit)

1. [ ] **Home** explains the project in under 30 seconds (research question, minimal schema, expert review path).
2. [ ] **Disclaimers** visible (SafetyContextBar + trust badges).
3. [ ] **Primary tabs** load: Home, Audit Results, Case Review, Mitigation, Validity, Reports, Methodology.
4. [ ] **Audit Results** shows dangerousness-focused metrics, address-proxy bucket, executive findings, variant matrix.
5. [ ] **Case Review** loads review records; audit signal (dangerousness Δ) shown first; reasoning diff; collapsible case inputs; quick filters; slim checklist.
6. [ ] **Mitigation** shows cross-prompt heatmap for three prompt modes.
7. [ ] **Validity** explains strict vs address-proxy exclusions.
8. [ ] **Reports** lists exported markdown reports and policy/overview JSON downloads.
9. [ ] **Methodology** documents minimal schema and dangerousness-only flagging.
10. [ ] No **“bias proven”** or unlawful-discrimination conclusion wording.
11. [ ] No **API keys** or `.env` in `web_dashboard/public/data/`.
12. [ ] **Mobile / narrow layout** usable (nav, tables, case review panes).
13. [ ] **`npm test`** and **`npm run build`** pass after export refresh.
14. [ ] **E2E** (`npm run test:e2e`) passes for tab navigation and deep links.
15. [ ] **Performance**: home does not prefetch all 360 review JSON files; Case Review loads index first, records on demand; deep links work.
16. [ ] **`npm run validate:data`** passes (no literal `NaN` / invalid JSON in export).

## Performance (current)

- Initial dashboard load fetches manifest once, then index and summary JSON — not all split review records.
- Tab panels, presentation mode, and Recharts bar chart are code-split (`next/dynamic`).
- Case Review deep links fetch a single record file; full queue loads in background when tab is open.
- Export validation: `npm run validate:data` and `python -m benchassist.validate_dashboard_export`.
- Flagging policy: [docs/detention_flagging_policy.md](docs/detention_flagging_policy.md).
- Demo/public preview export: add `--demo-redact-case-text` to `vercel_export` (omits full case text in review JSON; manifest `dashboard_export_profile: demo_redacted`).

## Flagging concept (current)

- Only **dangerousness_level** changes between neutral and variant count as flagged.
- Identity, unsupported inference, action/duration shifts are **not** primary audit signals in this export.
- **Address-proxy** variants are in a separate bucket from strict demographic rates.

## Commands

```bash
make detention-preflight          # corpus + dry-run go/no-go (before Gemini; add --resume if output_dir exists)
make detention-post-run           # analysis + dashboard export (after Gemini)
make detention-regen-corpus       # regenerate slim+address CSV (10 bases)

python -m benchassist.vercel_export --use-case detention \
  --run-dir results/gemini/detention_expanded_minimal_address \
  --data-status gemini_minimal_address
cd web_dashboard && npm install && npm test && npm run validate:data && npm run build && npm run test:e2e
make dashboard-qa
```
