"""Windows local IP configuration diagnostics for WHYFI."""

from __future__ import annotations

import ipaddress

from whyfi.diagnostics.windows.adapters import get_network_adapters
from whyfi.models.local_config import LocalConfigResult
from whyfi.models.network import NetworkAdapter


_VIRTUAL_ADAPTER_TERMS = (
    "vethernet",
    "hyper-v",
    "virtual",
    "vmware",
    "virtualbox",
    "wsl",
    "docker",
    "openvpn",
    "wireguard",
    "tailscale",
)


def _is_virtual_adapter(adapter: NetworkAdapter) -> bool:
    """Return True for common virtual or VPN-style network interfaces."""

    name = adapter.name.lower()

    return any(term in name for term in _VIRTUAL_ADAPTER_TERMS)


def _is_link_local_ipv4(address: str) -> bool:
    """Return True when an IPv4 address is in the 169.254.0.0/16 range."""

    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False

    return parsed.version == 4 and parsed.is_link_local


def _is_usable_ipv4(address: str) -> bool:
    """Return True when an IPv4 address is usable for normal networking."""

    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False

    return (
        parsed.version == 4
        and not parsed.is_loopback
        and not parsed.is_link_local
        and not parsed.is_unspecified
    )


def check_local_config() -> LocalConfigResult:
    """Inspect active Windows adapters for usable IPv4 configuration."""

    try:
        adapters = get_network_adapters()
    except Exception as exc:
        return LocalConfigResult(
            healthy=False,
            error=f"Adapter discovery failed: {exc}",
        )

    active_adapters: list[str] = []
    usable_ipv4_adapters: list[str] = []
    link_local_ipv4_adapters: list[str] = []

    for adapter in adapters:
        if not adapter.is_up:
            continue

        if adapter.is_loopback:
            continue

        if _is_virtual_adapter(adapter):
            continue

        active_adapters.append(adapter.name)

        if any(
            _is_usable_ipv4(address)
            for address in adapter.ipv4_addresses
        ):
            usable_ipv4_adapters.append(adapter.name)

        if any(
            _is_link_local_ipv4(address)
            for address in adapter.ipv4_addresses
        ):
            link_local_ipv4_adapters.append(adapter.name)

    healthy = bool(usable_ipv4_adapters)

    likely_dhcp_issue = (
        bool(active_adapters)
        and not usable_ipv4_adapters
        and bool(link_local_ipv4_adapters)
    )

    error = None

    if not active_adapters:
        error = "No active physical network adapters were found."
    elif likely_dhcp_issue:
        error = (
            "An active adapter has only a link-local IPv4 address. "
            "DHCP may have failed."
        )
    elif not usable_ipv4_adapters:
        error = "No active adapter has a usable IPv4 address."

    return LocalConfigResult(
        healthy=healthy,
        active_adapters=active_adapters,
        usable_ipv4_adapters=usable_ipv4_adapters,
        link_local_ipv4_adapters=link_local_ipv4_adapters,
        likely_dhcp_issue=likely_dhcp_issue,
        error=error,
    )
