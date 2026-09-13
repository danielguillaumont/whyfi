"""Structured models for complete WHYFI diagnostic runs."""

from dataclasses import dataclass

from whyfi.models.dns import DNSDiagnosticResult
from whyfi.models.network import PrimaryConnection
from whyfi.models.probes import InternetReachabilityResult, PingResult


@dataclass(slots=True)
class BaselineDiagnosticResult:
    """Represents the results of WHYFI's baseline network investigation."""

    connection: PrimaryConnection | None
    gateway: PingResult | None
    internet: InternetReachabilityResult | None
    dns: DNSDiagnosticResult | None
    completed: bool
    error: str | None = None
