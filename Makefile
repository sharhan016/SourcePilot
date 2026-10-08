.PHONY: verify test lint web-check

test:
	python3 -m pytest tests -q

lint:
	python3 -m ruff check apps tests

web-check:
	npm --prefix apps/web run check

verify: test web-check

