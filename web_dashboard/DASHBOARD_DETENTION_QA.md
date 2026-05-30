# BenchAssist-IL Detention Dashboard QA Checklist

Manual QA for the v3 expert-facing detention audit dashboard.

## Build & runtime

- [ ] `cd web_dashboard && npm install` succeeds
- [ ] `npm run lint` passes
- [ ] `npm run build` passes
- [ ] `npm test` passes (vitest unit tests)
- [ ] `npm run test:e2e` passes (Playwright smoke tests; requires build first)
- [ ] `npm run dev` → http://localhost:3000 loads without console errors
- [ ] No Python backend, `.env`, or API keys required at runtime

## Information architecture (8 tabs)

- [ ] **Home** — research story, hero, timeline, examples, audit method diagram, readiness, **Start expert review** CTA, **export metadata & provenance** panel
- [ ] **Audit Results** — summary cards, takeaways, **executive findings cards**, findings by issue, charts, group summary, variant matrix
- [ ] **Case Review** — unified expert workspace (queue, comparison, checklist, packet, progress)
- [ ] **Mitigation** — prompt mode cards, **cross-prompt field heatmap**, or clear empty state
- [ ] **Real Cases** — source browser + RTL full-text viewer + **add to review packet**
- [ ] **Legal Reliability** — grounding, unsupported inference, statistical tables
- [ ] **Reports** — search, filter by type, Markdown render, download
- [ ] **Methodology** — layers, examples, expandable limitations
- [ ] Legacy **Expert Workspace** tab URL redirects to Case Review
- [ ] Sticky tab navigation shows active section
- [ ] URL updates on tab / filter / case (`?tab=case-review&review_id=…&cr_base=…&cr_variant=…`)
- [ ] URL does **not** change on scroll alone
- [ ] Legacy URLs (`?tab=overview`, `?tab=findings`) redirect to new tabs

## Safety & disclaimers (reduced clutter)

- [ ] **No repeated disclaimer banners** on every section
- [ ] **Status strip** shows data mode, strict fairness source, access control
- [ ] **SafetyContextBar** chips visible (Research only, Not legal advice, etc.)
- [ ] **Why this matters** drawer opens from chips / button
- [ ] Full-text access-control note in drawer when full text exported
- [ ] One-line contextual notes on pages (not wall-of-text)
- [ ] No forbidden language (“bias proven”, “discriminatory”, “illegal”, etc.)

## Home / research story

- [ ] Hero with title, subtitle, badges, single clean note
- [ ] Research question card visible
- [ ] **Why this matters** expandable section works
- [ ] **Process timeline** (8 steps) with links to sections
- [ ] **Concrete examples** (base case, variant, output, comparison)
- [ ] **Audit method diagram** (synthetic lane + real-case lane)
- [ ] Readiness panel: “Dashboard ready for expert review”
- [ ] Export metadata shows git commit, split-export note, pairwise dedupe note when present

## Audit Results

- [ ] Layer 1: summary metric cards with ⓘ tooltips
- [ ] Layer 2: key takeaway cards + **executive findings** + findings grouped by legal issue
- [ ] Executive findings and findings-by-issue render from **review index** before full records load
- [ ] “Review these cases” links open Case Review Workspace with filters pre-set
- [ ] Variant matrix **Open in Case Review** sets `cr_base`, `cr_variant`, and `review_id` when index entry exists
- [ ] Layer 3: filters (via sticky filter bar on tab)
- [ ] Layer 4: bar chart + group summary cards
- [ ] Mock/Gemini full labels unobtrusive but clear

## Case Review Workspace (legal expert)

- [ ] `detention_case_review_index.json` loads on initial page load (lightweight queue metadata with `search_blob`, `issue_flags`)
- [ ] Full review records lazy-load in background (split per-record JSON under `detention_case_review_records/`)
- [ ] Review queue shows all review records with filters
- [ ] Search matches memo text / reasoning via index `search_blob` when records loaded
- [ ] Filters work: priority, variant, base scenario, local review state, focus mode, **flagged-only**
- [ ] **Mobile tab bar** (Queue / Comparison / Checklist) on narrow screens
- [ ] Base vs variant facts visible (full case text + structured facts)
- [ ] **Inline Hebrew text diff** between base and variant case text
- [ ] Full prompt viewer works (collapsible, reconstruction / exact-prompt status shown)
- [ ] **Cross-prompt comparison panel** (baseline vs mitigation modes when exported)
- [ ] Model output comparison side-by-side with diff indicators
- [ ] Changed fields highlighted (unchanged / changed / increased risk / omitted)
- [ ] Difference summary + why flagged panel visible
- [ ] **Reasoning excerpt** panel for long model outputs
- [ ] Legal expert checklist works (Yes / No / —)
- [ ] Review decision dropdown persists locally
- [ ] Local notes persist in localStorage
- [ ] Add/remove from review packet works (synthetic + real cases)
- [ ] Packet export JSON / CSV / Markdown includes diffs + checklist + notes
- [ ] **Review progress panel** (reviewed / flagged / packet counts; shows during lazy load)
- [ ] **Review state backup** import/export (JSON)
- [ ] **Keyboard navigation**: ↑/↓ or j/k to move queue selection
- [ ] Focus review mode shows high-priority flagged only
- [ ] Empty state shows export command when JSON missing
- [ ] Prompt text marked as `reconstructed_from_prompt_builder` for existing runs; `exact_prompt_logged` on future runs

## Start expert review flow

- [ ] Home **Start expert review** opens Case Review with focus mode + first high-priority flagged case selected after lazy load

## Real Case Review

- [ ] Source browser + metadata (stage, expert approval, sensitive flag)
- [ ] RTL Hebrew typography, expand/collapse, keyword chips
- [ ] “Excluded from strict rates” badge
- [ ] Local notes persist in localStorage
- [ ] Copy source summary
- [ ] **Add to / remove from review packet** (browser-local)

## Mitigation / Legal Reliability

- [ ] Mitigation side-by-side prompt mode cards
- [ ] **Cross-prompt field instability heatmap** when cross-prompt comparisons exported
- [ ] Legal reliability grouped by legal field
- [ ] Statistical tables show exploratory interpretation caveats
- [ ] Empty states explain missing data + export command

## Reports

- [ ] Report cards + search + type filter
- [ ] Markdown renders; download works
- [ ] QA / analysis / review packet reports findable

## Guided tour & presentation

- [ ] **Start here** guided tour (6 steps)
- [ ] **Presentation mode** — research question, method, metrics, findings, example, limitations
- [ ] Presentation hides dense triage tables (overlay mode)

## Metric tooltips

- [ ] Dangerousness shift, identity leakage, unsupported inference, strict fairness explained

## Accessibility & responsive

- [ ] Tab keyboard focus visible
- [ ] Tables scroll on narrow screens
- [ ] Case review uses mobile tab bar on narrow screens; stacks on tablet
- [ ] Loading screen while data fetches

## Housing fallback

- [ ] `manifest.use_case !== "detention"` still loads housing dashboard

## Commands

```bash
cd web_dashboard
npm install && npm run lint && npm test && npm run build && npm run test:e2e

# Refresh full Gemini export (repo root; no new model run):
python -m benchassist.vercel_export --auto --use-case detention --run-dir results/gemini/detention_full --data-status gemini_full

python -m benchassist.validate_dashboard_export --data-dir web_dashboard/public/data

python -m pytest
```

## Known limitations

- Full side-by-side memo text requires per-case model output in export (deltas work from analysis)
- Some statistical columns may use legacy housing-era names when reusing shared exports
- Review notes and packet state are browser-local only
- Cross-prompt panel needs multi-mode outputs in export; single-mode runs show empty state
- Existing Gemini run prompts are reconstructed; exact prompts logged on future runner executions

## Ready for legal-expert review?

After this checklist passes on exported Gemini full data: **Yes** — deploy only behind access control if full text is included.
