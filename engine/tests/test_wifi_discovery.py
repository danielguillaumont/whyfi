"""Deterministic netsh Wi-Fi discovery scenarios."""

import subprocess

import pytest

from whyfi.diagnosis.engine import diagnose_baseline
from whyfi.diagnostics.windows import adapters, baseline, primary, wifi
from whyfi.diagnostics.windows.routes import DefaultRoute
from whyfi.models.diagnosis import DiagnosisCode
from whyfi.models.dns import DNSDiagnosticResult
from whyfi.models.local_config import LocalConfigResult
from whyfi.models.network import NetworkAdapter
from whyfi.models.probes import InternetReachabilityResult, PingResult


def mock_netsh(monkeypatch, output, *, code=0, stderr=""):
    def run(command, **kwargs):
        assert command == ["netsh.exe", "wlan", "show", "interfaces"]
        return subprocess.CompletedProcess(command, code, output, stderr)

    monkeypatch.setattr(wifi.subprocess, "run", run)


def test_disconnected_record_does_not_hide_connected_record(monkeypatch):
    mock_netsh(monkeypatch, """
    There are 2 interfaces on the system:
        Name : Wi-Fi
        State : disconnected

        Name : Wi-Fi 2
        State : connected
        SSID : Test:Network
        Signal : 84%
        Channel : 44
    """)

    result = wifi.get_wifi_connection()

    assert result.connected is True
    assert result.interface_name == "Wi-Fi 2"
    assert result.ssid == "Test:Network"
    assert result.signal_percent == 84
    assert result.channel == 44


@pytest.mark.parametrize("reverse", [False, True])
def test_primary_adapter_selects_correct_connected_interface(monkeypatch, reverse):
    records = [
        "Name : Wi-Fi\nState : connected\nSignal : 12%\nSSID : Other",
        "Name : Office Link\nState : connected\nSignal : 90%\nSSID : Office",
    ]
    mock_netsh(
        monkeypatch,
        "There are 2 interfaces on the system:\n"
        + "\n\n".join(reversed(records) if reverse else records),
    )

    result = wifi.get_wifi_connection("office link")

    assert result.connected is True
    assert result.interface_name == "Office Link"
    assert result.signal_percent == 90
    assert result.ssid == "Office"


@pytest.mark.parametrize("primary", [None, "Wi-Fi 3"])
def test_multiple_connected_interfaces_without_match_are_ambiguous(monkeypatch, primary):
    mock_netsh(monkeypatch, """
    There are 2 interfaces on the system:
    Name : Wi-Fi 2
    State : connected
    Name : Wi-Fi 1
    State : connected
    """)

    result = wifi.get_wifi_connection(primary)

    assert result.connected is None
    assert result.signal_percent is None
    assert "Wi-Fi 1, Wi-Fi 2" in result.error


def test_connected_sibling_does_not_supply_metrics_for_primary(monkeypatch):
    mock_netsh(monkeypatch, """
    There are 2 interfaces on the system:
    Name : Wi-Fi
    State : disconnected
    Name : Wi-Fi 2
    State : connected
    Signal : 20%
    """)

    result = wifi.get_wifi_connection("Wi-Fi")

    assert result.connected is None
    assert result.signal_percent is None
    assert "Wi-Fi 2" in result.error


@pytest.mark.parametrize("output", [
    "There are 2 interfaces on the system:\n"
    "Name : Wi-Fi\nState : disconnected\nName : Wi-Fi 2\nState : disconnected",
    "There is no wireless interface on the system.",
])
def test_no_connected_wifi_after_successful_discovery(monkeypatch, output):
    mock_netsh(monkeypatch, output)

    result = wifi.get_wifi_connection()

    assert result.connected is False
    assert result.error is None


@pytest.mark.parametrize("output", [
    "",
    "Name : Wi-Fi\nSignal : 80%",
    "State : disconnected",
    "Nom : Wi-Fi\nÉtat : déconnecté",
    "Name : Wi-Fi\nState : authenticating",
    "There are 2 interfaces on the system:\nName : Wi-Fi\nState : disconnected",
    "Name : Wi-Fi\nState : disconnected\n\nNom : Wi-Fi 2\nÉtat : connecté",
    "There are 2 interfaces on the system:\n"
    "Name : Wi-Fi\nState : disconnected\n\nNom : Wi-Fi 2\nÉtat : connecté",
    "There is 1 interface on the system:\nName : Wi-Fi",
])
def test_unrecognized_output_is_unavailable(monkeypatch, output):
    mock_netsh(monkeypatch, output)

    result = wifi.get_wifi_connection()

    assert result.connected is None
    assert result.error


@pytest.mark.parametrize(("wlan_name", "expected_type", "diagnosis_code"), [
    ("Office Ethernet", "wifi", DiagnosisCode.WIFI_ISSUE),
    ("Secondary Wi-Fi", "ethernet", DiagnosisCode.UNSTABLE_CONNECTION),
])
def test_baseline_matches_wlan_to_primary_even_with_misleading_name(
    monkeypatch, wlan_name, expected_type, diagnosis_code
):
    alias = "Office Ethernet"
    gateway = "192.0.2.1"
    monkeypatch.setattr(
        primary, "get_default_route",
        lambda: DefaultRoute(alias, 7, gateway, 0, 25, 25),
    )
    monkeypatch.setattr(
        primary, "get_network_adapters",
        lambda: [NetworkAdapter(
            alias, adapters._infer_adapter_type(alias), True, False,
            ipv4_addresses=["192.0.2.2"],
        )],
    )
    monkeypatch.setattr(baseline, "check_local_config", lambda: LocalConfigResult(True))
    monkeypatch.setattr(
        baseline, "ping_host", lambda target: PingResult(target, True, 4, 3, 25.0)
    )
    monkeypatch.setattr(
        baseline, "check_internet_reachability", lambda: InternetReachabilityResult(True, 2, 2)
    )
    monkeypatch.setattr(
        baseline, "check_dns", lambda **kwargs: DNSDiagnosticResult(True, None, None)
    )
    mock_netsh(
        monkeypatch,
        f"There is 1 interface on the system:\nName : {wlan_name}\n"
        "Description : Wireless LAN\nState : connected\nSignal : 30%",
    )

    result = baseline.run_baseline_diagnostics()

    assert result.connection.adapter_type == expected_type
    assert diagnose_baseline(result).code == diagnosis_code
    if expected_type == "wifi":
        assert result.wifi.interface_name == alias
        assert result.wifi.signal_percent == 30
    else:
        assert result.wifi is None
    assert result.collection_errors == []


@pytest.mark.parametrize("code", [0, 1])
def test_netsh_error_preserves_details(monkeypatch, code):
    mock_netsh(monkeypatch, "Name : Wi-Fi\nState : disconnected", code=code, stderr="Access denied")

    result = wifi.get_wifi_connection()

    assert result.connected is None
    assert "Access denied" in result.error


@pytest.mark.parametrize("error", [
    subprocess.TimeoutExpired("netsh.exe", 10),
    FileNotFoundError("netsh.exe is missing"),
])
def test_netsh_timeout_or_launch_failure_is_unavailable(monkeypatch, error):
    def run(*args, **kwargs):
        raise error

    monkeypatch.setattr(wifi.subprocess, "run", run)

    result = wifi.get_wifi_connection()

    assert result.connected is None
    assert result.error
