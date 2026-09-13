"""Windows ICMP ping diagnostics for WHYFI."""

from __future__ import annotations

import re
import subprocess

from whyfi.models.probes import PingResult


_LATENCY_PATTERN = re.compile(
    r"time(?P<operator>[=<])\s*(?P<value>\d+)ms",
    re.IGNORECASE,
)


def _extract_latencies(output: str) -> list[float]:
    """Extract latency measurements from Windows ping output."""

    latencies: list[float] = []

    for match in _LATENCY_PATTERN.finditer(output):
        operator = match.group("operator")
        value = float(match.group("value"))

        # Windows may report very fast replies as "time<1ms".
        # Represent that conservatively as 0.5 ms.
        if operator == "<" and value == 1:
            value = 0.5

        latencies.append(value)

    return latencies


def _calculate_jitter(latencies: list[float]) -> float | None:
    """Calculate average latency variation between consecutive replies."""

    if len(latencies) < 2:
        return None

    differences = [
        abs(current - previous)
        for previous, current in zip(
            latencies,
            latencies[1:],
        )
    ]

    return round(
        sum(differences) / len(differences),
        2,
    )


def ping_host(
    target: str,
    count: int = 4,
    timeout_ms: int = 1000,
) -> PingResult:
    """Ping an IPv4 target using the native Windows ping utility."""

    if count < 1:
        raise ValueError("count must be at least 1")

    if timeout_ms < 1:
        raise ValueError("timeout_ms must be at least 1")

    command = [
        "ping.exe",
        "-4",
        "-n",
        str(count),
        "-w",
        str(timeout_ms),
        target,
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=(count * timeout_ms / 1000) + 5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return PingResult(
            target=target,
            reachable=False,
            packets_sent=count,
            packets_received=0,
            packet_loss_percent=100.0,
            error="Ping command timed out.",
        )
    except OSError as exc:
        return PingResult(
            target=target,
            reachable=False,
            packets_sent=count,
            packets_received=0,
            packet_loss_percent=100.0,
            error=str(exc),
        )

    output = f"{completed.stdout}\n{completed.stderr}"
    latencies = _extract_latencies(output)

    packets_received = len(latencies)
    packet_loss_percent = round(
        ((count - packets_received) / count) * 100,
        1,
    )

    if not latencies:
        return PingResult(
            target=target,
            reachable=False,
            packets_sent=count,
            packets_received=0,
            packet_loss_percent=100.0,
            error="No ICMP replies received.",
        )

    return PingResult(
        target=target,
        reachable=True,
        packets_sent=count,
        packets_received=packets_received,
        packet_loss_percent=packet_loss_percent,
        min_latency_ms=min(latencies),
        average_latency_ms=round(
            sum(latencies) / len(latencies),
            2,
        ),
        max_latency_ms=max(latencies),
        jitter_ms=_calculate_jitter(latencies),
    )
