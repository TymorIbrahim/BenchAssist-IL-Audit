# Web Dashboard QA Checklist

Manual checks before demo, class presentation, or Vercel deploy.

## Core experience (20 checks)

1. [ ] **First screen** explains the project in under 30 seconds (title, subtitle, summary, trust badges, reviewer path).
2. [ ] **Disclaimers** are visible without scrolling too far (sticky banner + trust badges on Executive overview).
3. [ ] **Recommended review path** is clear (Open reviewer path buttons + best starting point text).
4. [ ] **Main Findings** are understandable without technical background (What we measured / why inspect / caution lines).
5. [ ] **Metric definitions** are available (MetricExplainer, glossary, tooltips on cards).
6. [ ] **Explore by concern** works — cards set filters and scroll to Flagged Cases.
7. [ ] **Flagged Cases filters** work (priority, issue tag, high-priority only, search, reset).
8. [ ] **Flagged Cases actions** are not duplicated (Actions column; Copy JSON off by default).
9. [ ] **Case Explorer comparison** works (neutral vs variant, cross-prompt modes, empty states clear).
10. [ ] **Reviewer packet** downloads correctly with disclaimer and key fields (`review_packet_CASEID_VARIANTID.md`).
11. [ ] **Cross-prompt comparison** empty states are clear when only one prompt mode exported.
12. [ ] **Validity section** explains strict vs cautious comparisons.
13. [ ] **Stereotype and hallucination** sections are understandable with graceful empty states.
14. [ ] **Human Review** section gives clear next steps and template download.
15. [ ] **Reports** are easy to find (categories, search, recommended reading order, download).
16. [ ] No **“bias proven”** or unlawful-discrimination conclusion wording anywhere.
17. [ ] No **API keys** or `.env` content in `web_dashboard/public/data/` or source.
18. [ ] **Mobile / narrow layout** is usable (sidebar stacks, tables scroll, nav readable).
19. [ ] **`npm run build`** passes after export refresh.
20. [ ] **Vercel preview** can be deployed (`vercel` from `web_dashboard/`).

## New UX features (this pass)

- [ ] **Executive overview** — trust badges, reviewer path, audience guide
- [ ] **Key takeaways** — 3–6 cautious cards from exported data
- [ ] **Explore by concern** — legal-concern cards with counts
- [ ] **Flagged Cases queue** — review priority explanation, issue tags, reviewer packet
- [ ] **Case Explorer** — reviewer guidance box, What changed panel
- [ ] **Presentation panel** — 30s/1min summaries, demo path
- [ ] **Data transparency** — export metadata expandable panel
- [ ] **Methodology & limitations** — readable cards, scope caveats

## Interaction features

- [ ] Start **guided review** — steps, localStorage progress, go-to-section buttons
- [ ] **Presentation mode** — larger cards, hides dense tables, 5-minute path
- [ ] **Share link** — Case Explorer copy link; Flagged Cases filtered view link
- [ ] **Deep link** — `?section=case-explorer&case_id=…&variant_id=…` loads state
- [ ] **Comparison modes** in Case Explorer (empty state when data missing)
- [ ] **Glossary drawer** — opens from toolbar and sidebar

## Commands

```bash
python -m benchassist.vercel_export --auto
cd web_dashboard && npm install && npm run dev
npm run build
vercel          # preview
vercel --prod   # production
```dfxss
