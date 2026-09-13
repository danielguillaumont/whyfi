"""Wi-Fi diagnosis scenario tests for WHYFI."""

from whyfi.diagnosis.engine import diagnose_baseline
from whyfi.models.diagnostic import BaselineDiagnosticResult
from whyfi.models.diagnosis import DiagnosisCode
from whyfi.models.dns import DNSDiagnosticResult, DNSQueryResult
from whyfi.models.network import PrimaryConnection
from whyfi.models.probes import InternetReachabilityResult, PingResult
from whyfi.models.wifi import WiFiConnection


def make_connection() -> PrimaryConnection:
    """Create a representative Wi-Fi connection."""

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


def make_ping(packet_loss_percent: float = 0.0) -> PingResult:
    """Create a reachable gateway ping result."""

    packets_received = round(
        4 * (1 - packet_loss_percent / 100)
    )

    return PingResult(
        target="192.168.50.1",
        reachable=True,
        packets_sent=4,
        packets_received=packets_received,
        packet_loss_percent=packet_loss_percent,
        min_latency_ms=2.0,
        average_latency_ms=4.0,
        max_latency_ms=6.0,
    )


def make_internet() -> InternetReachabilityResult:
    """Create a healthy internet result."""

    probes = [
        PingResult(
            target="1.1.1.1",
            reachable=True,
            packets_sent=4,
            packets_received=4,
            packet_loss_percent=0.0,
            min_latency_ms=15.0,
            average_latency_ms=18.0,
            max_latency_ms=21.0,
        ),
        PingResult(
            target="8.8.8.8",
            reachable=True,
            packets_sent=4,
            packets_received=4,
            packet_loss_percent=0.0,
            min_latency_ms=14.0,
            average_latency_ms=17.0,
            max_latency_ms=20.0,
        ),
    ]

    return InternetReachabilityResult(
        reachable=True,
        targets_tested=2,
        targets_reachable=2,
        probes=probes,
    )


def make_dns() -> DNSDiagnosticResult:
    """Create a healthy DNS result."""

    query = DNSQueryResult(
        hostname="example.com",
        resolver="192.168.50.1",
        success=True,
        latency_ms=20.0,
        addresses=["93.184.216.34"],
    )

    return DNSDiagnosticResult(
        healthy=True,
        default_resolver="192.168.50.1",
        default_query=query,
        alternate_queries=[],
        likely_dns_issue=False,
    )


def make_wifi(signal_percent: int) -> WiFiConnection:
    """Create a connected Wi-Fi result."""

    return WiFiConnection(
        connected=True,
        interface_name="Wi-Fi",
        ssid="TestNetwork",
        signal_percent=signal_percent,
        radio_type="802.11ax",
        channel=1,
        receive_rate_mbps=286.8,
        transmit_rate_mbps=286.8,
    )


def test_weak_wifi_with_packet_loss_is_wifi_issue() -> None:
    """Weak Wi-Fi plus local packet loss should identify Wi-Fi as the cause."""

    baseline = BaselineDiagnosticResult(
        connection=make_connection(),
        gateway=make_ping(packet_loss_percent=25.0),
        internet=make_internet(),
        dns=make_dns(),
        wifi=make_wifi(signal_percent=30),
        completed=True,
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.WIFI_ISSUE
    assert diagnosis.confidence >= 90


def test_weak_wifi_without_packet_loss_is_not_enough() -> None:
    """Weak signal alone should not create a Wi-Fi failure diagnosis."""

    baseline = BaselineDiagnosticResult(
        connection=make_connection(),
        gateway=make_ping(packet_loss_percent=0.0),
        internet=make_internet(),
        dns=make_dns(),
        wifi=make_wifi(signal_percent=30),
        completed=True,
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.HEALTHY


def test_good_wifi_with_packet_loss_remains_generic_instability() -> None:
    """Strong Wi-Fi plus local loss should remain a generic local issue."""

    baseline = BaselineDiagnosticResult(
        connection=make_connection(),
        gateway=make_ping(packet_loss_percent=25.0),
        internet=make_internet(),
        dns=make_dns(),
        wifi=make_wifi(signal_percent=79),
        completed=True,
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.UNSTABLE_CONNECTION
