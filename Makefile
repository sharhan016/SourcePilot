.PHONY: verify test lint web-check web-test deploy-check

test:
	python3 -m pytest tests -q

lint:
	python3 -m ruff check apps tests

web-check:
	npm --prefix apps/web run check

web-test:
	npm --prefix apps/web run test

deploy-check:
	bash scripts/verify_hostinger_deployment.sh

verify: lint test web-test web-check
	python3 -m compileall -q apps/api/sourcepilot tests
