"""Deeper Windows connection-quality diagnostics for WHYFI."""

from __future__ import annotations

from whyfi.diagnostics.windows.ping import ping_host
from whyfi.diagnostics.windows.primary import get_primary_connection
from whyfi.models.quality import ConnectionQualityResult


_DEFAULT_PUBLIC_TARGETS = (
    "1.1.1.1",
    "8.8.8.8",
)

_GATEWAY_JITTER_THRESHOLD_MS = 15.0
_INTERNET_JITTER_THRESHOLD_MS = 30.0
_PACKET_LOSS_THRESHOLD_PERCENT = 10.0


def check_connection_quality(
    sample_count: int = 10,
) -> ConnectionQualityResult:
    """Run a deeper packet-loss and jitter investigation."""

    if sample_count < 2:
        raise ValueError("sample_count must be at least 2")

    try:
        connection = get_primary_connection()
    except Exception as exc:
        return ConnectionQualityResult(
            gateway=None,
            healthy=False,
            error=f"Primary connection discovery failed: {exc}",
        )

    if connection is None:
        return ConnectionQualityResult(
            gateway=None,
            healthy=False,
            error="No primary network connection was found.",
        )

    gateway = ping_host(
        connection.gateway,
        count=sample_count,
    )

    internet_probes = [
        ping_host(
            target,
            count=sample_count,
        )
        for target in _DEFAULT_PUBLIC_TARGETS
    ]

    gateway_high_jitter = (
        gateway.jitter_ms is not None
        and gateway.jitter_ms >= _GATEWAY_JITTER_THRESHOLD_MS
    )

    high_jitter_public_probes = [
        probe
        for probe in internet_probes
        if (
            probe.jitter_ms is not None
            and probe.jitter_ms >= _INTERNET_JITTER_THRESHOLD_MS
        )
    ]

    public_high_jitter = (
        bool(internet_probes)
        and len(high_jitter_public_probes)
        == len(internet_probes)
    )

    gateway_packet_loss = (
        gateway.reachable
        and gateway.packet_loss_percent
        >= _PACKET_LOSS_THRESHOLD_PERCENT
    )

    lossy_public_probes = [
        probe
        for probe in internet_probes
        if (
            probe.reachable
            and probe.packet_loss_percent
            >= _PACKET_LOSS_THRESHOLD_PERCENT
        )
    ]

    public_packet_loss = (
        bool(internet_probes)
        and len(lossy_public_probes)
        == len(internet_probes)
    )

    gateway_unstable = (
        gateway_high_jitter
        or gateway_packet_loss
    )

    internet_unstable = (
        public_high_jitter
        or public_packet_loss
    )

    high_jitter = (
        gateway_high_jitter
        or public_high_jitter
    )

    packet_loss_detected = (
        gateway_packet_loss
        or public_packet_loss
    )

    healthy = (
        gateway.reachable
        and any(probe.reachable for probe in internet_probes)
        and not gateway_unstable
        and not internet_unstable
    )

    return ConnectionQualityResult(
        gateway=gateway,
        internet_probes=internet_probes,
        healthy=healthy,
        gateway_unstable=gateway_unstable,
        internet_unstable=internet_unstable,
        high_jitter=high_jitter,
        packet_loss_detected=packet_loss_detected,
    )
