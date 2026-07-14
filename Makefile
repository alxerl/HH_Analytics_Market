.PHONY: install lint typecheck test check collect

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
