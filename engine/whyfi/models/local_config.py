"""Structured models for WHYFI local network configuration diagnostics."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class LocalConfigResult:
    """Represents the health of the machine's local IP configuration."""

    healthy: bool
    active_adapters: list[str] = field(default_factory=list)
    usable_ipv4_adapters: list[str] = field(default_factory=list)
    link_local_ipv4_adapters: list[str] = field(default_factory=list)
    likely_dhcp_issue: bool = False
    error: str | None = None
