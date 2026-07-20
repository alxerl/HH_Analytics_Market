from hh_market.quality.checks import QualityResult
from hh_market.quality.runner import should_fail


def test_severity_exit_threshold() -> None:
    results = [QualityResult("example", "warning", False, 1, 0)]
    assert not should_fail(results, "critical")
    assert should_fail(results, "warning")
    assert should_fail(results, "info")
