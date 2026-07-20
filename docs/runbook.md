# Operations runbook

## Normal daily run

```bash
uv run hh-market migrate
uv run hh-market collect --date YYYY-MM-DD
uv run hh-market load --date YYYY-MM-DD
uv run hh-market predict
uv run hh-market quality --date YYYY-MM-DD --fail-on critical
```

## Incident response

- **429/5xx:** rerun `collect --resume`; completed raw pages are recorded in the manifest.
- **Partial raw file:** delete only a `.tmp` file; never edit an accepted JSON page. Re-run with
  `--resume`.
- **Database unavailable:** restore PostgreSQL, run `migrate`, then rerun `load` with the same
  date. Loader upserts are idempotent.
- **Schema drift:** stop downstream commands, capture the raw response, add a migration and a
  contract fixture before resuming.
- **Critical DQ failure:** do not publish BI refreshes; inspect `reports/quality-*.md`, remediate
  the source or loader, and rerun the full stage.

## Data retention

Raw API responses may contain third-party data. Keep them outside Git, limit access, and delete
them according to the agreed retention policy and HeadHunter terms.
