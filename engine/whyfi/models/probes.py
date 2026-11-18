"""Structured models for WHYFI connectivity probes."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class PingResult:
    """An ICMP test. A null reachable value means collection failed."""

    target: str
    reachable: bool | None
    packets_sent: int | None
    packets_received: int | None
    packet_loss_percent: float | None
    min_latency_ms: float | None = None
    average_latency_ms: float | None = None
    max_latency_ms: float | None = None
    jitter_ms: float | None = None
    error: str | None = None


@dataclass(slots=True)
class InternetReachabilityResult:
    """Represents WHYFI's direct-IP internet reachability check."""

    reachable: bool | None
    targets_tested: int
    targets_reachable: int
    probes: list[PingResult] = field(default_factory=list)
    error: str | None = None
