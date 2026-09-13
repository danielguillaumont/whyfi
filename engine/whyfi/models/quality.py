"""Structured models for WHYFI connection-quality diagnostics."""

from dataclasses import dataclass, field

from whyfi.models.probes import PingResult


@dataclass(slots=True)
class ConnectionQualityResult:
    """Represents a deeper measurement of network connection quality."""

    gateway: PingResult | None
    internet_probes: list[PingResult] = field(default_factory=list)
    healthy: bool = True
    high_jitter: bool = False
    packet_loss_detected: bool = False
    error: str | None = None
