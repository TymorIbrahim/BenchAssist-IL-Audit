# README for reviewers

Thank you for reviewing the **BenchAssist-IL Audit** project.

## Start here

1. Open **`docs/final_audit_report.md`** (or **`reports/final_audit_report.md`** if copied there).
2. Skim **`docs/PROJECT_OVERVIEW.md`** for context.
3. Optional: run the interactive dashboard from the **repository root** (not from this folder):

   ```bash
   pip install -e '.[dev,dashboard]'
   streamlit run app.py
   ```

## Important cautions

- This is a **toy Responsible AI audit** for a **non-binding** judicial decision-support prototype.
- Outputs are **not legal advice** and the system is **not an AI judge**.
- Automated metrics are **screening tools** only — not proof of unlawful discrimination.
- Cases are **synthetic**; conclusions require **human legal review**.

## Package contents

- `docs/` — project documentation and overview
- `reports/` — Markdown audit reports
- `tables/` — CSV summaries and flagged cases
- `charts/` — figures (if generated)

API keys, `.env`, and raw development caches are **excluded** from this package by design.
