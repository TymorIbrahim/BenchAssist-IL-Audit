.PHONY: regen audit validate dashboard-dev dashboard-build dashboard-qa

# ─────────────────────────────────────────────────────────────────────
# BenchAssist-IL detention audit — current pipeline
#   dataset (Excel) -> rachel_llm_runner -> rachel_data/llm_outputs.json
#   -> rachel_analysis (+ generate_case_reviews) -> deep_analysis_v4
#   -> web_dashboard/public/data -> Next.js v2 dashboard
# ─────────────────────────────────────────────────────────────────────

# Regenerate all dashboard data from existing model outputs (no API calls).
# rachel_analysis also shells out to generate_case_reviews.py.
regen:
	python -m benchassist.rachel_analysis \
		--inputs rachel_data/llm_outputs.json \
		--output-dir web_dashboard/public/data
	python scripts/deep_analysis_v4.py

# Re-run the Gemini model over the dataset (requires GEMINI_API_KEY), then regenerate.
audit:
	python -m benchassist.rachel_llm_runner \
		--excel rachel_data/benchassist_audit_dataset_expanded.xlsx \
		--output rachel_data/llm_outputs.json
	$(MAKE) regen

# Validate the exported dashboard JSON (no NaN/Infinity, required files present).
validate:
	python -m benchassist.validate_dashboard_export --data-dir web_dashboard/public/data

dashboard-dev:
	cd web_dashboard && npm run dev

dashboard-build:
	cd web_dashboard && npm run build

# Full dashboard QA: JSON validation + build + Python export check.
dashboard-qa:
	cd web_dashboard && npm run validate:data && npm run build
	python -m benchassist.validate_dashboard_export --data-dir web_dashboard/public/data
