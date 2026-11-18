"""Evidence-based diagnosis rules for WHYFI."""

from __future__ import annotations

from whyfi.diagnosis.wifi import describe_wifi_signal, is_weak_wifi_signal
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
    wifi = result.wifi
    local_config = result.local_config
    route_failed = any(error.check == "route" for error in result.collection_errors)
    no_default_route = connection is None and not route_failed

    if no_default_route and internet is not None and internet.reachable is True:
        return DiagnosisResult(
            code=DiagnosisCode.UNKNOWN,
            title="The diagnosis is inconclusive.",
            confidence=None,
            summary=(
                "Windows reported no active IPv4 default route, but WHYFI "
                "received replies from public IPv4 targets."
            ),
            evidence=[
                "No active IPv4 default route was found.",
                f"Public IPv4 targets reachable: {internet.targets_reachable}.",
            ],
            recommendation="Run the diagnosis again and review the technical details.",
        )

    # An active physical adapter with only a 169.254.x.x address strongly
    # suggests that Windows failed to receive an IPv4 lease from DHCP.
    #
    # This must be checked before NO_CONNECTION because a DHCP failure can
    # prevent Windows from having a usable default route at all.
    if (
        not route_failed
        and local_config is not None
        and local_config.likely_dhcp_issue
    ):
        adapters = ", ".join(
            local_config.link_local_ipv4_adapters
        ) or "Unknown"

        return DiagnosisResult(
            code=DiagnosisCode.LOCAL_CONFIG_ISSUE,
            title="Your computer didn't get a usable IP address.",
            confidence=97,
            summary=(
                "WHYFI found an active network adapter, but Windows assigned "
                "only a 169.254.x.x link-local IPv4 address. This usually means "
                "the computer could not obtain a normal address from DHCP."
            ),
            evidence=[
                f"Active adapter(s): {', '.join(local_config.active_adapters)}.",
                f"Link-local adapter(s): {adapters}.",
                "No usable IPv4 address was found.",
                "A 169.254.x.x address was detected.",
            ],
            recommendation=(
                "Reconnect to the network and try renewing the IP address. "
                "If the problem continues, check the router or DHCP service."
            ),
        )

    if no_default_route and (
        (internet is not None and internet.reachable is False)
        or (
            local_config is not None
            and not local_config.healthy
            and not local_config.active_adapters
        )
    ):
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

    if (
        connection is None
        or gateway is None
        or gateway.reachable is None
        or internet is None
        or internet.reachable is None
        or any(
            error.check in {"gateway", "internet", "local_config"}
            for error in result.collection_errors
        )
    ):
        evidence = [
            f"{error.target}: {error.message}" if error.target else error.message
            for error in result.collection_errors
        ]
        if no_default_route:
            evidence.insert(0, "No active IPv4 default route was found.")
        if not evidence and result.error:
            evidence.append(result.error)

        return DiagnosisResult(
            code=DiagnosisCode.UNKNOWN,
            title="The diagnosis is inconclusive.",
            confidence=None,
            summary=(
                "WHYFI could not collect the evidence needed to identify "
                "a connection problem reliably."
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

    # Weak Wi-Fi plus packet loss to the local gateway gives us stronger
    # evidence that the wireless link itself is contributing to the problem.
    if (
        connection.adapter_type == "wifi"
        and wifi is not None
        and wifi.connected
        and is_weak_wifi_signal(wifi.signal_percent)
        and gateway.reachable
        and gateway.packet_loss_percent is not None
        and gateway.packet_loss_percent >= _PACKET_LOSS_THRESHOLD_PERCENT
    ):
        signal_description = describe_wifi_signal(wifi.signal_percent)

        return DiagnosisResult(
            code=DiagnosisCode.WIFI_ISSUE,
            title="Your Wi-Fi signal looks weak.",
            confidence=95,
            summary=(
                "WHYFI found significant packet loss between your computer "
                "and the router while the Wi-Fi signal was weak."
            ),
            evidence=[
                f"Wi-Fi signal: {wifi.signal_percent}%.",
                f"Signal quality: {signal_description}.",
                f"Gateway packet loss: {gateway.packet_loss_percent}%.",
                f"Radio type: {wifi.radio_type or 'Unknown'}.",
                f"Channel: {wifi.channel if wifi.channel is not None else 'Unknown'}.",
            ],
            recommendation=(
                "Move closer to the router or access point, reduce wireless "
                "interference, and run WHYFI again. If possible, compare the "
                "result with an Ethernet connection."
            ),
        )

    # Packet loss to the local gateway strongly suggests instability between
    # this computer and the local network.
    if (
        gateway.reachable
        and gateway.packet_loss_percent is not None
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

    configured_queries = dns.configured_queries if dns is not None else []
    if not configured_queries and dns is not None and dns.default_query is not None:
        configured_queries = [dns.default_query]
    system_query = dns.system_query if dns is not None else None
    conflicting_dns = (
        system_query is not None
        and system_query.success is not None
        and dns.healthy is not None
        and system_query.success != dns.healthy
    )

    if (
        internet.reachable
        and dns is not None
        and dns.healthy is False
        and dns.measurements_complete
        and not conflicting_dns
    ):
        return DiagnosisResult(
            code=DiagnosisCode.DNS_ISSUE,
            title="The DNS test lookup failed.",
            confidence=88,
            summary=(
                "WHYFI can reach the internet by IP address, but DNS resolution "
                "through the configured resolvers did not succeed for the test name."
            ),
            evidence=[
                "Direct-IP internet connectivity succeeded.",
                dns.error or "No configured resolver resolved the test name.",
                *[
                    f"{query.resolver}: {query.error or 'Lookup did not succeed.'}"
                    for query in configured_queries
                ],
            ],
            recommendation=(
                "Check the DNS settings and any VPN or network policy that applies "
                "to this connection."
            ),
        )

    # Multiple independent public targets must show significant loss before
    # WHYFI classifies the wider internet connection as unstable.
    lossy_public_probes = [
        probe
        for probe in internet.probes
        if (
            probe.reachable
            and probe.packet_loss_percent is not None
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

    resolved = sum(query.success is True for query in configured_queries)
    partial_dns = 0 < resolved < len(configured_queries)
    if dns is None or not dns.measurements_complete or partial_dns or conflicting_dns:
        evidence = [
            f"{query.resolver}: {query.error or 'Lookup result unavailable.'}"
            for query in configured_queries
            if query.success is not True
        ]
        if configured_queries:
            evidence.insert(
                0,
                f"Configured DNS resolvers that resolved the test name: "
                f"{resolved}/{len(configured_queries)}.",
            )
        if dns is not None and dns.error:
            evidence.append(dns.error)
        if dns is not None and dns.attribution_error:
            evidence.append(dns.attribution_error)
        if system_query is not None and system_query.error:
            evidence.append(system_query.error)
        if conflicting_dns:
            evidence.append("Windows DNS-client and direct resolver lookups gave different results.")
        if dns is None and result.error:
            evidence.append(result.error)
        return DiagnosisResult(
            code=DiagnosisCode.UNKNOWN,
            title=(
                "DNS works through some configured resolvers."
                if partial_dns and not conflicting_dns else "The DNS test is inconclusive."
            ),
            confidence=None,
            summary=(
                "At least one configured resolver answered the test lookup. "
                "Other configured lookups failed or were unavailable."
                if partial_dns and not conflicting_dns else
                "WHYFI could not establish consistent DNS evidence for this connection."
            ),
            evidence=evidence,
            recommendation="Run the diagnosis again and review the DNS details.",
        )

    if gateway.reachable and internet.reachable and dns.healthy:
        gateway_latency = (
            f"{gateway.average_latency_ms} ms"
            if gateway.average_latency_ms is not None
            else "Unavailable"
        )

        evidence = [
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
        ]

        if configured_queries:
            evidence.append(
                f"Configured DNS resolvers that resolved the test name: "
                f"{resolved}/{len(configured_queries)}."
            )
        if system_query is not None:
            evidence.append("The Windows DNS client resolved the test name.")
        if (
            connection.adapter_type == "wifi"
            and wifi is not None
            and wifi.connected
            and wifi.signal_percent is not None
        ):
            evidence.append(
                (
                    f"Wi-Fi signal: {wifi.signal_percent}% "
                    f"({describe_wifi_signal(wifi.signal_percent)})."
                )
            )

        if local_config is not None and local_config.healthy:
            evidence.append("Local IPv4 configuration: healthy.")

        return DiagnosisResult(
            code=DiagnosisCode.HEALTHY,
            title="Everything looks healthy.",
            confidence=96,
            summary=(
                "Your local connection, router, internet access, and DNS "
                "are all responding normally."
            ),
            evidence=evidence,
            recommendation="No action is needed based on the baseline checks.",
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
