"""Local IP configuration tests for WHYFI."""

from whyfi.diagnostics.windows import local_config
from whyfi.models.network import NetworkAdapter


def make_adapter(
    name: str,
    ipv4_addresses: list[str],
    is_up: bool = True,
) -> NetworkAdapter:
    """Create a representative network adapter."""

    return NetworkAdapter(
        name=name,
        adapter_type="wifi",
        is_up=is_up,
        is_loopback=False,
        ipv4_addresses=ipv4_addresses,
    )


def test_healthy_private_ipv4(monkeypatch) -> None:
    """A normal private IPv4 address should be considered healthy."""

    adapters = [
        make_adapter(
            name="Wi-Fi",
            ipv4_addresses=["192.168.50.211"],
        ),
    ]

    monkeypatch.setattr(
        local_config,
        "get_network_adapters",
        lambda: adapters,
    )

    result = local_config.check_local_config()

    assert result.healthy is True
    assert result.likely_dhcp_issue is False
    assert result.usable_ipv4_adapters == ["Wi-Fi"]


def test_link_local_ipv4_indicates_dhcp_issue(monkeypatch) -> None:
    """A 169.254 address should suggest DHCP configuration failure."""

    adapters = [
        make_adapter(
            name="Wi-Fi",
            ipv4_addresses=["169.254.44.10"],
        ),
    ]

    monkeypatch.setattr(
        local_config,
        "get_network_adapters",
        lambda: adapters,
    )

    result = local_config.check_local_config()

    assert result.healthy is False
    assert result.likely_dhcp_issue is True
    assert result.link_local_ipv4_adapters == ["Wi-Fi"]


def test_virtual_adapter_does_not_hide_physical_dhcp_issue(
    monkeypatch,
) -> None:
    """A healthy virtual adapter should not mask a broken physical adapter."""

    adapters = [
        make_adapter(
            name="vEthernet (WSL)",
            ipv4_addresses=["172.31.64.1"],
        ),
        make_adapter(
            name="Wi-Fi",
            ipv4_addresses=["169.254.44.10"],
        ),
    ]

    monkeypatch.setattr(
        local_config,
        "get_network_adapters",
        lambda: adapters,
    )

    result = local_config.check_local_config()

    assert result.healthy is False
    assert result.likely_dhcp_issue is True
    assert result.active_adapters == ["Wi-Fi"]


def test_no_active_physical_adapter(monkeypatch) -> None:
    """No active physical adapter should produce an unhealthy result."""

    adapters = [
        make_adapter(
            name="Wi-Fi",
            ipv4_addresses=[],
            is_up=False,
        ),
    ]

    monkeypatch.setattr(
        local_config,
        "get_network_adapters",
        lambda: adapters,
    )

    result = local_config.check_local_config()

    assert result.healthy is False
    assert result.likely_dhcp_issue is False
    assert result.active_adapters == []
    assert result.error == "No active physical network adapters were found."
