# Clean-room release checklist

Run these commands from a fresh clone with Python 3.12+, Docker and `uv` installed.

```bash
uv sync --all-extras --frozen
uv run ruff check .
uv run mypy
uv run pytest
docker compose up -d db
uv run hh-market migrate
uv run hh-market collect --date YYYY-MM-DD --query-set config/search_queries.yml
uv run hh-market load --date YYYY-MM-DD
uv run hh-market predict
uv run hh-market build-marts
uv run hh-market quality --date YYYY-MM-DD --fail-on critical
uv run hh-market recommend --date YYYY-MM-DD --profile data/profiles/example_profile.yml --top 20
```

Release only when the quality command exits zero, all CI checks pass, and no raw API responses,
`.env`, model binaries, or generated reports appear in `git status`.

For hybrid inference, run `train` first, then call `predict` with `--model-path` and
`--model-version`. Review the generated model card before making any performance claim.
