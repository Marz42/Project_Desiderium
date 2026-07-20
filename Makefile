.PHONY: test test-unit test-integration lint typecheck

test-unit:
	python -m pytest tests/unit -v --tb=short

test-integration:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
	docker compose -f docker-compose.test.yml down -v

test: test-unit

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy app
