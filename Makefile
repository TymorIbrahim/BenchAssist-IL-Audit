.PHONY: test dashboard-qa export-detention-minimal detention-regen-corpus detention-preflight detention-dry-run detention-post-run

CONFIG_MINIMAL ?= configs/gemini_detention_expanded_minimal_address.yaml

test:
	python -m pytest -q

export-detention-minimal:
	python -m benchassist.vercel_export --use-case detention \
		--run-dir results/gemini/detention_expanded_minimal_address \
		--data-status gemini_minimal_address

detention-regen-corpus:
	python -m benchassist.detention_data_generation \
		--variant-set slim \
		--include-address-variants \
		--max-base-cases 30

detention-preflight:
	python -m benchassist.detention_run_preflight --config $(CONFIG_MINIMAL) --resume

detention-preflight-new:
	python -m benchassist.detention_run_preflight --config $(CONFIG_MINIMAL)

detention-dry-run:
	python -m benchassist.detention_full_run_plan --config $(CONFIG_MINIMAL) --dry-run

detention-post-run:
	python -m benchassist.detention_post_run --config $(CONFIG_MINIMAL)

dashboard-qa:
	cd web_dashboard && npm test && npm run validate:data && npm run build
	python -m benchassist.validate_dashboard_export --data-dir web_dashboard/public/data
