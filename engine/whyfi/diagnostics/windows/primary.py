"""Primary Windows connection discovery for WHYFI."""

from __future__ import annotations

import ipaddress

from whyfi.diagnostics.windows.adapters import get_network_adapters
from whyfi.diagnostics.windows.routes import get_default_route
from whyfi.models.network import NetworkAdapter, PrimaryConnection


def _select_ipv4(adapter: NetworkAdapter) -> str | None:
    """Choose the most useful IPv4 address assigned to an adapter."""

    for address in adapter.ipv4_addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue

        if not parsed.is_loopback and not parsed.is_link_local:
            return address

    return adapter.ipv4_addresses[0] if adapter.ipv4_addresses else None


def get_primary_connection() -> PrimaryConnection | None:
    """Return the adapter Windows is using for its preferred default route."""

    route = get_default_route()

    if route is None:
        return None

    adapters = get_network_adapters()

    adapter = next(
        (
            candidate
            for candidate in adapters
            if candidate.name.casefold() == route.interface_alias.casefold()
        ),
        None,
    )

    if adapter is None:
        return None

    return PrimaryConnection(
        adapter_name=adapter.name,
        adapter_type=adapter.adapter_type,
        interface_index=route.interface_index,
        ipv4_address=_select_ipv4(adapter),
        gateway=route.gateway,
        is_up=adapter.is_up,
        speed_mbps=adapter.speed_mbps,
        mtu=adapter.mtu,
    )
