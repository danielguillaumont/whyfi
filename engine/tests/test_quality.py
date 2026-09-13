"""Connection-quality diagnostic tests for WHYFI."""

from whyfi.diagnostics.windows import quality
from whyfi.models.network import PrimaryConnection
from whyfi.models.probes import PingResult


def make_connection() -> PrimaryConnection:
    """Create a representative primary connection."""

    return PrimaryConnection(
        adapter_name="Wi-Fi",
        adapter_type="wifi",
        interface_index=17,
        ipv4_address="192.168.50.211",
        gateway="192.168.50.1",
        is_up=True,
        speed_mbps=286,
        mtu=1500,
    )


def make_ping(
    target: str,
    jitter_ms: float = 5.0,
    packet_loss_percent: float = 0.0,
) -> PingResult:
    """Create a representative successful ping measurement."""

    packets_sent = 10
    packets_received = round(
        packets_sent * (1 - packet_loss_percent / 100)
    )

    return PingResult(
        target=target,
        reachable=True,
        packets_sent=packets_sent,
        packets_received=packets_received,
        packet_loss_percent=packet_loss_percent,
        min_latency_ms=10.0,
        average_latency_ms=20.0,
        max_latency_ms=30.0,
        jitter_ms=jitter_ms,
    )


def test_healthy_connection_quality(monkeypatch) -> None:
    """Stable gateway and public probes should be healthy."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.healthy is True
    assert result.high_jitter is False
    assert result.packet_loss_detected is False


def test_gateway_high_jitter_is_detected(monkeypatch) -> None:
    """High jitter to the local router should be considered meaningful."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target == "192.168.50.1":
            return make_ping(target, jitter_ms=20.0)

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.healthy is False
    assert result.high_jitter is True


def test_both_public_targets_with_high_jitter_are_detected(
    monkeypatch,
) -> None:
    """High jitter across both public targets should indicate instability."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target in {"1.1.1.1", "8.8.8.8"}:
            return make_ping(target, jitter_ms=35.0)

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.healthy is False
    assert result.high_jitter is True


def test_one_noisy_public_target_does_not_trigger_jitter(
    monkeypatch,
) -> None:
    """One noisy public endpoint should not condemn the connection."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target == "1.1.1.1":
            return make_ping(target, jitter_ms=50.0)

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.healthy is True
    assert result.high_jitter is False


def test_gateway_packet_loss_is_detected(monkeypatch) -> None:
    """Packet loss to the router should indicate local instability."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target == "192.168.50.1":
            return make_ping(
                target,
                packet_loss_percent=10.0,
            )

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.healthy is False
    assert result.packet_loss_detected is True


def test_both_public_targets_with_loss_are_detected(
    monkeypatch,
) -> None:
    """Packet loss across both public targets should indicate instability."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target in {"1.1.1.1", "8.8.8.8"}:
            return make_ping(
                target,
                packet_loss_percent=10.0,
            )

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.healthy is False
    assert result.packet_loss_detected is True


def test_one_lossy_public_target_does_not_trigger_failure(
    monkeypatch,
) -> None:
    """One lossy public endpoint should not condemn the connection."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target == "8.8.8.8":
            return make_ping(
                target,
                packet_loss_percent=10.0,
            )

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.healthy is True
    assert result.packet_loss_detected is False


def test_quality_requires_at_least_two_samples() -> None:
    """Jitter analysis should require multiple measurements."""

    try:
        quality.check_connection_quality(sample_count=1)
    except ValueError as exc:
        assert str(exc) == "sample_count must be at least 2"
    else:
        raise AssertionError("Expected ValueError")


def test_healthy_quality_has_no_instability_scope(monkeypatch) -> None:
    """Healthy measurements should not mark either network segment unstable."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.gateway_unstable is False
    assert result.internet_unstable is False


def test_gateway_jitter_is_scoped_to_local_network(monkeypatch) -> None:
    """Gateway jitter should identify the local network as unstable."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target == "192.168.50.1":
            return make_ping(
                target,
                jitter_ms=20.0,
            )

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.gateway_unstable is True
    assert result.internet_unstable is False


def test_public_jitter_is_scoped_to_internet(monkeypatch) -> None:
    """Jitter across both public targets should identify upstream instability."""

    monkeypatch.setattr(
        quality,
        "get_primary_connection",
        make_connection,
    )

    def fake_ping(target: str, count: int) -> PingResult:
        if target in {"1.1.1.1", "8.8.8.8"}:
            return make_ping(
                target,
                jitter_ms=35.0,
            )

        return make_ping(target)

    monkeypatch.setattr(
        quality,
        "ping_host",
        fake_ping,
    )

    result = quality.check_connection_quality()

    assert result.gateway_unstable is False
    assert result.internet_unstable is True
