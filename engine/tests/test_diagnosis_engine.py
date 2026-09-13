"""Scenario tests for WHYFI's evidence-based diagnosis engine."""

from whyfi.diagnosis.engine import diagnose_baseline
from whyfi.models.diagnostic import BaselineDiagnosticResult
from whyfi.models.diagnosis import DiagnosisCode
from whyfi.models.dns import DNSDiagnosticResult, DNSQueryResult
from whyfi.models.network import PrimaryConnection
from whyfi.models.probes import InternetReachabilityResult, PingResult


def make_connection() -> PrimaryConnection:
    """Create a representative healthy primary connection."""

    return PrimaryConnection(
        adapter_name="Wi-Fi",
        adapter_type="wifi",
        interface_index=17,
        ipv4_address="192.168.50.211",
        gateway="192.168.50.1",
        is_up=True,
        speed_mbps=286,
        mtu=1500,
    )


def make_ping(
    target: str,
    reachable: bool = True,
) -> PingResult:
    """Create a representative ping result."""

    if reachable:
        return PingResult(
            target=target,
            reachable=True,
            packets_sent=4,
            packets_received=4,
            packet_loss_percent=0.0,
            min_latency_ms=2.0,
            average_latency_ms=4.0,
            max_latency_ms=6.0,
        )

    return PingResult(
        target=target,
        reachable=False,
        packets_sent=4,
        packets_received=0,
        packet_loss_percent=100.0,
        error="No ICMP replies received.",
    )


def make_internet(
    reachable: bool = True,
) -> InternetReachabilityResult:
    """Create a representative direct-IP internet result."""

    if reachable:
        probes = [
            make_ping("1.1.1.1"),
            make_ping("8.8.8.8"),
        ]

        return InternetReachabilityResult(
            reachable=True,
            targets_tested=2,
            targets_reachable=2,
            probes=probes,
        )

    probes = [
        make_ping("1.1.1.1", reachable=False),
        make_ping("8.8.8.8", reachable=False),
    ]

    return InternetReachabilityResult(
        reachable=False,
        targets_tested=2,
        targets_reachable=0,
        probes=probes,
        error="No public IP targets responded.",
    )


def make_dns(
    healthy: bool = True,
    likely_dns_issue: bool = False,
) -> DNSDiagnosticResult:
    """Create a representative DNS diagnostic result."""

    if healthy:
        default_query = DNSQueryResult(
            hostname="example.com",
            resolver="192.168.50.1",
            success=True,
            latency_ms=20.0,
            addresses=["93.184.216.34"],
        )

        return DNSDiagnosticResult(
            healthy=True,
            default_resolver="192.168.50.1",
            default_query=default_query,
            alternate_queries=[],
            likely_dns_issue=False,
        )

    default_query = DNSQueryResult(
        hostname="example.com",
        resolver="192.168.50.1",
        success=False,
        error="DNS query timed out.",
    )

    alternate_query = DNSQueryResult(
        hostname="example.com",
        resolver="1.1.1.1",
        success=True,
        latency_ms=20.0,
        addresses=["93.184.216.34"],
    )

    return DNSDiagnosticResult(
        healthy=False,
        default_resolver="192.168.50.1",
        default_query=default_query,
        alternate_queries=[alternate_query],
        likely_dns_issue=likely_dns_issue,
    )


def test_healthy_connection() -> None:
    """Healthy measurements should produce a healthy diagnosis."""

    baseline = BaselineDiagnosticResult(
        connection=make_connection(),
        gateway=make_ping("192.168.50.1"),
        internet=make_internet(),
        dns=make_dns(),
        completed=True,
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.HEALTHY
    assert diagnosis.confidence >= 90


def test_no_connection() -> None:
    """Missing primary connection should produce NO_CONNECTION."""

    baseline = BaselineDiagnosticResult(
        connection=None,
        gateway=None,
        internet=None,
        dns=None,
        completed=False,
        error="No primary network connection was found.",
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.NO_CONNECTION


def test_gateway_failure() -> None:
    """Failed gateway and internet probes should indicate a gateway issue."""

    baseline = BaselineDiagnosticResult(
        connection=make_connection(),
        gateway=make_ping("192.168.50.1", reachable=False),
        internet=make_internet(reachable=False),
        dns=make_dns(healthy=False),
        completed=True,
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.GATEWAY_ISSUE


def test_internet_failure() -> None:
    """Healthy gateway with failed public IP probes should indicate upstream failure."""

    baseline = BaselineDiagnosticResult(
        connection=make_connection(),
        gateway=make_ping("192.168.50.1"),
        internet=make_internet(reachable=False),
        dns=make_dns(healthy=False),
        completed=True,
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.INTERNET_ISSUE


def test_dns_failure() -> None:
    """Working direct-IP internet with failed default DNS should indicate DNS failure."""

    baseline = BaselineDiagnosticResult(
        connection=make_connection(),
        gateway=make_ping("192.168.50.1"),
        internet=make_internet(),
        dns=make_dns(
            healthy=False,
            likely_dns_issue=True,
        ),
        completed=True,
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.DNS_ISSUE
    assert diagnosis.confidence >= 90
