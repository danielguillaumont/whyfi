"""Structured models for complete WHYFI diagnostic runs."""

from dataclasses import dataclass

from whyfi.models.dns import DNSDiagnosticResult
from whyfi.models.local_config import LocalConfigResult
from whyfi.models.network import PrimaryConnection
from whyfi.models.probes import InternetReachabilityResult, PingResult
from whyfi.models.wifi import WiFiConnection


@dataclass(slots=True)
class BaselineDiagnosticResult:
    """Represents the results of WHYFI's baseline network investigation."""

    connection: PrimaryConnection | None
    gateway: PingResult | None
    internet: InternetReachabilityResult | None
    dns: DNSDiagnosticResult | None
    completed: bool
    wifi: WiFiConnection | None = None
    local_config: LocalConfigResult | None = None
    error: str | None = None
