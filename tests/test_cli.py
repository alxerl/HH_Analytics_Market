from hh_market.cli import main
from hh_market.ingestion.collector import CollectionSummary


def test_collect_prints_run_summary(capsys, monkeypatch) -> None:
    def fake_collect(*_args, **_kwargs) -> CollectionSummary:
        return CollectionSummary(pages_collected=1, pages_skipped=0, items_collected=3)

    monkeypatch.setattr("hh_market.cli.collect_queries", fake_collect)
    assert main(["collect", "--query-set", "config/search_queries.yml"]) == 0
    output = capsys.readouterr().out
    assert "run_id=" in output
    assert "items_collected=3" in output
