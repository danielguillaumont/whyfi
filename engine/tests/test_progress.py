"""Progress reporting tests for WHYFI diagnostics."""

from types import SimpleNamespace

from whyfi.diagnostics.windows import baseline, quality
from whyfi.models.probes import PingResult


def test_baseline_reports_progress(monkeypatch) -> None:
    """Baseline diagnostics should report each investigation stage."""

    connection = SimpleNamespace(
        gateway="192.0.2.1",
        adapter_type="wifi",
    )

    monkeypatch.setattr(
        baseline,
        "check_local_config",
        lambda: object(),
    )
    monkeypatch.setattr(
        baseline,
        "get_primary_connection",
        lambda: connection,
    )
    monkeypatch.setattr(
        baseline,
        "ping_host",
        lambda target: object(),
    )
    monkeypatch.setattr(
        baseline,
        "get_wifi_connection",
        lambda: object(),
    )
    monkeypatch.setattr(
        baseline,
        "check_internet_reachability",
        lambda: object(),
    )
    monkeypatch.setattr(
        baseline,
        "check_dns",
        lambda: object(),
    )

    messages: list[str] = []

    result = baseline.run_baseline_diagnostics(
        progress=messages.append,
    )

    assert result.completed is True
    assert messages == [
        "Checking network configuration...",
        "Finding your active connection...",
        "Checking your router...",
        "Checking Wi-Fi signal...",
        "Testing internet access...",
        "Checking DNS...",
    ]


def test_quality_reports_progress(monkeypatch) -> None:
    """Quality diagnostics should report each measurement stage."""

    connection = SimpleNamespace(
        gateway="192.0.2.1",
    )

    def stable_ping(
        target: str,
        count: int = 10,
    ) -> PingResult:
        return PingResult(
            target=target,
            reachable=True,
            packets_sent=count,
            packets_received=count,
            packet_loss_percent=0.0,
            min_latency_ms=1.0,
            average_latency_ms=2.0,
            max_latency_ms=3.0,
            jitter_ms=1.0,
        )

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        lambda: connection,
    )
    monkeypatch.setattr(
        quality,
        "ping_host",
        stable_ping,
    )

    messages: list[str] = []

    result = quality.check_connection_quality(
        sample_count=2,
        progress=messages.append,
    )

    assert result.healthy is True
    assert messages == [
        "Finding your active connection...",
        "Measuring your router connection...",
        "Testing 1.1.1.1...",
        "Testing 8.8.8.8...",
        "Analyzing connection stability...",
    ]
