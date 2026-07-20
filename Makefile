.PHONY: install lint typecheck test check collect migrate e2e

install:
	uv sync --all-extras --frozen

lint:
	uv run ruff check .

typecheck:
	uv run mypy

test:
	uv run pytest

check: lint typecheck test

collect:
	uv run hh-market collect --query-set config/search_queries.yml

migrate:
	uv run hh-market migrate

e2e:
	uv run hh-market migrate
	uv run pytest tests/test_integration_database.py
