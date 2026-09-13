"""Connection-quality diagnosis tests for WHYFI."""

from whyfi.diagnosis.quality import diagnose_connection_quality
from whyfi.models.diagnosis import DiagnosisCode
from whyfi.models.probes import PingResult
from whyfi.models.quality import ConnectionQualityResult


def make_ping(
    target: str,
    jitter_ms: float = 5.0,
    packet_loss_percent: float = 0.0,
) -> PingResult:
    """Create a representative ping result."""

    return PingResult(
        target=target,
        reachable=True,
        packets_sent=10,
        packets_received=10,
        packet_loss_percent=packet_loss_percent,
        min_latency_ms=10.0,
        average_latency_ms=20.0,
        max_latency_ms=30.0,
        jitter_ms=jitter_ms,
    )


def make_public_probes() -> list[PingResult]:
    """Create healthy public internet probes."""

    return [
        make_ping("1.1.1.1"),
        make_ping("8.8.8.8"),
    ]


def test_healthy_quality_diagnosis() -> None:
    """Healthy quality measurements should produce a healthy diagnosis."""

    result = ConnectionQualityResult(
        gateway=make_ping("192.168.50.1"),
        internet_probes=make_public_probes(),
        healthy=True,
        gateway_unstable=False,
        internet_unstable=False,
        high_jitter=False,
        packet_loss_detected=False,
    )

    diagnosis = diagnose_connection_quality(result)

    assert diagnosis.code == DiagnosisCode.HEALTHY
    assert diagnosis.confidence >= 90
    assert diagnosis.title == "Your connection quality looks healthy."


def test_local_instability_diagnosis() -> None:
    """Gateway instability should be diagnosed as a local network problem."""

    result = ConnectionQualityResult(
        gateway=make_ping(
            "192.168.50.1",
            jitter_ms=20.0,
        ),
        internet_probes=make_public_probes(),
        healthy=False,
        gateway_unstable=True,
        internet_unstable=False,
        high_jitter=True,
        packet_loss_detected=False,
    )

    diagnosis = diagnose_connection_quality(result)

    assert diagnosis.code == DiagnosisCode.UNSTABLE_CONNECTION
    assert diagnosis.confidence >= 90
    assert diagnosis.title == "Your local connection is unstable."


def test_upstream_instability_diagnosis() -> None:
    """Public instability with a stable gateway should be diagnosed upstream."""

    public_probes = [
        make_ping("1.1.1.1", jitter_ms=35.0),
        make_ping("8.8.8.8", jitter_ms=40.0),
    ]

    result = ConnectionQualityResult(
        gateway=make_ping("192.168.50.1"),
        internet_probes=public_probes,
        healthy=False,
        gateway_unstable=False,
        internet_unstable=True,
        high_jitter=True,
        packet_loss_detected=False,
    )

    diagnosis = diagnose_connection_quality(result)

    assert diagnosis.code == DiagnosisCode.UNSTABLE_CONNECTION
    assert diagnosis.confidence >= 90
    assert diagnosis.title == (
        "The instability appears to be beyond your router."
    )


def test_quality_error_returns_unknown() -> None:
    """Failed quality collection should produce an unknown diagnosis."""

    result = ConnectionQualityResult(
        gateway=None,
        internet_probes=[],
        healthy=False,
        error="No primary network connection was found.",
    )

    diagnosis = diagnose_connection_quality(result)

    assert diagnosis.code == DiagnosisCode.UNKNOWN
    assert diagnosis.confidence < 60
    assert diagnosis.evidence == [
        "No primary network connection was found."
    ]
