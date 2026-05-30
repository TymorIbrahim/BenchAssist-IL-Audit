# BenchAssist-IL Audit — Vercel Research Dashboard

Read-only Next.js dashboard for sharing audit results with team members, legal experts, and Responsible AI reviewers.

**Design goal:** A polished legal-research product — story-driven, cautious, and presentation-ready. Not a raw data dump.

## Dashboard purpose

- Present a **Responsible AI audit** of a toy, non-binding Israeli bench-memo assistant
- Show **two dataset modes**: synthetic controlled counterfactual audit (strict fairness) and **Real Israeli Case-Inspired Audit** (domain realism, reliability, stereotype/grounding — not strict bias proof)
- Help **legal experts** triage flagged case comparisons and inspect neutral vs variant memos
- Support **RAI reviewers** and **course evaluators** with plain-language summaries, limitations, and reports
- Run entirely from **exported static JSON** — no backend, no API keys, no live model calls

## Who should use this

**For:** legal experts reviewing flagged cases; RAI reviewers; bias-in-LLM researchers; course reviewers evaluating audit design.

**Not for:** litigants seeking legal advice; judges making decisions; production court deployment; legal certification of model safety.

## What this is not

- **Not legal advice**
- **Not an AI judge**
- **Not** proof of unlawful discrimination — metrics are screening signals only
- **Not** a production judicial system

## Export audit data

From the project root:

```bash
python -m benchassist.vercel_export --auto
```

Optional custom output directory:

```bash
python -m benchassist.vercel_export --output-dir web_dashboard/public/data
```

This writes JSON to `web_dashboard/public/data/` (manifest, metrics, tables, reports). No secrets or `.env` content is exported.

## Run locally

```bash
cd web_dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Build for production

```bash
cd web_dashboard
npm install
npm run build
npm run start
```

## Deploy to Vercel

Preview deploy:

```bash
cd web_dashboard
vercel
```

Production deploy:

```bash
cd web_dashboard
vercel --prod
```

Set the project root to `web_dashboard` when linking the Vercel project. No `.env` is required on Vercel.

## Reviewer workflow

1. Start at **Executive overview** — read trust badges and use **Open reviewer path**
2. Review **Key takeaways** and **Main findings** (screening signals, not conclusions)
3. Use **Explore by concern** or **Flagged cases** to triage the review queue
4. Open a case in **Case explorer** — compare neutral vs variant, check validity, download reviewer packet
5. Read **Methodology & limitations** and open reports as needed

**Five-minute path:** Main Findings → one high-priority flagged case → Methodology & limitations.

## Refresh after new audit results

1. Re-run the audit pipeline and generate reports
2. Run `python -m benchassist.vercel_export --auto`
3. Commit updated `public/data/*.json` (or redeploy)

## Navigation (grouped)

| Group | Sections |
|-------|----------|
| Overview | Executive overview, Key takeaways, Audit story |
| Results | Main findings, Flagged cases, Case explorer, Validity, Mitigation, Narrative |
| Safety audits | Identity leakage, Grounding & hallucination, Statistical uncertainty |
| Review & export | Human review, Reports & downloads, Methodology & limitations |

Global filters (variant, cue, case ID, review priority, concern tag, search, flagged-only) apply across triage sections.

## Safety

- No API keys in the repository or dashboard code
- No `.env` required on Vercel
- No external model API calls at runtime
- Read-only dashboard — no user-submitted data stored

## Cross-prompt comparison

Case Explorer can compare the **same case and variant** across prompt modes (baseline, fairness-aware, demographic-blind). Requires exported output CSVs for more than one prompt mode:

```bash
python -m benchassist.vercel_export --auto
```

If only baseline exists, cross-prompt modes show a clear empty state.

See `WEB_DASHBOARD_QA_CHECKLIST.md` and `VERCEL_DEPLOYMENT_CHECKLIST.md` for manual QA steps.
