# Contributing

Use Python 3.12+ and `uv`. Install dependencies with `uv sync --all-extras --frozen`.
Before opening a pull request, run `make check` (or the equivalent `uv run` commands).

Keep changes focused, add tests for behaviour changes, and do not commit `.env`, raw API
responses, models, reports, or personal data. Update the relevant contract in `docs/` when
changing a public command, metric, or data schema.
