"""Structured models for WHYFI connectivity probes."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class PingResult:
    """Represents the result of an ICMP connectivity test."""

    target: str
    reachable: bool
    packets_sent: int
    packets_received: int
    packet_loss_percent: float
    min_latency_ms: float | None = None
    average_latency_ms: float | None = None
    max_latency_ms: float | None = None
    jitter_ms: float | None = None
    error: str | None = None


@dataclass(slots=True)
class InternetReachabilityResult:
    """Represents WHYFI's direct-IP internet reachability check."""

    reachable: bool
    targets_tested: int
    targets_reachable: int
    probes: list[PingResult] = field(default_factory=list)
    error: str | None = None
