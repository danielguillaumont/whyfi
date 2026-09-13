"""Evidence-based diagnosis rules for WHYFI."""

from __future__ import annotations

from whyfi.models.diagnostic import BaselineDiagnosticResult
from whyfi.models.diagnosis import DiagnosisCode, DiagnosisResult


_PACKET_LOSS_THRESHOLD_PERCENT = 25.0


def diagnose_baseline(
    result: BaselineDiagnosticResult,
) -> DiagnosisResult:
    """Turn baseline diagnostic measurements into a root-cause diagnosis."""

    connection = result.connection
    gateway = result.gateway
    internet = result.internet
    dns = result.dns

    # No usable Windows default connection was discovered.
    if connection is None:
        return DiagnosisResult(
            code=DiagnosisCode.NO_CONNECTION,
            title="You're not connected.",
            confidence=98,
            summary=(
                "WHYFI could not find an active primary network connection "
                "with a usable default route."
            ),
            evidence=[
                "No primary network connection was discovered.",
            ],
            recommendation=(
                "Connect to Wi-Fi or Ethernet, then run the diagnosis again."
            ),
        )

    # We found a connection, but one or more required checks failed to execute.
    if gateway is None or internet is None or dns is None:
        evidence = [
            f"Primary adapter: {connection.adapter_name}",
            f"IPv4 address: {connection.ipv4_address or 'Unavailable'}",
            f"Gateway: {connection.gateway}",
        ]

        if result.error:
            evidence.append(result.error)

        return DiagnosisResult(
            code=DiagnosisCode.UNKNOWN,
            title="I couldn't finish every test.",
            confidence=55,
            summary=(
                "WHYFI found your network connection, but one or more "
                "diagnostic checks could not be completed."
            ),
            evidence=evidence,
            recommendation=(
                "Run the diagnosis again and review the technical details."
            ),
        )

    # Gateway and wider internet are both unreachable.
    if not gateway.reachable and not internet.reachable:
        return DiagnosisResult(
            code=DiagnosisCode.GATEWAY_ISSUE,
            title="Your router isn't answering.",
            confidence=90,
            summary=(
                "Your computer has a network connection, but WHYFI could not "
                "reach either the default gateway or known public internet targets."
            ),
            evidence=[
                f"Adapter {connection.adapter_name} is active.",
                f"Gateway {connection.gateway} did not respond.",
                (
                    f"Public targets reachable: "
                    f"{internet.targets_reachable}/{internet.targets_tested}."
                ),
            ],
            recommendation=(
                "Check your Wi-Fi or Ethernet connection and restart the router "
                "if other devices are having the same problem."
            ),
        )

    # Some routers intentionally ignore ICMP even when routing still works.
    if not gateway.reachable and internet.reachable:
        return DiagnosisResult(
            code=DiagnosisCode.UNKNOWN,
            title="Your internet works, but your router ignored the ping.",
            confidence=72,
            summary=(
                "WHYFI can reach the wider internet, but your default gateway "
                "did not respond to ICMP. Some routers intentionally block ping."
            ),
            evidence=[
                f"Gateway {connection.gateway} did not respond to ICMP.",
                (
                    f"Public targets reachable: "
                    f"{internet.targets_reachable}/{internet.targets_tested}."
                ),
            ],
            recommendation=(
                "No immediate action is required if your connection is "
                "otherwise working."
            ),
        )

    # Local gateway works, but direct-IP internet access does not.
    if gateway.reachable and not internet.reachable:
        return DiagnosisResult(
            code=DiagnosisCode.INTERNET_ISSUE,
            title="Your router works. The internet beyond it doesn't.",
            confidence=93,
            summary=(
                "Your computer can reach the local router, but WHYFI could not "
                "reach known public IP addresses."
            ),
            evidence=[
                f"Gateway {connection.gateway} is reachable.",
                f"Gateway packet loss: {gateway.packet_loss_percent}%.",
                (
                    f"Public targets reachable: "
                    f"{internet.targets_reachable}/{internet.targets_tested}."
                ),
            ],
            recommendation=(
                "Check your modem or ISP status. If the problem continues "
                "across multiple devices, the issue is likely upstream of "
                "your local network."
            ),
        )

    # Packet loss to the local gateway strongly suggests instability between
    # this computer and the local network.
    if (
        gateway.reachable
        and gateway.packet_loss_percent >= _PACKET_LOSS_THRESHOLD_PERCENT
    ):
        return DiagnosisResult(
            code=DiagnosisCode.UNSTABLE_CONNECTION,
            title="Your local connection looks unstable.",
            confidence=92,
            summary=(
                "WHYFI can reach your router, but packets are being lost "
                "between your computer and the local network."
            ),
            evidence=[
                f"Gateway {connection.gateway} is reachable.",
                f"Gateway packet loss: {gateway.packet_loss_percent}%.",
                (
                    f"Packet-loss warning threshold: "
                    f"{_PACKET_LOSS_THRESHOLD_PERCENT}%."
                ),
            ],
            recommendation=(
                "If you're on Wi-Fi, move closer to the router and reduce "
                "wireless interference. If you're on Ethernet, check the "
                "cable and network port."
            ),
        )

    # Internet works directly by IP, while the configured DNS resolver fails
    # and at least one alternate resolver succeeds.
    if internet.reachable and dns.likely_dns_issue:
        alternate_successes = sum(
            1 for query in dns.alternate_queries if query.success
        )

        return DiagnosisResult(
            code=DiagnosisCode.DNS_ISSUE,
            title="Your Wi-Fi's fine. DNS isn't.",
            confidence=96,
            summary=(
                "Your connection can reach the internet directly, but your "
                "configured DNS resolver failed while an alternate resolver worked."
            ),
            evidence=[
                "Internet reachable by direct IP: yes.",
                f"Default DNS resolver: {dns.default_resolver or 'Unknown'}.",
                "Default DNS query failed.",
                (
                    f"Alternate DNS resolvers successful: "
                    f"{alternate_successes}/{len(dns.alternate_queries)}."
                ),
            ],
            recommendation=(
                "Try using a public DNS resolver such as 1.1.1.1 or 8.8.8.8."
            ),
        )

    # Direct-IP internet works but DNS resolution is unhealthy across the board.
    if internet.reachable and not dns.healthy:
        return DiagnosisResult(
            code=DiagnosisCode.DNS_ISSUE,
            title="DNS resolution isn't working.",
            confidence=88,
            summary=(
                "WHYFI can reach the internet by IP address, but DNS resolution "
                "did not complete successfully."
            ),
            evidence=[
                "Direct-IP internet connectivity succeeded.",
                f"Default DNS resolver: {dns.default_resolver or 'Unknown'}.",
                "The configured DNS query failed.",
            ],
            recommendation=(
                "Check your DNS configuration or temporarily try another resolver."
            ),
        )

    # We require multiple public targets to show packet loss before declaring
    # wider internet instability. This avoids blaming the connection because
    # one remote host happens to rate-limit or deprioritize ICMP.
    lossy_public_probes = [
        probe
        for probe in internet.probes
        if (
            probe.reachable
            and probe.packet_loss_percent >= _PACKET_LOSS_THRESHOLD_PERCENT
        )
    ]

    if len(lossy_public_probes) >= 2:
        evidence = [
            f"Gateway packet loss: {gateway.packet_loss_percent}%.",
        ]

        evidence.extend(
            (
                f"{probe.target} packet loss: "
                f"{probe.packet_loss_percent}%."
            )
            for probe in lossy_public_probes
        )

        return DiagnosisResult(
            code=DiagnosisCode.UNSTABLE_CONNECTION,
            title="Your internet connection looks unstable.",
            confidence=88,
            summary=(
                "WHYFI can reach the internet, but multiple independent "
                "public targets are showing significant packet loss."
            ),
            evidence=evidence,
            recommendation=(
                "Run the test again to confirm the pattern. If packet loss "
                "continues across multiple devices, check your modem, router, "
                "or ISP connection."
            ),
        )

    # All baseline layers are healthy.
    if gateway.reachable and internet.reachable and dns.healthy:
        gateway_latency = (
            f"{gateway.average_latency_ms} ms"
            if gateway.average_latency_ms is not None
            else "Unavailable"
        )

        dns_latency = (
            f"{dns.default_query.latency_ms} ms"
            if (
                dns.default_query is not None
                and dns.default_query.latency_ms is not None
            )
            else "Unavailable"
        )

        return DiagnosisResult(
            code=DiagnosisCode.HEALTHY,
            title="Everything looks healthy.",
            confidence=96,
            summary=(
                "Your local connection, router, internet access, and DNS "
                "are all responding normally."
            ),
            evidence=[
                f"Primary adapter: {connection.adapter_name}.",
                (
                    f"Gateway reachable with "
                    f"{gateway.packet_loss_percent}% packet loss."
                ),
                f"Average gateway latency: {gateway_latency}.",
                (
                    f"Public targets reachable: "
                    f"{internet.targets_reachable}/{internet.targets_tested}."
                ),
                (
                    f"DNS resolver {dns.default_resolver} "
                    f"responded in {dns_latency}."
                ),
            ],
            recommendation=(
                "No action is needed based on the baseline checks."
            ),
        )

    return DiagnosisResult(
        code=DiagnosisCode.UNKNOWN,
        title="Something unusual is going on.",
        confidence=50,
        summary=(
            "WHYFI collected the baseline measurements but could not match "
            "them confidently to a known failure pattern."
        ),
        evidence=[],
        recommendation=(
            "Review the technical details and run the diagnosis again."
        ),
    )
