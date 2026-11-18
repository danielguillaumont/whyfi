"""Windows ICMP ping diagnostics for WHYFI."""

from __future__ import annotations

import ipaddress
import json
import subprocess

from whyfi.models.probes import PingResult


# IPStatus values for observed timeouts and network responses other than echo replies.
_NO_REPLY_STATUSES = {11002, 11003, 11004, 11005, 11010, 11013, 11014}


def _parse_ping_samples(output: str, count: int) -> list[float]:
    samples = json.loads(output)
    if not isinstance(samples, list) or len(samples) != count:
        raise ValueError(f"Expected {count} ICMP samples.")

    latencies = []
    for sample in samples:
        status = sample["status"]
        if type(status) is not int:
            raise ValueError("Invalid ICMP status.")
        if status == 0:
            elapsed = sample["elapsed"]
            if type(elapsed) is not int or elapsed < 0:
                raise ValueError("Invalid ICMP round-trip time.")
            latencies.append(float(elapsed) if elapsed else 0.5)
        elif status not in _NO_REPLY_STATUSES:
            raise ValueError(f"ICMP probe failed with Windows status {status}.")

    return latencies


def _calculate_jitter(latencies: list[float]) -> float | None:
    """Calculate average latency variation between consecutive replies."""

    if len(latencies) < 2:
        return None

    differences = [
        abs(current - previous)
        for previous, current in zip(latencies, latencies[1:])
    ]
    return round(sum(differences) / len(differences), 2)


def _unavailable_ping(target: str, error: str) -> PingResult:
    return PingResult(
        target=target,
        reachable=None,
        packets_sent=None,
        packets_received=None,
        packet_loss_percent=None,
        error=error,
    )


def ping_host(
    target: str,
    count: int = 4,
    timeout_ms: int = 1000,
) -> PingResult:
    """Measure IPv4 ICMP replies using the structured Windows .NET ping API."""

    if type(count) is not int or count < 1:
        raise ValueError("count must be a positive integer")
    if type(timeout_ms) is not int or timeout_ms < 1:
        raise ValueError("timeout_ms must be a positive integer")

    address = ipaddress.IPv4Address(target)
    if address.is_unspecified:
        return _unavailable_ping(
            target, "The default route has no IPv4 next hop to ping."
        )

    script = f"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$address = [System.Net.IPAddress]::Parse('{address}')
$ping = [System.Net.NetworkInformation.Ping]::new()
try {{
    $samples = @(for ($i = 0; $i -lt {count}; $i++) {{
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        $reply = $ping.Send($address, {timeout_ms})
        [PSCustomObject]@{{status = [int]$reply.Status; elapsed = $reply.RoundtripTime}}
        $delay = 1000 - $timer.ElapsedMilliseconds
        if ($i + 1 -lt {count} -and $delay -gt 0) {{
            Start-Sleep -Milliseconds $delay
        }}
    }})
    ConvertTo-Json -InputObject $samples -Compress
}} finally {{
    $ping.Dispose()
}}
"""

    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=(count * max(timeout_ms, 1000) / 1000) + 10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _unavailable_ping(target, "Windows ICMP command timed out.")
    except OSError as exc:
        return _unavailable_ping(target, f"Could not run Windows ICMP command: {exc}")

    if completed.returncode != 0 or completed.stderr.strip():
        detail = completed.stderr.strip() or completed.stdout.strip()
        return _unavailable_ping(
            target, f"Windows ICMP command failed (exit {completed.returncode}): {detail}"
        )

    try:
        latencies = _parse_ping_samples(completed.stdout, count)
    except (KeyError, TypeError, ValueError) as exc:
        return _unavailable_ping(target, f"Invalid Windows ICMP output: {exc}")

    packets_received = len(latencies)
    packet_loss_percent = round(((count - packets_received) / count) * 100, 1)

    return PingResult(
        target=target,
        reachable=bool(latencies),
        packets_sent=count,
        packets_received=packets_received,
        packet_loss_percent=packet_loss_percent,
        min_latency_ms=min(latencies) if latencies else None,
        average_latency_ms=round(sum(latencies) / packets_received, 2) if latencies else None,
        max_latency_ms=max(latencies) if latencies else None,
        jitter_ms=_calculate_jitter(latencies),
        error=None if latencies else "No ICMP replies received.",
    )
