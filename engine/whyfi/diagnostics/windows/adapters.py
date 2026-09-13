"""Windows network adapter discovery for WHYFI."""

from __future__ import annotations

import ipaddress
import socket

import psutil

from whyfi.models.network import NetworkAdapter


def _infer_adapter_type(name: str) -> str:
    """Infer a simple adapter type from the Windows interface name."""

    normalized = name.lower()

    if "loopback" in normalized:
        return "loopback"

    if "wi-fi" in normalized or "wifi" in normalized or "wireless" in normalized or "wlan" in normalized:
        return "wifi"

    if "ethernet" in normalized:
        return "ethernet"

    if "bluetooth" in normalized:
        return "bluetooth"

    return "other"


def _is_loopback_address(address: str) -> bool:
    """Return True when an IP address is a loopback address."""

    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def get_network_adapters() -> list[NetworkAdapter]:
    """Discover network adapters and their basic configuration."""

    interface_addresses = psutil.net_if_addrs()
    interface_stats = psutil.net_if_stats()

    adapters: list[NetworkAdapter] = []

    for name, addresses in interface_addresses.items():
        ipv4_addresses: list[str] = []
        ipv6_addresses: list[str] = []
        mac_address: str | None = None

        for address in addresses:
            if address.family == socket.AF_INET:
                ipv4_addresses.append(address.address)

            elif address.family == socket.AF_INET6:
                ipv6_address = address.address.split("%", 1)[0]
                ipv6_addresses.append(ipv6_address)

            elif address.family == psutil.AF_LINK:
                mac_address = address.address or None

        stats = interface_stats.get(name)

        is_up = stats.isup if stats is not None else False
        speed_mbps = stats.speed if stats is not None and stats.speed > 0 else None
        mtu = stats.mtu if stats is not None else None

        ip_addresses = ipv4_addresses + ipv6_addresses

        is_loopback = (
            _infer_adapter_type(name) == "loopback"
            or (
                bool(ip_addresses)
                and all(_is_loopback_address(ip) for ip in ip_addresses)
            )
        )

        adapters.append(
            NetworkAdapter(
                name=name,
                adapter_type=_infer_adapter_type(name),
                is_up=is_up,
                is_loopback=is_loopback,
                ipv4_addresses=ipv4_addresses,
                ipv6_addresses=ipv6_addresses,
                mac_address=mac_address,
                speed_mbps=speed_mbps,
                mtu=mtu,
            )
        )

    adapters.sort(
        key=lambda adapter: (
            not adapter.is_up,
            adapter.is_loopback,
            not bool(adapter.ipv4_addresses),
            adapter.name.lower(),
        )
    )

    return adapters
