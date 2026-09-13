"""Structured models for WHYFI network information."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class NetworkAdapter:
    """Represents a network adapter discovered on the local system."""

    name: str
    adapter_type: str
    is_up: bool
    is_loopback: bool
    ipv4_addresses: list[str] = field(default_factory=list)
    ipv6_addresses: list[str] = field(default_factory=list)
    mac_address: str | None = None
    speed_mbps: int | None = None
    mtu: int | None = None


@dataclass(slots=True)
class PrimaryConnection:
    """Represents the network connection Windows is using by default."""

    adapter_name: str
    adapter_type: str
    interface_index: int
    ipv4_address: str | None
    gateway: str
    is_up: bool
    speed_mbps: int | None = None
    mtu: int | None = None
