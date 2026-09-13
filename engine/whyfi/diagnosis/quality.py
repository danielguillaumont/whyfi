"""Diagnosis rules for WHYFI connection-quality investigations."""

from __future__ import annotations

from whyfi.models.diagnosis import DiagnosisCode, DiagnosisResult
from whyfi.models.quality import ConnectionQualityResult


def diagnose_connection_quality(
    result: ConnectionQualityResult,
) -> DiagnosisResult:
    """Turn deeper connection-quality measurements into a diagnosis."""

    gateway = result.gateway

    if result.error is not None or gateway is None:
        evidence = []

        if result.error:
            evidence.append(result.error)

        return DiagnosisResult(
            code=DiagnosisCode.UNKNOWN,
            title="I couldn't measure connection quality.",
            confidence=55,
            summary=(
                "WHYFI could not collect enough information to determine "
                "whether the connection is stable."
            ),
            evidence=evidence,
            recommendation=(
                "Run the connection-quality test again."
            ),
        )

    # If instability is already visible between this computer and the
    # gateway, it begins inside the local network. Check this before
    # upstream instability because local problems can also affect public
    # internet measurements.
    if result.gateway_unstable:
        evidence = [
            f"Gateway: {gateway.target}.",
            f"Gateway packet loss: {gateway.packet_loss_percent}%.",
            (
                f"Gateway jitter: "
                f"{gateway.jitter_ms if gateway.jitter_ms is not None else 'Unavailable'} ms."
            ),
        ]

        return DiagnosisResult(
            code=DiagnosisCode.UNSTABLE_CONNECTION,
            title="Your local connection is unstable.",
            confidence=94,
            summary=(
                "WHYFI detected instability between your computer and the "
                "local router or access point."
            ),
            evidence=evidence,
            recommendation=(
                "If you're using Wi-Fi, move closer to the router and reduce "
                "wireless interference. If you're using Ethernet, check the "
                "cable and network port."
            ),
        )

    if result.internet_unstable:
        evidence = [
            f"Gateway packet loss: {gateway.packet_loss_percent}%.",
            (
                f"Gateway jitter: "
                f"{gateway.jitter_ms if gateway.jitter_ms is not None else 'Unavailable'} ms."
            ),
        ]

        for probe in result.internet_probes:
            evidence.append(
                (
                    f"{probe.target}: {probe.packet_loss_percent}% packet loss, "
                    f"{probe.jitter_ms if probe.jitter_ms is not None else 'Unavailable'} ms jitter."
                )
            )

        return DiagnosisResult(
            code=DiagnosisCode.UNSTABLE_CONNECTION,
            title="The instability appears to be beyond your router.",
            confidence=91,
            summary=(
                "Your local path to the router looks stable, but multiple "
                "public internet targets show significant instability."
            ),
            evidence=evidence,
            recommendation=(
                "Run the test again to confirm the pattern. If it continues "
                "across multiple devices, check your modem or ISP connection."
            ),
        )

    if result.healthy:
        evidence = [
            f"Gateway packet loss: {gateway.packet_loss_percent}%.",
            (
                f"Gateway jitter: "
                f"{gateway.jitter_ms if gateway.jitter_ms is not None else 'Unavailable'} ms."
            ),
        ]

        for probe in result.internet_probes:
            evidence.append(
                (
                    f"{probe.target}: {probe.packet_loss_percent}% packet loss, "
                    f"{probe.jitter_ms if probe.jitter_ms is not None else 'Unavailable'} ms jitter."
                )
            )

        return DiagnosisResult(
            code=DiagnosisCode.HEALTHY,
            title="Your connection quality looks healthy.",
            confidence=94,
            summary=(
                "WHYFI did not find significant packet loss or jitter on the "
                "local network or across multiple public targets."
            ),
            evidence=evidence,
            recommendation="No action is needed based on this quality test.",
        )

    return DiagnosisResult(
        code=DiagnosisCode.UNKNOWN,
        title="The quality results are inconclusive.",
        confidence=50,
        summary=(
            "WHYFI collected connection-quality measurements but could not "
            "confidently match them to a known instability pattern."
        ),
        evidence=[],
        recommendation="Run the connection-quality test again.",
    )
