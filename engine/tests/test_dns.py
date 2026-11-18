"""Tests for configured DNS resolution and optional public comparisons."""

import json
import subprocess
import sys

import dns.exception
import dns.message
import dns.resolver
import pytest

from whyfi import __main__ as cli
from whyfi.diagnosis.engine import diagnose_baseline
from whyfi.diagnostics.common import dns as diagnostic
from whyfi.diagnostics.windows import baseline
from whyfi.diagnostics.windows import dns as windows_dns
from whyfi.models.diagnostic import BaselineDiagnosticResult
from whyfi.models.diagnosis import DiagnosisCode
from whyfi.models.dns import DNSQueryResult, SystemDNSQueryResult
from whyfi.models.local_config import LocalConfigResult
from whyfi.models.network import PrimaryConnection
from whyfi.models.probes import InternetReachabilityResult, PingResult


def mock_dns(monkeypatch, configured, outcomes):
    calls = []
    monkeypatch.setattr(diagnostic, "get_system_dns_servers", lambda index: configured)

    def query(*, hostname, resolver_address):
        calls.append(resolver_address)
        outcome = outcomes[resolver_address]
        return DNSQueryResult(
            hostname, resolver_address, outcome,
            error=None if outcome is True else "Lookup error",
        )

    monkeypatch.setattr(diagnostic, "query_dns", query)
    return calls


@pytest.mark.parametrize(("configured_outcomes", "expected_health", "code"), [
    ((False, True), True, DiagnosisCode.UNKNOWN),
    ((True, True), True, DiagnosisCode.HEALTHY),
    ((False, False), False, DiagnosisCode.DNS_ISSUE),
    ((False, None), None, DiagnosisCode.UNKNOWN),
    ((None, True), True, DiagnosisCode.UNKNOWN),
    ((True, None), True, DiagnosisCode.UNKNOWN),
])
def test_configured_dns_results_drive_baseline(
    monkeypatch, configured_outcomes, expected_health, code
):
    servers = ["192.0.2.53", "192.0.2.54"]
    calls = mock_dns(
        monkeypatch, servers,
        {**dict(zip(servers, configured_outcomes)), "1.1.1.1": True, "8.8.8.8": None},
    )

    result = diagnostic.check_dns()
    diagnosis = diagnose_baseline(BaselineDiagnosticResult(
        connection=PrimaryConnection("LAN", "ethernet", 7, "192.0.2.2", "192.0.2.1", True),
        gateway=PingResult("192.0.2.1", True, 4, 4, 0.0),
        internet=InternetReachabilityResult(True, 2, 2),
        dns=result,
        completed=True,
    ))

    assert result.healthy is expected_health
    assert result.measurements_complete is (None not in configured_outcomes)
    assert result.default_resolver == servers[0]
    assert result.default_query is result.configured_queries[0]
    assert [query.success for query in result.configured_queries] == list(configured_outcomes)
    assert calls == servers + (["1.1.1.1", "8.8.8.8"] if expected_health is False else [])
    assert result.likely_dns_issue is (expected_health is False)
    assert diagnosis.code is code
    if expected_health is True and configured_outcomes != (True, True):
        assert diagnosis.title == "DNS works through some configured resolvers."
        assert "resolved the test name: 1/2" in " ".join(diagnosis.evidence)
    if code is DiagnosisCode.UNKNOWN:
        assert diagnosis.confidence is None
    elif code is DiagnosisCode.HEALTHY:
        assert diagnosis.confidence == 96


@pytest.mark.parametrize(("packet_loss", "code"), [
    (0.0, "unknown"),
    (25.0, "unstable_connection"),
])
def test_partial_dns_collection_reaches_stream_without_masking_gateway_evidence(
    monkeypatch, capsys, packet_loss, code
):
    gateway = "192.0.2.1"
    first, second = "192.0.2.53", "192.0.2.54"
    mock_dns(monkeypatch, [first, second], {first: None, second: True})
    monkeypatch.setattr(baseline, "check_dns", diagnostic.check_dns)
    monkeypatch.setattr(
        baseline, "get_primary_connection",
        lambda: PrimaryConnection("LAN", "ethernet", 7, "192.0.2.2", gateway, True),
    )
    monkeypatch.setattr(baseline, "check_local_config", lambda: LocalConfigResult(True))
    monkeypatch.setattr(baseline, "get_wifi_connection", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        baseline, "ping_host",
        lambda target: PingResult(target, True, 4, 4 if not packet_loss else 3, packet_loss),
    )
    monkeypatch.setattr(
        baseline, "check_internet_reachability", lambda: InternetReachabilityResult(True, 2, 2)
    )
    monkeypatch.setattr(sys, "argv", ["whyfi", "--stream-json"])

    cli.main()

    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result["diagnosis"]["code"] == code
    assert (result["diagnosis"]["confidence"] is None) is (code == "unknown")
    assert result["details"]["completed"] is False
    dns_details = result["details"]["dns"]
    assert dns_details["healthy"] is True
    assert [query["success"] for query in dns_details["configured_queries"]] == [None, True]
    assert result["details"]["collection_errors"] == [
        {"check": "dns", "message": "Lookup error", "target": first},
    ]


def test_duplicate_resolvers_and_unavailable_public_comparison(monkeypatch):
    calls = mock_dns(
        monkeypatch,
        ["2001:0DB8::53", "2001:db8::53", "1.1.1.1", "1.1.1.1"],
        {"2001:0DB8::53": False, "1.1.1.1": False, "8.8.8.8": None},
    )

    result = diagnostic.check_dns()

    assert calls == ["2001:0DB8::53", "1.1.1.1", "8.8.8.8"]
    assert result.healthy is False
    assert len(result.configured_queries) == 2
    assert [query.success for query in result.alternate_queries] == [None]


def test_custom_dns_name_is_never_sent_to_public_comparison_resolvers(monkeypatch):
    calls = mock_dns(monkeypatch, ["192.0.2.53"], {"192.0.2.53": False})

    result = diagnostic.check_dns("service.internal.example")

    assert calls == ["192.0.2.53"]
    assert result.alternate_queries == []


def test_known_empty_configuration_differs_from_discovery_failure(monkeypatch):
    calls = mock_dns(monkeypatch, [], {})
    empty = diagnostic.check_dns()

    def fail(index):
        raise PermissionError("access denied")

    monkeypatch.setattr(diagnostic, "get_system_dns_servers", fail)
    unavailable = diagnostic.check_dns()

    assert calls == []
    assert empty.healthy is False
    assert empty.default_query is None
    assert unavailable.healthy is None
    assert "access denied" in unavailable.error


def test_windows_dns_configuration_prefers_primary_and_scopes_ipv6(monkeypatch):
    rows = [
        {"index": 3, "metric": 5, "family": 2, "servers": ["192.0.2.53"]},
        {"index": 7, "metric": 15, "family": 23, "servers": ["fe80::53"]},
        {"index": 7, "metric": 15, "family": 2, "servers": ["198.51.100.53", "198.51.100.54"]},
        {"index": 9, "metric": 50, "family": 23, "servers": [
            "FEC0:0:0:FFFF::1%1", "fec0:0:0:ffff::2%1", "fec0:0:0:ffff::3%1",
        ]},
    ]
    monkeypatch.setattr(diagnostic.sys, "platform", "win32")
    monkeypatch.setattr(
        diagnostic.subprocess, "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(
            cmd, 0, json.dumps({"interfaces": [dict(row, alias="Test") for row in rows]}), ""
        ),
    )

    assert diagnostic.get_system_dns_servers(7) == [
        "198.51.100.53", "198.51.100.54", "fe80::53%7", "192.0.2.53",
        "FEC0:0:0:FFFF::1%1", "fec0:0:0:ffff::2%1", "fec0:0:0:ffff::3%1",
    ]


@pytest.mark.parametrize(("stdout", "stderr", "exit_code"), [
    ("[]", "Windows returned no DNS configuration record for interface 7:2.", 1),
    ("[]", "", 0),
    ('[{"index":3,"family":2,"metric":1,"servers":["192.0.2.53"]}]', "", 0),
    ('[{"index":7,"family":2,"metric":1,"servers":[null]}]', "", 0),
])
def test_incomplete_windows_enumeration_cannot_confirm_empty_dns(
    monkeypatch, stdout, stderr, exit_code
):
    monkeypatch.setattr(diagnostic.sys, "platform", "win32")
    monkeypatch.setattr(
        diagnostic.subprocess, "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, exit_code, stdout, stderr),
    )

    result = diagnostic.check_dns(primary_interface_index=7)

    assert result.healthy is None
    assert not result.measurements_complete
    assert not result.likely_dns_issue
    assert result.configured_queries == []
    assert result.error


def test_complete_empty_legacy_inventory_for_primary_confirms_no_configured_dns(monkeypatch):
    row = {"index": 7, "alias": "LAN", "family": 2, "metric": 10, "servers": []}
    monkeypatch.setattr(diagnostic.sys, "platform", "win32")
    monkeypatch.setattr(
        diagnostic.subprocess, "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(
            cmd, 0, json.dumps({"interfaces": [row]}), ""
        ),
    )

    result = diagnostic.check_dns(primary_interface_index=7)

    assert result.healthy is False
    assert result.measurements_complete
    assert result.configured_queries == []


@pytest.mark.parametrize(("error", "expected"), [
    (dns.resolver.NXDOMAIN(), False),
    (dns.resolver.NoAnswer(), False),
    (dns.exception.Timeout(), False),
    (PermissionError("socket denied"), None),
    (dns.resolver.NoNameservers(
        request=dns.message.make_query("example.com", "A"),
        errors=[("192.0.2.53", False, 53, "SERVFAIL", object())],
    ), False),
    (dns.resolver.NoNameservers(
        request=dns.message.make_query("example.com", "A"),
        errors=[("192.0.2.53", False, 53, OSError("network unreachable"), None)],
    ), None),
])
def test_dns_lookup_distinguishes_failed_from_unavailable(monkeypatch, error, expected):
    def resolve(self, hostname, record_type, *, search):
        assert hostname == "example.com"
        assert record_type == "A"
        assert search is False
        raise error

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", resolve)

    result = diagnostic.query_dns("example.com", "192.0.2.53")

    assert result.success is expected
    assert result.error
    assert result.addresses == []
    assert result.latency_ms is None


def windows_fixture(monkeypatch, extra_rows=(), extra_routes=(), policy=False, client=True):
    rows = [{"index": 20, "alias": "Wi-Fi", "family": 2, "metric": 25,
             "servers": ["192.168.50.1"]}, *extra_rows]
    routes = [{"index": 20, "prefix": "192.168.50.0/24"}, *extra_routes]
    monkeypatch.setattr(diagnostic, "_windows_json", lambda script: {
        "interfaces": rows, "routes": routes, "policy": policy,
    })
    monkeypatch.setattr(windows_dns, "query_windows_dns_client", lambda:
                        SystemDNSQueryResult("example.com.", client))
    calls = []

    def resolve(*, hostname, resolver_address):
        calls.append(resolver_address)
        return DNSQueryResult(hostname, resolver_address, True, 43.28)

    monkeypatch.setattr(diagnostic, "query_dns", resolve)
    return calls


def dns_diagnosis(dns, gateway=True, internet=True):
    return diagnose_baseline(BaselineDiagnosticResult(
        connection=PrimaryConnection("Wi-Fi", "wifi", 20, "192.168.50.211", "192.168.50.1", True),
        gateway=PingResult("192.168.50.1", gateway, 4, 4 if gateway else 0,
                           0.0 if gateway else 100.0),
        internet=InternetReachabilityResult(internet, 2, 2 if internet else 0),
        local_config=LocalConfigResult(True),
        dns=dns,
        completed=True,
    ))


@pytest.mark.parametrize("mode", ["--json", "--stream-json"])
def test_real_world_virtual_ipv6_entries_stay_in_details(monkeypatch, capsys, mode):
    triplet = [f"fec0:0:0:ffff::{i}" for i in (1, 2, 3)]
    rows = [
        {"index": index, "alias": alias, "family": 23, "metric": 30, "servers": triplet}
        for index, alias in [
            (1, "Loopback"), (5, "VMware VMnet1"), (12, "VMware VMnet8"),
            (17, "VMware VMnet4"), (78, "WSL"),
        ]
    ]
    calls = windows_fixture(monkeypatch, rows, [
        {"index": 1, "prefix": "::1/128"}, {"index": 5, "prefix": "fe80::/64"},
        {"index": 12, "prefix": "fe80::/64"}, {"index": 17, "prefix": "fe80::/64"},
        {"index": 78, "prefix": "fe80::/64"},
    ])
    monkeypatch.setattr(baseline, "get_primary_connection", lambda: PrimaryConnection(
        "Wi-Fi", "wifi", 20, "192.168.50.211", "192.168.50.1", True,
    ))
    monkeypatch.setattr(baseline, "check_local_config", lambda: LocalConfigResult(True))
    monkeypatch.setattr(baseline, "get_wifi_connection", lambda *args, **kwargs: None)
    monkeypatch.setattr(baseline, "ping_host", lambda target: PingResult(target, True, 4, 4, 0.0))
    monkeypatch.setattr(baseline, "check_internet_reachability",
                        lambda: InternetReachabilityResult(True, 2, 2))
    monkeypatch.setattr(sys, "argv", ["whyfi", mode])
    cli.main()
    output = capsys.readouterr().out
    event = json.loads(output if mode == "--json" else output.splitlines()[-1])
    assert event["diagnosis"]["code"] == "healthy"
    details = event["details"]["dns"]
    assert event["details"]["completed"]
    assert calls == ["192.168.50.1"]
    assert details["default_resolver"] == "192.168.50.1"
    assert details["system_query"]["success"] is True
    other = [item for item in details["resolver_evidence"] if not item["primary"]]
    assert {item["interface_index"] for item in other} == {1, 5, 12, 17, 78}
    assert len(other) == 15
    assert all(item["provenance"] == "unknown" and not item["route_on_interface"] for item in other)


@pytest.mark.parametrize("direct_status", [False, None])
def test_primary_ipv6_and_secondary_success_preserve_incomplete_evidence(monkeypatch, direct_status):
    row = {"index": 20, "alias": "Wi-Fi", "family": 23, "metric": 25,
           "servers": ["fe80::53", "fec0:0:0:ffff::1"]}
    windows_fixture(monkeypatch, [row], [
        {"index": 20, "prefix": "fe80::/64"}, {"index": 5, "prefix": "fe80::/64"},
        {"index": 20, "prefix": "fec0:0:0:ffff::/64"},
    ])
    monkeypatch.setattr(diagnostic, "query_dns", lambda hostname, resolver_address: DNSQueryResult(
        hostname, resolver_address, True if resolver_address == "fe80::53%20" else direct_status,
    ))
    result = windows_dns.check_dns(primary_interface_index=20)
    assert result.attribution_error is None
    assert result.default_query.success is direct_status
    assert [query.success for query in result.configured_queries] == [direct_status, True, direct_status]
    assert [item.scope for item in result.resolver_evidence] == [None, "20", None]
    assert dns_diagnosis(result).code is DiagnosisCode.UNKNOWN


@pytest.mark.parametrize("alias", ["VMware VMnet1", "WSL", "VPN"])
def test_isolated_off_interface_route_does_not_block_healthy_dns(monkeypatch, alias):
    row = {"index": 5, "alias": alias, "family": 2, "metric": 30,
           "servers": ["192.168.180.53"]}
    calls = windows_fixture(monkeypatch, [row], [
        {"index": 5, "prefix": "192.168.180.0/24"},
    ])

    result = windows_dns.check_dns(primary_interface_index=20)
    assert result.attribution_error is None
    assert result.system_query.success is True
    assert calls == ["192.168.50.1"]
    assert [query.resolver for query in result.configured_queries] == calls
    other, = [item for item in result.resolver_evidence if not item.primary]
    assert (other.interface_index, other.interface_alias) == (5, alias)
    assert (other.resolver, other.route_on_interface) == ("192.168.180.53", True)
    assert dns_diagnosis(result).code is DiagnosisCode.HEALTHY


@pytest.mark.parametrize("case", [
    "vpn", "policy", "policy_unknown", "partial", "routes_missing",
    "client_unavailable", "conflict", "missing_primary",
])
def test_uncertain_dns_does_not_hide_independent_failures(monkeypatch, case):
    row = {"index": 3, "alias": "VPN", "family": 2, "metric": 5, "servers": ["10.1.0.53"]}
    windows_fixture(
        monkeypatch,
        [dict(row, servers=None)] if case == "partial" else [row] if case == "vpn" else [],
        [
            {"index": 3, "prefix": "10.1.0.0/24"},
            {"index": 3, "prefix": "192.168.50.1/32"},
        ] if case == "vpn" else [{"index": 20}] if case == "routes_missing" else [],
        policy=None if case == "policy_unknown" else case == "policy",
        client=None if case == "client_unavailable" else case != "conflict",
    )
    result = windows_dns.check_dns(primary_interface_index=99 if case == "missing_primary" else 20)
    diagnosis = dns_diagnosis(result)
    assert diagnosis.code is DiagnosisCode.UNKNOWN and diagnosis.confidence is None
    assert dns_diagnosis(result, gateway=False, internet=False).code is DiagnosisCode.GATEWAY_ISSUE
    assert dns_diagnosis(result, internet=False).code is DiagnosisCode.INTERNET_ISSUE


@pytest.mark.parametrize(("client", "expected"), [(True, DiagnosisCode.UNKNOWN), (False, DiagnosisCode.DNS_ISSUE)])
def test_dns_client_success_alone_does_not_prove_live_reachability(monkeypatch, client, expected):
    windows_fixture(monkeypatch, client=client)
    monkeypatch.setattr(diagnostic, "query_dns", lambda hostname, resolver_address:
                        DNSQueryResult(hostname, resolver_address, False, error="SERVFAIL"))
    result = windows_dns.check_dns(primary_interface_index=20)
    assert result.system_query.success is client
    assert result.likely_dns_issue is (not client)
    assert dns_diagnosis(result).code is expected


def test_more_specific_off_interface_route_blocks_primary_direct_probe(monkeypatch):
    calls = windows_fixture(monkeypatch, extra_routes=[
        {"index": 3, "prefix": "192.168.50.1/32"},
    ])
    result = windows_dns.check_dns(primary_interface_index=20)
    assert calls == []
    assert result.default_query.success is None
    assert "ambiguous Windows route" in result.attribution_error
    assert dns_diagnosis(result).code is DiagnosisCode.UNKNOWN


@pytest.mark.parametrize(("payload", "success"), [
    ({"addresses": ["192.0.2.1"], "code": None}, True),
    ({"addresses": [], "code": "DNS_ERROR_RCODE_NAME_ERROR"}, False),
    ({"addresses": [], "code": "AccessDenied"}, None),
    ({"addresses": ["not an IP"], "code": None}, None),
    ({"addresses": ["192.0.2.1"]}, None),
])
def test_windows_client_lookup_is_bounded_and_has_no_explicit_upstream(monkeypatch, payload, success):
    def run(script, *, timeout):
        assert timeout == 8
        assert "-DnsOnly -NoHostsFile" in script
        assert "-Server " not in script
        return payload

    monkeypatch.setattr(diagnostic, "_windows_json", run)
    assert windows_dns.query_windows_dns_client().success is success


def test_windows_client_subprocess_timeout_is_unavailable(monkeypatch):
    def timeout(script, *, timeout):
        raise subprocess.TimeoutExpired("powershell", timeout)

    monkeypatch.setattr(diagnostic, "_windows_json", timeout)
    result = windows_dns.query_windows_dns_client()
    assert result.success is None
    assert "collection deadline" in result.error


def test_windows_inventory_timeout_keeps_command_out_of_diagnostic_evidence(monkeypatch):
    def timeout(script):
        raise subprocess.TimeoutExpired(["powershell.exe", "-Command", script], 10)

    monkeypatch.setattr(diagnostic, "_windows_json", timeout)
    monkeypatch.setattr(
        windows_dns, "query_windows_dns_client",
        lambda: SystemDNSQueryResult("example.com.", True),
    )

    result = windows_dns.check_dns(primary_interface_index=20)

    assert result.attribution_error == (
        "Windows DNS interface inventory unavailable: Windows DNS interface inventory timed out."
    )
    assert result.system_query.success is True
    assert not result.measurements_complete
