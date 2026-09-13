"""Structured models for WHYFI connectivity probes."""

from dataclasses import dataclass


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
    error: str | None = None
